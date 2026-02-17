from django.db.models import Count, Max, Avg, Min, F, Q
from django.db.models.functions import TruncDate, TruncHour
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ChatConversation, ChatMessage, ClientIntent


class AnalyticsView(APIView):
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
