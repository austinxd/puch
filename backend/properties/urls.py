from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentViewSet, PropertyViewSet

router = DefaultRouter()
router.register(r'properties', PropertyViewSet)
router.register(r'agents', AgentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
