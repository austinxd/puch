from datetime import date, timedelta

from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Agent, Appointment, Property, PropertyImage, PropertyVideo
from .permissions import IsAdmin
from .serializers import (
    AgentSerializer, AppointmentSerializer, PropertySerializer,
    PropertyListSerializer, PropertyImageSerializer, PropertyVideoSerializer,
)
from .calendar_service import get_calendar_events


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    search_fields = ['name', 'email']
    permission_classes = [IsAdmin]


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.select_related('agent').prefetch_related('images', 'videos').all()
    filterset_fields = ['clase', 'operacion', 'distrito', 'activo']
    search_fields = ['identificador', 'nombre', 'distrito', 'tipologia', 'pitch']
    ordering_fields = ['precio', 'created_at', 'nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        return PropertySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(agent=self.request.user.agent_profile)
        return qs

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            serializer.save(agent=self.request.user.agent_profile)
        else:
            serializer.save()


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('property', 'agent').all()
    serializer_class = AppointmentSerializer
    filterset_fields = ['status', 'agent']
    search_fields = ['client_name', 'client_phone', 'property__identificador']
    ordering_fields = ['datetime_start', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(agent=self.request.user.agent_profile)
        return qs


class CalendarEventsView(APIView):
    """Fetch Google Calendar events for connected agents."""

    def get(self, request):
        date_from = request.query_params.get('from', date.today().strftime('%Y-%m-%d'))
        date_to = request.query_params.get('to', (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'))

        if request.user.is_staff:
            agents = Agent.objects.exclude(google_calendar_id='')
        else:
            agents = Agent.objects.filter(
                id=request.user.agent_profile.id,
            ).exclude(google_calendar_id='')

        all_events = []
        for agent in agents:
            result = get_calendar_events(agent.id, date_from, date_to)
            if isinstance(result, list):
                all_events.extend(result)

        all_events.sort(key=lambda e: e.get('start', ''))
        return Response(all_events)


class PropertyImageView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, property_id):
        prop = get_object_or_404(Property, pk=property_id)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)
        order = request.data.get('order', 0)
        tag = request.data.get('tag', '')
        img = PropertyImage.objects.create(property=prop, image=image_file, order=order, tag=tag)
        serializer = PropertyImageSerializer(img, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PropertyImageDetailView(APIView):
    def patch(self, request, property_id, image_id):
        img = get_object_or_404(PropertyImage, pk=image_id, property_id=property_id)
        update_fields = []
        order = request.data.get('order')
        if order is not None:
            img.order = order
            update_fields.append('order')
        tag = request.data.get('tag')
        if tag is not None:
            img.tag = tag
            update_fields.append('tag')
        if update_fields:
            img.save(update_fields=update_fields)
        serializer = PropertyImageSerializer(img, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, property_id, image_id):
        img = get_object_or_404(PropertyImage, pk=image_id, property_id=property_id)
        img.image.delete(save=False)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ImageTagsView(APIView):
    def get(self, request):
        return Response(PropertyImage.COMMON_TAGS)


class PropertyVideoView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, property_id):
        prop = get_object_or_404(Property, pk=property_id)
        video_file = request.FILES.get('video')
        if not video_file:
            return Response({'error': 'No video file provided'}, status=status.HTTP_400_BAD_REQUEST)
        vid = PropertyVideo.objects.create(property=prop, video=video_file)
        serializer = PropertyVideoSerializer(vid, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PropertyVideoDetailView(APIView):
    def delete(self, request, property_id, video_id):
        vid = get_object_or_404(PropertyVideo, pk=video_id, property_id=property_id)
        vid.video.delete(save=False)
        vid.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
