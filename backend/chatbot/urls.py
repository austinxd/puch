from django.urls import path
from .views import ChatView, ConversationListView, ChatHistoryView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/<uuid:session_id>/', ChatHistoryView.as_view(), name='chat-history'),
]
