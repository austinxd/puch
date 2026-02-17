from django.urls import path
from .views import ChatView, ConversationListView, ChatHistoryView
from .whatsapp import WhatsAppWebhookView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/<str:session_id>/', ChatHistoryView.as_view(), name='chat-history'),
    path('whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
]
