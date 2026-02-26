import json
import logging
import threading
import time
import requests
from django.conf import settings
from django.db import close_old_connections
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import ChatConversation, ChatMessage
from .services import get_chat_response, assign_conversation_agent

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"

# Debounce: wait for rapid messages before processing
DEBOUNCE_SECONDS = 4

# Track active processing sessions within this worker to prevent duplicates
_active_sessions = set()
_sessions_lock = threading.Lock()


def send_whatsapp_message(to, text):
    """Send a text message via WhatsApp Business API."""
    url = f"{WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"WhatsApp send error: {response.status_code} {response.text}")
    return response


def send_whatsapp_image(to, image_url, caption=''):
    """Send an image via WhatsApp Business API using a public URL."""
    url = f"{WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    image_payload = {"link": image_url}
    if caption:
        image_payload["caption"] = caption
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": image_payload,
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"WhatsApp image send error: {response.status_code} {response.text}")
    return response


def send_whatsapp_video(to, video_url, caption=''):
    """Send a video via WhatsApp Business API using a public URL."""
    url = f"{WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    video_payload = {"link": video_url}
    if caption:
        video_payload["caption"] = caption
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "video",
        "video": video_payload,
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"WhatsApp video send error: {response.status_code} {response.text}")
    return response


def _process_pending(session_id, phone):
    """Find and process all pending user messages for a conversation."""
    conversation = ChatConversation.objects.get(session_id=session_id)

    if conversation.is_ai_paused:
        return False

    # Find the last bot/admin response
    last_response = conversation.messages.filter(
        role__in=['assistant', 'admin']
    ).order_by('-created_at').first()

    # Get pending user messages (after last response)
    if last_response:
        pending = conversation.messages.filter(
            role='user',
            created_at__gt=last_response.created_at,
        ).order_by('created_at')
    else:
        pending = conversation.messages.filter(role='user').order_by('created_at')

    if not pending.exists():
        return False

    # Use the last pending message as the "current" message.
    # get_chat_response loads the full history from DB, so the AI
    # sees ALL pending messages in sequence and generates one unified reply.
    last_msg = pending.last()

    response = get_chat_response(conversation, last_msg.content)
    reply = response['text']
    media = response['media']

    # Double-check: has another worker already responded while we were processing?
    new_last = conversation.messages.filter(
        role__in=['assistant', 'admin']
    ).order_by('-created_at').first()
    if last_response and new_last and new_last.pk != last_response.pk:
        return False
    if not last_response and new_last:
        return False

    # Save assistant message
    saved_content = reply
    if media:
        media_lines = '\n'.join(
            f'[media:{item["type"]}]{item["url"]}[/media]' for item in media
        )
        saved_content = f"{reply}\n{media_lines}"
    ChatMessage.objects.create(
        conversation=conversation,
        role=ChatMessage.Role.ASSISTANT,
        content=saved_content,
    )

    # Send via WhatsApp
    send_whatsapp_message(phone, reply)
    for item in media:
        if item['type'] == 'image':
            send_whatsapp_image(phone, item['url'])
        elif item['type'] == 'video':
            send_whatsapp_video(phone, item['url'])

    return True


def _process_messages_async(session_id, phone):
    """Background thread: wait for rapid messages to accumulate, then process."""
    try:
        # Wait for more messages to arrive
        time.sleep(DEBOUNCE_SECONDS)

        # Process all accumulated messages as one
        _process_pending(session_id, phone)

        # Brief wait then check for messages that arrived during processing
        time.sleep(2)
        _process_pending(session_id, phone)

    except Exception as e:
        logger.error(f"Error processing messages for {session_id}: {e}")
    finally:
        with _sessions_lock:
            _active_sessions.discard(session_id)
        close_old_connections()


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):

    def get(self, request):
        """Webhook verification (Meta sends GET to verify)."""
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type='text/plain')

        return HttpResponse('Forbidden', status=403)

    def post(self, request):
        """Receive incoming messages from WhatsApp."""
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extract message data
        for entry in body.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages = value.get('messages', [])

                for msg in messages:
                    if msg.get('type') != 'text':
                        continue

                    phone = msg['from']
                    text = msg['text']['body']

                    logger.info(f"WhatsApp message from {phone}: {text}")

                    # Use phone number as session_id (consistent per user)
                    session_id = phone
                    conversation, created = ChatConversation.objects.get_or_create(
                        session_id=session_id,
                    )
                    if created:
                        assign_conversation_agent(conversation, text)

                    # Save user message immediately
                    ChatMessage.objects.create(
                        conversation=conversation,
                        role=ChatMessage.Role.USER,
                        content=text,
                    )

                    # Skip AI if paused by admin
                    if conversation.is_ai_paused:
                        logger.info(f"AI paused for {phone}, skipping response")
                        continue

                    # Debounce: only start processing if no thread is already
                    # waiting/processing for this session
                    with _sessions_lock:
                        if session_id in _active_sessions:
                            logger.info(f"Debounce: {phone} already active, message queued")
                            continue
                        _active_sessions.add(session_id)

                    threading.Thread(
                        target=_process_messages_async,
                        args=(session_id, phone),
                        daemon=True,
                    ).start()

        return JsonResponse({'status': 'ok'})
