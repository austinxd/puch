from rest_framework import serializers
from .models import Agent, Property


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = '__all__'


class PropertyListSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True, default='')

    class Meta:
        model = Property
        fields = [
            'id', 'identificador', 'nombre', 'clase', 'operacion',
            'distrito', 'precio', 'metraje', 'tipologia', 'activo',
            'agent', 'agent_name', 'imagen_1',
        ]


class PropertySerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True, default='')

    class Meta:
        model = Property
        fields = '__all__'
