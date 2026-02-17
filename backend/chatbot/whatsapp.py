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

                    # Get AI response
                    reply = get_chat_response(conversation, text)

                    # Save assistant message
                    ChatMessage.objects.create(
                        conversation=conversation,
                        role=ChatMessage.Role.ASSISTANT,
                        content=reply,
                    )

                    # Send reply via WhatsApp
                    send_whatsapp_message(phone, reply)

        return JsonResponse({'status': 'ok'})
