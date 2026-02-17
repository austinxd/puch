from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Agent, Appointment, Property, PropertyImage, PropertyVideo
from .serializers import (
    AgentSerializer, AppointmentSerializer, PropertySerializer,
    PropertyListSerializer, PropertyImageSerializer, PropertyVideoSerializer,
)


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    search_fields = ['name', 'email']


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.select_related('agent').prefetch_related('images', 'videos').all()
    filterset_fields = ['clase', 'operacion', 'distrito', 'activo']
    search_fields = ['identificador', 'nombre', 'distrito', 'tipologia', 'pitch']
    ordering_fields = ['precio', 'created_at', 'nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        return PropertySerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('property', 'agent').all()
    serializer_class = AppointmentSerializer
    filterset_fields = ['status', 'agent']
    search_fields = ['client_name', 'client_phone', 'property__identificador']
    ordering_fields = ['datetime_start', 'created_at']


class PropertyImageView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, property_id):
        prop = get_object_or_404(Property, pk=property_id)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)
        order = request.data.get('order', 0)
        img = PropertyImage.objects.create(property=prop, image=image_file, order=order)
        serializer = PropertyImageSerializer(img, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PropertyImageDetailView(APIView):
    def patch(self, request, property_id, image_id):
        img = get_object_or_404(PropertyImage, pk=image_id, property_id=property_id)
        order = request.data.get('order')
        if order is not None:
            img.order = order
            img.save(update_fields=['order'])
        serializer = PropertyImageSerializer(img, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, property_id, image_id):
        img = get_object_or_404(PropertyImage, pk=image_id, property_id=property_id)
        img.image.delete(save=False)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
