import json
import logging
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import ChatConversation, ChatMessage
from .services import get_chat_response

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


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
                    conversation, _ = ChatConversation.objects.get_or_create(
                        session_id=session_id,
                    )

                    # Save user message
                    ChatMessage.objects.create(
                        conversation=conversation,
                        role=ChatMessage.Role.USER,
                        content=text,
                    )

                    # Get AI response (now returns dict with text and media)
                    response = get_chat_response(conversation, text)
                    reply = response['text']
                    media = response['media']

                    # Save assistant message
                    ChatMessage.objects.create(
                        conversation=conversation,
                        role=ChatMessage.Role.ASSISTANT,
                        content=reply,
                    )

                    # Send text reply via WhatsApp
                    send_whatsapp_message(phone, reply)

                    # Send media natively
                    for item in media:
                        if item['type'] == 'image':
                            send_whatsapp_image(phone, item['url'])
                        elif item['type'] == 'video':
                            send_whatsapp_video(phone, item['url'])

        return JsonResponse({'status': 'ok'})
