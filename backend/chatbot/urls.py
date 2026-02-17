from django.urls import path
from .views import ChatView, ChatHistoryView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/<uuid:session_id>/', ChatHistoryView.as_view(), name='chat-history'),
]
