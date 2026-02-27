from django.urls import path
from .views import (
    ChatView, ConversationListView, ChatHistoryView, SystemPromptView,
    PromptAnalysisView, AdminReplyView, AdminUnpauseView, ChatDebugView,
)
from .whatsapp import WhatsAppWebhookView
from .analytics import AnalyticsView, IntentListView, DealAnalysisView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/<str:session_id>/', ChatHistoryView.as_view(), name='chat-history'),
    path('chat/<str:session_id>/reply/', AdminReplyView.as_view(), name='admin-reply'),
    path('chat/<str:session_id>/unpause/', AdminUnpauseView.as_view(), name='admin-unpause'),
    path('chat/<str:session_id>/debug/', ChatDebugView.as_view(), name='chat-debug'),
    path('whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('intents/', IntentListView.as_view(), name='intent-list'),
    path('prompt/', SystemPromptView.as_view(), name='system-prompt'),
    path('prompt/analyze/', PromptAnalysisView.as_view(), name='prompt-analyze'),
    path('analytics/ai-analysis/', DealAnalysisView.as_view(), name='deal-analysis'),
]
