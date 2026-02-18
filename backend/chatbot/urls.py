from django.urls import path
from .views import ChatView, ConversationListView, ChatHistoryView, SystemPromptView, PromptAnalysisView
from .whatsapp import WhatsAppWebhookView
from .analytics import AnalyticsView, IntentListView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/<str:session_id>/', ChatHistoryView.as_view(), name='chat-history'),
    path('whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('intents/', IntentListView.as_view(), name='intent-list'),
    path('prompt/', SystemPromptView.as_view(), name='system-prompt'),
    path('prompt/analyze/', PromptAnalysisView.as_view(), name='prompt-analyze'),
]
