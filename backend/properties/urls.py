from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AgentViewSet, PropertyViewSet, AppointmentViewSet,
    CalendarEventsView,
    PropertyImageView, PropertyImageDetailView, ImageTagsView,
    PropertyVideoView, PropertyVideoDetailView,
)
from .google_auth import GoogleConnectView, GoogleCallbackView, DisconnectGoogleView
from .auth_views import LoginView, LogoutView, MeView, MyProfileView

router = DefaultRouter()
router.register(r'properties', PropertyViewSet)
router.register(r'agents', AgentViewSet)
router.register(r'appointments', AppointmentViewSet)

urlpatterns = [
    # Auth
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/profile/', MyProfileView.as_view(), name='auth-profile'),
    # Property media (before router so they don't get caught by properties/<pk>/)
    path('properties/image-tags/', ImageTagsView.as_view(), name='image-tags'),
    path('properties/<int:property_id>/images/', PropertyImageView.as_view(), name='property-images'),
    path('properties/<int:property_id>/images/<int:image_id>/', PropertyImageDetailView.as_view(), name='property-image-detail'),
    path('properties/<int:property_id>/videos/', PropertyVideoView.as_view(), name='property-videos'),
    path('properties/<int:property_id>/videos/<int:video_id>/', PropertyVideoDetailView.as_view(), name='property-video-detail'),
    path('', include(router.urls)),
    # Calendar events
    path('calendar/events/', CalendarEventsView.as_view(), name='calendar-events'),
    # Google Calendar OAuth
    path('google/connect/<int:agent_id>/', GoogleConnectView.as_view(), name='google-connect'),
    path('google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
    path('agents/<int:agent_id>/disconnect-google/', DisconnectGoogleView.as_view(), name='google-disconnect'),
]
