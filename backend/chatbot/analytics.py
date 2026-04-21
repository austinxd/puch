import logging
import re
from collections import defaultdict
from django.conf import settings
from django.db.models import Count, Max, Avg, Min, F, Q
from django.db.models.functions import TruncDate, TruncHour
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from properties.permissions import IsAdmin
from .models import ChatConversation, ChatMessage, ClientIntent, PropertyInterest
from properties.models import Property


def normalize_phone(phone):
    return re.sub(r'\D', '', phone or '')


def _property_summary(prop, request=None):
    if prop is None:
        return None
    image = prop.images.first() if hasattr(prop, 'images') else None
    image_url = None
    if image and image.image:
        url = image.image.url
        if request is not None:
            image_url = request.build_absolute_uri(url)
        else:
            image_url = f"{settings.BASE_URL.rstrip('/')}{url}"
    return {
        'id': prop.id,
        'identificador': prop.identificador,
        'nombre': prop.nombre,
        'distrito': prop.distrito,
        'tipologia': prop.tipologia,
        'precio': prop.precio,
        'moneda': prop.moneda,
        'image_url': image_url,
    }

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

        # Most searched properties (first intent)
        top_properties = list(
            ChatConversation.objects
            .filter(first_property__isnull=False)
            .values(
                'first_property__identificador',
                'first_property__nombre',
                'first_property__distrito',
            )
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        top_properties_list = [
            {
                'identificador': p['first_property__identificador'],
                'nombre': p['first_property__nombre'],
                'distrito': p['first_property__distrito'],
                'count': p['count'],
            }
            for p in top_properties
        ]

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
            'top_properties': top_properties_list,
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


class ClientListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        search = (request.query_params.get('search') or '').strip().lower()

        intents = (
            ClientIntent.objects
            .exclude(phone='')
            .select_related('conversation', 'conversation__first_property')
            .order_by('-updated_at')
        )

        groups = defaultdict(list)
        for intent in intents:
            key = normalize_phone(intent.phone)
            if key:
                groups[key].append(intent)

        conv_ids = [i.conversation_id for intents_list in groups.values() for i in intents_list]
        last_msg_by_conv = dict(
            ChatMessage.objects
            .filter(conversation_id__in=conv_ids)
            .values('conversation_id')
            .annotate(last=Max('created_at'), count=Count('id'))
            .values_list('conversation_id', 'last')
        )
        msg_count_by_conv = dict(
            ChatMessage.objects
            .filter(conversation_id__in=conv_ids)
            .values('conversation_id')
            .annotate(c=Count('id'))
            .values_list('conversation_id', 'c')
        )
        interest_count_by_phone = {}

        results = []
        for phone, intent_list in groups.items():
            intent_list_sorted = sorted(intent_list, key=lambda i: i.conversation.created_at)
            latest = max(intent_list, key=lambda i: i.updated_at)
            conv_ids_phone = [i.conversation_id for i in intent_list]

            distinct_interests = (
                PropertyInterest.objects
                .filter(conversation_id__in=conv_ids_phone)
                .values('property_id').distinct().count()
            )
            interest_count_by_phone[phone] = distinct_interests

            last_activity = max(
                (last_msg_by_conv.get(cid) for cid in conv_ids_phone if last_msg_by_conv.get(cid)),
                default=latest.updated_at,
            )
            total_msgs = sum(msg_count_by_conv.get(cid, 0) for cid in conv_ids_phone)

            first_conv = intent_list_sorted[0].conversation
            first_prop = _property_summary(first_conv.first_property, request)

            row = {
                'phone': phone,
                'phone_display': latest.phone,
                'conversation_count': len(set(conv_ids_phone)),
                'message_count': total_msgs,
                'last_activity': last_activity,
                'first_property': first_prop,
                'interested_count': distinct_interests,
                'latest_intent': {
                    'operacion': latest.operacion,
                    'tipo_propiedad': latest.tipo_propiedad,
                    'distritos': latest.distritos,
                    'precio_min': latest.precio_min,
                    'precio_max': latest.precio_max,
                    'habitaciones': latest.habitaciones,
                    'caracteristicas': latest.caracteristicas,
                    'resumen': latest.resumen,
                    'updated_at': latest.updated_at,
                },
            }
            results.append(row)

        if search:
            results = [
                r for r in results
                if search in r['phone']
                or search in (r['latest_intent']['resumen'] or '').lower()
                or search in (r['latest_intent']['distritos'] or '').lower()
            ]

        results.sort(key=lambda r: r['last_activity'], reverse=True)
        return Response({'results': results})


class ClientDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, phone):
        target = normalize_phone(phone)
        if not target:
            return Response({'error': 'phone vacío'}, status=400)

        intents = (
            ClientIntent.objects
            .exclude(phone='')
            .select_related('conversation', 'conversation__first_property', 'conversation__agent')
        )
        matched = [i for i in intents if normalize_phone(i.phone) == target]
        if not matched:
            return Response({'error': 'cliente no encontrado'}, status=404)

        conv_map = {}
        for intent in matched:
            conv_map.setdefault(intent.conversation_id, intent.conversation)

        conv_ids = list(conv_map.keys())

        msg_counts = dict(
            ChatMessage.objects
            .filter(conversation_id__in=conv_ids)
            .values('conversation_id')
            .annotate(c=Count('id'), last=Max('created_at'))
            .values_list('conversation_id', 'c')
        )
        last_msg = dict(
            ChatMessage.objects
            .filter(conversation_id__in=conv_ids)
            .values('conversation_id')
            .annotate(last=Max('created_at'))
            .values_list('conversation_id', 'last')
        )

        conversations = []
        for cid, conv in sorted(conv_map.items(), key=lambda kv: kv[1].created_at, reverse=True):
            conversations.append({
                'session_id': str(conv.session_id),
                'created_at': conv.created_at,
                'last_message_at': last_msg.get(cid),
                'message_count': msg_counts.get(cid, 0),
                'agent_name': conv.agent.name if conv.agent else None,
                'first_property': _property_summary(conv.first_property, request),
            })

        intents_payload = [
            {
                'id': i.id,
                'session_id': str(i.conversation.session_id),
                'operacion': i.operacion,
                'tipo_propiedad': i.tipo_propiedad,
                'distritos': i.distritos,
                'precio_min': i.precio_min,
                'precio_max': i.precio_max,
                'habitaciones': i.habitaciones,
                'caracteristicas': i.caracteristicas,
                'resumen': i.resumen,
                'created_at': i.created_at,
                'updated_at': i.updated_at,
            }
            for i in sorted(matched, key=lambda x: x.updated_at, reverse=True)
        ]

        interests = (
            PropertyInterest.objects
            .filter(conversation_id__in=conv_ids)
            .select_related('property')
            .prefetch_related('property__images')
        )
        agg = {}
        for pi in interests:
            entry = agg.setdefault(pi.property_id, {
                'property': _property_summary(pi.property, request),
                'first_shown_at': pi.first_shown_at,
                'last_shown_at': pi.last_shown_at,
                'shown_count': 0,
                'session_ids': set(),
            })
            entry['shown_count'] += pi.shown_count
            entry['first_shown_at'] = min(entry['first_shown_at'], pi.first_shown_at)
            entry['last_shown_at'] = max(entry['last_shown_at'], pi.last_shown_at)
            entry['session_ids'].add(str(conv_map[pi.conversation_id].session_id))

        interested_properties = sorted(
            (
                {
                    **e,
                    'session_ids': sorted(e['session_ids']),
                }
                for e in agg.values()
            ),
            key=lambda e: e['last_shown_at'],
            reverse=True,
        )

        latest_intent = intents_payload[0] if intents_payload else None
        return Response({
            'phone': target,
            'phone_display': matched[0].phone,
            'latest_intent': latest_intent,
            'intents': intents_payload,
            'conversations': conversations,
            'interested_properties': interested_properties,
        })


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
