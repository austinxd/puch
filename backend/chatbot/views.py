import json
import logging
import uuid
from django.conf import settings
from django.db.models import Count, Max
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from .models import ChatConversation, ChatMessage, SystemPrompt
from .services import get_chat_response

logger = logging.getLogger(__name__)


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

        response = get_chat_response(conversation, message)
        reply = response['text']
        media = response['media']

        # Save assistant message (include media URLs for admin visibility)
        saved_content = reply
        if media:
            media_lines = '\n'.join(f'[media:{item["type"]}]{item["url"]}[/media]' for item in media)
            saved_content = f"{reply}\n{media_lines}"
        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.ASSISTANT,
            content=saved_content,
        )

        return Response({
            'session_id': session_id,
            'reply': reply,
            'media': media,
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


class SystemPromptView(APIView):
    def get(self, request):
        try:
            prompt = SystemPrompt.objects.get(pk=1)
            return Response({
                'content': prompt.content,
                'updated_at': prompt.updated_at,
            })
        except SystemPrompt.DoesNotExist:
            return Response({
                'content': '',
                'updated_at': None,
            })

    def put(self, request):
        content = request.data.get('content', '').strip()
        if not content:
            return Response(
                {'error': 'El contenido es requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prompt, _ = SystemPrompt.objects.update_or_create(
            pk=1, defaults={'content': content}
        )
        return Response({
            'content': prompt.content,
            'updated_at': prompt.updated_at,
        })


class PromptAnalysisView(APIView):
    def post(self, request):
        if not settings.OPENAI_API_KEY:
            return Response(
                {'error': 'OpenAI API key no configurada'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            current_prompt = SystemPrompt.objects.get(pk=1).content
        except SystemPrompt.DoesNotExist:
            return Response(
                {'error': 'No hay prompt configurado'},
                status=status.HTTP_404_NOT_FOUND,
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
            conversation_samples.append('\n'.join(lines))

        if not conversation_samples:
            return Response({
                'analysis': 'No hay suficientes conversaciones para analizar. Se necesitan conversaciones con al menos 3 mensajes.',
                'conversations_analyzed': 0,
            })

        samples_text = '\n\n---\n\n'.join(conversation_samples)

        analysis_prompt = f"""Eres un experto en diseño de prompts para chatbots inmobiliarios.

Analiza el siguiente system prompt y las conversaciones reales del chatbot, luego sugiere mejoras concretas.

=== SYSTEM PROMPT ACTUAL ===
{current_prompt}

=== CONVERSACIONES RECIENTES ({len(conversation_samples)} conversaciones) ===
{samples_text}

=== INSTRUCCIONES ===
Analiza:
1. **Efectividad general**: ¿El chatbot sigue las instrucciones del prompt?
2. **Problemas detectados**: ¿Hay conversaciones donde el chatbot falló o se desvió?
3. **Oportunidades de mejora**: ¿Qué reglas o flujos se podrían mejorar?
4. **Sugerencias concretas**: Lista cambios específicos al prompt con ejemplos.

Responde en español, de forma estructurada y accionable."""

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=2000,
                temperature=0.5,
            )
            analysis = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing prompt: {e}")
            return Response(
                {'error': 'Error al analizar con IA'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'analysis': analysis,
            'conversations_analyzed': len(conversation_samples),
        })
