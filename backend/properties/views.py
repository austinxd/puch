from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Agent, Property
from .serializers import AgentSerializer, PropertySerializer, PropertyListSerializer


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    search_fields = ['name', 'email']


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.select_related('agent').all()
    filterset_fields = ['clase', 'operacion', 'distrito', 'activo']
    search_fields = ['identificador', 'nombre', 'distrito', 'tipologia', 'pitch']
    ordering_fields = ['precio', 'created_at', 'nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        return PropertySerializer
