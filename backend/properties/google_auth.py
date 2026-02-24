import logging
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from google_auth_oauthlib.flow import Flow

from .models import Agent

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


def _build_flow():
    """Build Google OAuth flow from settings."""
    client_config = {
        'web': {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


class GoogleConnectView(APIView):
    """Redirects to Google OAuth consent screen for an agent."""
    permission_classes = [AllowAny]

    def get(self, request, agent_id):
        # Browser redirects can't send auth headers, so accept token via query param
        user = request.user
        if not user or not user.is_authenticated:
            token_key = request.query_params.get('token')
            if token_key:
                from rest_framework.authtoken.models import Token
                try:
                    token = Token.objects.select_related('user').get(key=token_key)
                    user = token.user
                except Token.DoesNotExist:
                    return Response(
                        {'error': 'Token inválido'},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            else:
                return Response(
                    {'error': 'No autorizado'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # Non-admin can only connect their own calendar
        if not user.is_staff:
            agent = getattr(user, 'agent_profile', None)
            if not agent or agent.id != agent_id:
                return Response(
                    {'error': 'No autorizado'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response(
                {'error': 'Agente no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Encode source in state: agent_id:source
        source = request.query_params.get('source', 'admin')
        state = f'{agent_id}:{source}'

        flow = _build_flow()
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=state,
        )
        return redirect(authorization_url)


class GoogleCallbackView(APIView):
    """Handles Google OAuth callback, stores tokens on the agent."""
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state', '')
        error = request.GET.get('error')

        # Parse state: "agent_id:source" or just "agent_id"
        parts = state.split(':', 1)
        agent_id = parts[0]
        source = parts[1] if len(parts) > 1 else 'admin'

        if error:
            logger.error(f"Google OAuth error: {error}")
            redirect_url = self._build_redirect(agent_id, source, 'error')
            return redirect(redirect_url)

        if not code or not agent_id:
            return Response(
                {'error': 'Faltan parámetros'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response(
                {'error': 'Agente no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            flow = _build_flow()
            flow.fetch_token(code=code)
            credentials = flow.credentials

            agent.google_access_token = credentials.token
            agent.google_refresh_token = credentials.refresh_token or agent.google_refresh_token
            agent.google_token_expiry = credentials.expiry
            agent.google_calendar_connected = True
            agent.save()

            logger.info(f"Google Calendar connected for agent {agent.id} ({agent.name})")
            redirect_url = self._build_redirect(agent.id, source, 'connected')
            return redirect(redirect_url)
        except Exception as e:
            logger.error(f"Error exchanging Google token for agent {agent_id}: {e}")
            redirect_url = self._build_redirect(agent_id, source, 'error')
            return redirect(redirect_url)

    def _build_redirect(self, agent_id, source, result):
        base = 'https://admin.brikia.tech'
        if source == 'profile':
            return f'{base}/profile?google={result}'
        return f'{base}/agents/{agent_id}/edit?google={result}'


class DisconnectGoogleView(APIView):
    """Disconnects Google Calendar for an agent."""
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        # Non-admin can only disconnect their own calendar
        if not request.user.is_staff:
            agent = getattr(request.user, 'agent_profile', None)
            if not agent or agent.id != agent_id:
                return Response(
                    {'error': 'No autorizado'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response(
                {'error': 'Agente no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        agent.google_access_token = ''
        agent.google_refresh_token = ''
        agent.google_token_expiry = None
        agent.google_calendar_connected = False
        agent.save()

        logger.info(f"Google Calendar disconnected for agent {agent.id} ({agent.name})")
        return Response({'status': 'disconnected'})
