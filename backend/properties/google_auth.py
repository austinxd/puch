import logging
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse
from django.utils import timezone
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

    def get(self, request, agent_id):
        try:
            Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response(
                {'error': 'Agente no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        flow = _build_flow()
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=str(agent_id),
        )
        return redirect(authorization_url)


class GoogleCallbackView(APIView):
    """Handles Google OAuth callback, stores tokens on the agent."""

    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')

        if error:
            logger.error(f"Google OAuth error: {error}")
            return redirect(
                f'https://admin.brikia.tech/agents/{state}/edit?google=error'
            )

        if not code or not state:
            return Response(
                {'error': 'Faltan parámetros'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agent = Agent.objects.get(pk=state)
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
            return redirect(
                f'https://admin.brikia.tech/agents/{agent.id}/edit?google=connected'
            )
        except Exception as e:
            logger.error(f"Error exchanging Google token for agent {state}: {e}")
            return redirect(
                f'https://admin.brikia.tech/agents/{state}/edit?google=error'
            )


class DisconnectGoogleView(APIView):
    """Disconnects Google Calendar for an agent."""

    def post(self, request, agent_id):
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
