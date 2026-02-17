import uuid
from django.db.models import Count, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from .models import ChatConversation, ChatMessage
from .services import get_chat_response


class ChatView(APIView):
    def post(self, request):
        message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id')

        if not message:
            return Response(
                {'error': 'El mensaje es requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not session_id:
            session_id = str(uuid.uuid4())

        conversation, _ = ChatConversation.objects.get_or_create(session_id=session_id)

        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.USER,
            content=message,
        )

        reply = get_chat_response(conversation, message)

        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.ASSISTANT,
            content=reply,
        )

        return Response({
            'session_id': session_id,
            'reply': reply,
        })


class ConversationListView(APIView):
    def get(self, request):
        conversations = (
            ChatConversation.objects
            .annotate(
                message_count=Count('messages'),
                last_message_at=Max('messages__created_at'),
            )
            .filter(message_count__gt=0)
            .order_by('-last_message_at')
        )

        # Get first user message as preview for each conversation
        results = []
        for conv in conversations:
            first_msg = conv.messages.filter(role='user').first()
            results.append({
                'session_id': str(conv.session_id),
                'created_at': conv.created_at,
                'message_count': conv.message_count,
                'last_message_at': conv.last_message_at,
                'preview': first_msg.content[:100] if first_msg else '',
            })

        return Response({'results': results})


class ChatHistoryView(APIView):
    def get(self, request, session_id):
        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversación no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = conversation.messages.all().values('role', 'content', 'created_at')
        return Response({
            'session_id': str(session_id),
            'messages': list(messages),
        })
