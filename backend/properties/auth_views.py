from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'error': 'Usuario y contraseña son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(_user_payload(user, token.key))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'status': 'ok'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token = request.user.auth_token.key
        return Response(_user_payload(request.user, token))


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agent = getattr(request.user, 'agent_profile', None)
        if not agent:
            return Response(
                {'error': 'No hay perfil de agente vinculado'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            'id': agent.id,
            'name': agent.name,
            'phone': agent.phone,
            'email': agent.email,
            'google_calendar_connected': agent.google_calendar_connected,
        })

    def patch(self, request):
        agent = getattr(request.user, 'agent_profile', None)
        if not agent:
            return Response(
                {'error': 'No hay perfil de agente vinculado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        for field in ('name', 'phone', 'email'):
            value = request.data.get(field)
            if value is not None:
                setattr(agent, field, value)
        agent.save()

        return Response({
            'id': agent.id,
            'name': agent.name,
            'phone': agent.phone,
            'email': agent.email,
            'google_calendar_connected': agent.google_calendar_connected,
        })


def _user_payload(user, token):
    agent = getattr(user, 'agent_profile', None)
    return {
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_staff,
            'agent_id': agent.id if agent else None,
            'agent_name': agent.name if agent else user.username,
        },
    }
