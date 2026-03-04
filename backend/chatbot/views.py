import json
import logging
import uuid
from django.conf import settings
from django.db.models import Count, Max, Q, Subquery, OuterRef
from django.utils import timezone
from openai import OpenAI
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from .models import ChatConversation, ChatMessage, SystemPrompt
from .services import get_chat_response, assign_conversation_agent, search_properties, _extract_keywords, _find_conversation_property
from .whatsapp import send_whatsapp_message
from properties.permissions import IsAdmin

logger = logging.getLogger(__name__)


class ChatView(APIView):
    permission_classes = [AllowAny]

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

        conversation, created = ChatConversation.objects.get_or_create(session_id=session_id)
        if created:
            assign_conversation_agent(conversation, message)

        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.USER,
            content=message,
        )

        # If AI is paused by admin, save message but skip AI response
        if conversation.is_ai_paused:
            return Response({
                'session_id': session_id,
                'reply': '',
                'media': [],
                'ai_paused': True,
            })

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Subquery for first user message preview (avoids N+1)
        first_user_msg = (
            ChatMessage.objects
            .filter(conversation=OuterRef('pk'), role='user')
            .order_by('created_at')
            .values('content')[:1]
        )

        conversations = (
            ChatConversation.objects
            .select_related('agent')
            .annotate(
                message_count=Count('messages', distinct=True),
                last_message_at=Max('messages__created_at'),
                preview_raw=Subquery(first_user_msg),
            )
            .filter(message_count__gt=0)
        )

        # Non-admin users only see conversations assigned to their agent
        if not request.user.is_staff:
            agent = getattr(request.user, 'agent_profile', None)
            if agent:
                conversations = conversations.filter(agent=agent)
            else:
                return Response({'results': []})

        search = request.query_params.get('search', '').strip()
        if search:
            # Use a subquery to check message content without inflating counts
            matching_convs = (
                ChatMessage.objects
                .filter(content__icontains=search)
                .values('conversation_id')
            )
            conversations = conversations.filter(
                Q(session_id__icontains=search) |
                Q(pk__in=matching_convs)
            )

        conversations = conversations.order_by('-last_message_at')

        results = []
        for conv in conversations:
            preview = (conv.preview_raw or '')[:100]
            results.append({
                'session_id': str(conv.session_id),
                'created_at': conv.created_at,
                'message_count': conv.message_count,
                'last_message_at': conv.last_message_at,
                'preview': preview,
                'agent_name': conv.agent.name if conv.agent else None,
            })

        return Response({'results': results})


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversación no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = conversation.messages.all().values('role', 'content', 'created_at')

        pause_remaining = 0
        if conversation.is_ai_paused:
            pause_remaining = int((conversation.admin_paused_until - timezone.now()).total_seconds())

        return Response({
            'session_id': str(session_id),
            'messages': list(messages),
            'is_ai_paused': conversation.is_ai_paused,
            'is_permanently_paused': conversation.is_permanently_paused,
            'admin_paused_until': conversation.admin_paused_until,
            'pause_remaining_seconds': pause_remaining,
        })


class SystemPromptView(APIView):
    permission_classes = [IsAdmin]

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
    permission_classes = [IsAdmin]

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


class AdminReplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                {'error': 'El mensaje es requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversación no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.ADMIN,
            content=message,
        )

        pause_mode = request.data.get('pause_mode', 'auto')
        if pause_mode == 'permanent':
            conversation.pause_ai(permanent=True)
        elif pause_mode == 'auto':
            conversation.pause_ai(minutes=30)
        # 'none' = don't pause

        # If session_id is a phone number, send via WhatsApp
        if session_id.isdigit() and len(session_id) >= 7:
            send_whatsapp_message(session_id, message)

        return Response({'status': 'sent', 'ai_paused_until': conversation.admin_paused_until})


class AdminUnpauseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversación no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        conversation.unpause_ai()
        return Response({'status': 'unpaused'})


class AdminPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        mode = request.data.get('mode', 'auto')
        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversación no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if mode == 'off':
            conversation.unpause_ai()
        elif mode == 'permanent':
            conversation.pause_ai(permanent=True)
        else:
            conversation.pause_ai(minutes=30)

        return Response({
            'status': 'ok',
            'is_ai_paused': conversation.is_ai_paused,
            'is_permanently_paused': conversation.is_permanently_paused,
            'admin_paused_until': conversation.admin_paused_until,
        })


class ChatDebugView(APIView):
    """Debug endpoint: shows what the bot sees for a conversation."""
    permission_classes = [IsAdmin]

    def get(self, request, session_id):
        from properties.models import Property

        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversación no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Load history like get_chat_response does
        history = conversation.messages.order_by('-created_at')[:100]
        history = list(reversed(history))

        conversation_msgs = [
            {'role': msg.role, 'content': msg.content}
            for msg in history
        ]

        # Get the last user message
        last_user_msg = ''
        for msg in reversed(history):
            if msg.role == 'user':
                last_user_msg = msg.content
                break

        # Debug: show keyword extraction
        keywords = _extract_keywords(last_user_msg)

        # Debug: show active property from history
        base_qs = Property.objects.filter(activo=True).select_related('agent').prefetch_related('images', 'videos')
        active_prop = _find_conversation_property(conversation_msgs, base_qs)

        # Debug: show search results
        properties = search_properties(last_user_msg, conversation_messages=conversation_msgs)
        prop_list = [
            {
                'identificador': p.identificador,
                'nombre': p.nombre,
                'agent': p.agent.name if p.agent else None,
            }
            for p in properties
        ]

        # Recent messages
        recent_msgs = [
            {
                'role': msg.role,
                'content': msg.content[:200],
                'created_at': msg.created_at.isoformat(),
            }
            for msg in history[-10:]
        ]

        return Response({
            'session_id': session_id,
            'last_user_message': last_user_msg,
            'extracted_keywords': keywords,
            'active_property': active_prop.identificador if active_prop else None,
            'search_results': prop_list,
            'total_messages': len(history),
            'recent_messages': recent_msgs,
            'agent_assigned': conversation.agent.name if conversation.agent else None,
        })
