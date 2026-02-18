from rest_framework import serializers
from .models import Agent, Appointment, Property, PropertyImage, PropertyVideo


class AgentSerializer(serializers.ModelSerializer):
    google_calendar_connected = serializers.BooleanField(read_only=True)

    class Meta:
        model = Agent
        fields = ['id', 'name', 'phone', 'email', 'google_calendar_connected']


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'order', 'tag']


class PropertyVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyVideo
        fields = ['id', 'video']


class PropertyListSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True, default='')
    first_image = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'identificador', 'nombre', 'clase', 'operacion',
            'distrito', 'precio', 'moneda', 'metraje', 'tipologia', 'activo',
            'agent', 'agent_name', 'first_image',
        ]

    def get_first_image(self, obj):
        first = obj.images.first()
        if first:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first.image.url)
            return first.image.url
        return None


class PropertySerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True, default='')
    images = PropertyImageSerializer(many=True, read_only=True)
    videos = PropertyVideoSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = '__all__'


class AppointmentSerializer(serializers.ModelSerializer):
    property_identifier = serializers.CharField(source='property.identificador', read_only=True)
    property_name = serializers.CharField(source='property.nombre', read_only=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'property', 'property_identifier', 'property_name',
            'agent', 'agent_name', 'client_name', 'client_phone',
            'datetime_start', 'datetime_end', 'google_event_id',
            'status', 'conversation_session_id', 'created_at', 'updated_at',
        ]
        read_only_fields = ['google_event_id', 'created_at', 'updated_at']
