from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Agent, Appointment, Property, PropertyImage, PropertyVideo

User = get_user_model()


class AgentSerializer(serializers.ModelSerializer):
    google_calendar_connected = serializers.SerializerMethodField()
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Agent
        fields = ['id', 'name', 'phone', 'email', 'google_calendar_id', 'google_calendar_connected', 'username', 'password']

    def get_google_calendar_connected(self, obj):
        return bool(obj.google_calendar_id)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user:
            data['username'] = instance.user.username
        else:
            data['username'] = ''
        return data

    def create(self, validated_data):
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        agent = Agent.objects.create(**validated_data)
        if username and password:
            user = User.objects.create_user(username=username, password=password)
            agent.user = user
            agent.save()
        return agent

    def update(self, instance, validated_data):
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if username or password:
            if instance.user:
                if username:
                    instance.user.username = username
                if password:
                    instance.user.set_password(password)
                instance.user.save()
            elif username and password:
                user = User.objects.create_user(username=username, password=password)
                instance.user = user
                instance.save()

        return instance


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
