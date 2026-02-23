import logging
from django.conf import settings
from django.db.models import Count, Max, Avg, Min, F, Q
from django.db.models.functions import TruncDate, TruncHour
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from properties.permissions import IsAdmin
from .models import ChatConversation, ChatMessage, ClientIntent

logger = logging.getLogger(__name__)


class AnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        """Dashboard statistics."""
        conversations = ChatConversation.objects.annotate(
            msg_count=Count('messages'),
            user_msg_count=Count('messages', filter=Q(messages__role='user')),
            assistant_msg_count=Count('messages', filter=Q(messages__role='assistant')),
            last_message_at=Max('messages__created_at'),
            first_message_at=Min('messages__created_at'),
        ).filter(msg_count__gt=0)

        total_conversations = conversations.count()
        total_messages = ChatMessage.objects.count()
        total_user_messages = ChatMessage.objects.filter(role='user').count()

        # Average messages per conversation
        avg_messages = conversations.aggregate(avg=Avg('msg_count'))['avg'] or 0

        # Conversations with only 1 user message (abandoned)
        single_msg = conversations.filter(user_msg_count=1).count()
        abandonment_rate = (single_msg / total_conversations * 100) if total_conversations > 0 else 0

        # Conversations with 3+ user messages (engaged)
        engaged = conversations.filter(user_msg_count__gte=3).count()
        engagement_rate = (engaged / total_conversations * 100) if total_conversations > 0 else 0

        # Messages per day
        messages_per_day = list(
            ChatMessage.objects.filter(role='user')
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')[:30]
        )
        for item in messages_per_day:
            item['date'] = item['date'].isoformat()

        # Messages per hour (peak hours)
        messages_per_hour = list(
            ChatMessage.objects.filter(role='user')
            .annotate(hour=TruncHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        hour_distribution = {}
        for item in messages_per_hour:
            h = item['hour'].hour
            hour_distribution[h] = hour_distribution.get(h, 0) + item['count']

        # Conversation depth distribution
        depth_dist = {
            '1 mensaje': conversations.filter(user_msg_count=1).count(),
            '2-3 mensajes': conversations.filter(user_msg_count__gte=2, user_msg_count__lte=3).count(),
            '4-6 mensajes': conversations.filter(user_msg_count__gte=4, user_msg_count__lte=6).count(),
            '7+ mensajes': conversations.filter(user_msg_count__gte=7).count(),
        }

        # Intents summary
        intents = ClientIntent.objects.all()
        intent_stats = {
            'total': intents.count(),
            'operacion': {},
            'tipo_propiedad': {},
            'distritos': {},
        }
        for intent in intents:
            if intent.operacion:
                op = intent.operacion
                intent_stats['operacion'][op] = intent_stats['operacion'].get(op, 0) + 1
            if intent.tipo_propiedad:
                tp = intent.tipo_propiedad
                intent_stats['tipo_propiedad'][tp] = intent_stats['tipo_propiedad'].get(tp, 0) + 1
            if intent.distritos:
                for d in intent.distritos.split(','):
                    d = d.strip()
                    if d:
                        intent_stats['distritos'][d] = intent_stats['distritos'].get(d, 0) + 1

        return Response({
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'total_user_messages': total_user_messages,
            'avg_messages_per_conversation': round(avg_messages, 1),
            'abandonment_rate': round(abandonment_rate, 1),
            'engagement_rate': round(engagement_rate, 1),
            'messages_per_day': messages_per_day,
            'hour_distribution': hour_distribution,
            'depth_distribution': depth_dist,
            'intents': intent_stats,
        })


class IntentListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        """List all client intents for follow-up."""
        intents = ClientIntent.objects.select_related('conversation').all()
        results = []
        for intent in intents:
            results.append({
                'id': intent.id,
                'phone': intent.phone,
                'session_id': intent.conversation.session_id,
                'operacion': intent.operacion,
                'tipo_propiedad': intent.tipo_propiedad,
                'distritos': intent.distritos,
                'precio_min': intent.precio_min,
                'precio_max': intent.precio_max,
                'habitaciones': intent.habitaciones,
                'caracteristicas': intent.caracteristicas,
                'resumen': intent.resumen,
                'notificado': intent.notificado,
                'created_at': intent.created_at,
                'updated_at': intent.updated_at,
            })
        return Response({'results': results})


class DealAnalysisView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        if not settings.OPENAI_API_KEY:
            return Response(
                {'error': 'OpenAI API key no configurada'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Get recent conversations with 3+ messages
        conversations = (
            ChatConversation.objects
            .annotate(msg_count=Count('messages'))
            .filter(msg_count__gte=3)
            .order_by('-created_at')[:20]
        )

        conversation_samples = []
        for conv in conversations:
            msgs = conv.messages.all()[:15]
            lines = [f"{'Usuario' if m.role == 'user' else 'Asistente'}: {m.content}" for m in msgs]

            # Include intent if exists
            intent = ClientIntent.objects.filter(conversation=conv).first()
            if intent:
                lines.append(f"\n[Intención detectada: {intent.operacion or ''} {intent.tipo_propiedad or ''} en {intent.distritos or ''}, presupuesto {intent.precio_min}-{intent.precio_max}, resumen: {intent.resumen or ''}]")

            conversation_samples.append('\n'.join(lines))

        if not conversation_samples:
            return Response({
                'analysis': 'No hay suficientes conversaciones para analizar. Se necesitan conversaciones con al menos 3 mensajes.',
                'conversations_analyzed': 0,
            })

        samples_text = '\n\n---\n\n'.join(conversation_samples)

        analysis_prompt = f"""Eres un experto en ventas inmobiliarias y análisis de leads.

Analiza las siguientes conversaciones reales de un chatbot inmobiliario y genera un informe estratégico de cierre de ventas.

=== CONVERSACIONES RECIENTES ({len(conversation_samples)} conversaciones) ===
{samples_text}

=== INSTRUCCIONES ===
Genera un análisis estratégico que incluya:

1. **Objeciones frecuentes**: ¿Cuáles son las principales objeciones o dudas de los clientes? ¿Cómo se están manejando?
2. **Oportunidades de cierre perdidas**: Identifica momentos donde el cliente mostró alta intención pero no se avanzó hacia el cierre.
3. **Leads de alta intención**: Lista los leads más calientes y por qué consideras que tienen alta probabilidad de conversión.
4. **Estrategias de mejora**: Sugiere acciones concretas para mejorar la tasa de conversión (seguimiento, respuestas, timing).
5. **Recomendaciones de seguimiento**: ¿A quién contactar primero y con qué mensaje?

Responde en español, de forma estructurada y accionable. Usa markdown para formato."""

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=2500,
                temperature=0.5,
            )
            analysis = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in deal analysis: {e}")
            return Response(
                {'error': 'Error al analizar con IA'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'analysis': analysis,
            'conversations_analyzed': len(conversation_samples),
        })
