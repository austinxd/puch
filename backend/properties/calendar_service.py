import logging
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import Agent, Appointment, Property

logger = logging.getLogger(__name__)

TIMEZONE = 'America/Lima'
BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 18
# Monday=0 ... Saturday=5; Sunday=6 is excluded
BUSINESS_DAYS = {0, 1, 2, 3, 4, 5}  # Lunes a Sábado
SLOT_DURATION_MINUTES = 60


def get_google_credentials(agent):
    """Build Google Credentials for an agent, refreshing the token if expired."""
    if not agent.google_access_token:
        return None

    creds = Credentials(
        token=agent.google_access_token,
        refresh_token=agent.google_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            agent.google_access_token = creds.token
            agent.google_token_expiry = creds.expiry
            agent.save(update_fields=['google_access_token', 'google_token_expiry'])
        except Exception as e:
            logger.error(f"Error refreshing token for agent {agent.id}: {e}")
            agent.google_calendar_connected = False
            agent.save(update_fields=['google_calendar_connected'])
            return None

    return creds


def _get_calendar_service(agent):
    """Get a Google Calendar API service for the given agent."""
    creds = get_google_credentials(agent)
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)


def check_availability(agent_id, date_str, time_str=None):
    """
    Check available slots for an agent on a given date.

    Args:
        agent_id: ID of the agent
        date_str: Date string in YYYY-MM-DD format
        time_str: Optional time string in HH:MM format to check a specific slot

    Returns:
        dict with available_slots list or specific slot availability
    """
    try:
        agent = Agent.objects.get(pk=agent_id)
    except Agent.DoesNotExist:
        return {'error': 'Agente no encontrado'}

    if not agent.google_calendar_connected:
        return {'error': 'El agente no tiene Google Calendar conectado'}

    service = _get_calendar_service(agent)
    if not service:
        return {'error': 'No se pudo conectar con Google Calendar'}

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return {'error': f'Formato de fecha inválido: {date_str}. Usa YYYY-MM-DD'}

    # Check if it's a business day
    if target_date.weekday() not in BUSINESS_DAYS:
        return {
            'available': False,
            'available_slots': [],
            'message': 'Ese día es domingo. Solo atendemos de lunes a sábado.',
        }

    # Build time range for the day
    tz = ZoneInfo(TIMEZONE)
    day_start = datetime.combine(target_date, dt_time(hour=BUSINESS_START_HOUR), tzinfo=tz)
    day_end = datetime.combine(target_date, dt_time(hour=BUSINESS_END_HOUR), tzinfo=tz)

    # Query Google Calendar freebusy
    body = {
        'timeMin': day_start.isoformat(),
        'timeMax': day_end.isoformat(),
        'timeZone': TIMEZONE,
        'items': [{'id': 'primary'}],
    }

    try:
        result = service.freebusy().query(body=body).execute()
    except Exception as e:
        logger.error(f"Error querying freebusy for agent {agent_id}: {e}")
        return {'error': 'Error al consultar disponibilidad en Google Calendar'}

    busy_periods = result.get('calendars', {}).get('primary', {}).get('busy', [])

    # Parse busy periods
    busy_slots = []
    for period in busy_periods:
        start = datetime.fromisoformat(period['start'])
        end = datetime.fromisoformat(period['end'])
        busy_slots.append((start, end))

    # If checking a specific time
    if time_str:
        try:
            hour, minute = map(int, time_str.split(':'))
            slot_start = datetime.combine(target_date, dt_time(hour=hour, minute=minute), tzinfo=tz)
            slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
        except ValueError:
            return {'error': f'Formato de hora inválido: {time_str}. Usa HH:MM'}

        if slot_start < day_start or slot_end > day_end:
            return {
                'available': False,
                'message': f'Horario fuera del rango de atención ({BUSINESS_START_HOUR}:00 - {BUSINESS_END_HOUR}:00)',
            }

        is_free = all(
            slot_end <= busy_start or slot_start >= busy_end
            for busy_start, busy_end in busy_slots
        )

        return {
            'available': is_free,
            'date': date_str,
            'time': time_str,
            'message': 'Horario disponible' if is_free else 'Horario ocupado',
        }

    # Generate all available slots
    available_slots = []
    current = day_start
    while current + timedelta(minutes=SLOT_DURATION_MINUTES) <= day_end:
        slot_end = current + timedelta(minutes=SLOT_DURATION_MINUTES)
        is_free = all(
            slot_end <= busy_start or current >= busy_end
            for busy_start, busy_end in busy_slots
        )
        if is_free:
            available_slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=SLOT_DURATION_MINUTES)

    return {
        'date': date_str,
        'available_slots': available_slots,
        'message': f'{len(available_slots)} horarios disponibles' if available_slots else 'No hay horarios disponibles para esta fecha',
    }


def create_appointment(agent_id, property_id, client_name, client_phone, date_str, time_str, session_id=''):
    """
    Create an appointment on Google Calendar and in local DB.

    Args:
        agent_id: ID of the agent
        property_id: ID or identificador of the property
        client_name: Client's name
        client_phone: Client's phone number
        date_str: Date string in YYYY-MM-DD format
        time_str: Time string in HH:MM format
        session_id: Chat session ID

    Returns:
        dict with appointment details or error
    """
    try:
        agent = Agent.objects.get(pk=agent_id)
    except Agent.DoesNotExist:
        return {'error': 'Agente no encontrado'}

    if not agent.google_calendar_connected:
        return {'error': 'El agente no tiene Google Calendar conectado'}

    # Find property by ID or identificador
    try:
        prop = Property.objects.get(pk=property_id)
    except (Property.DoesNotExist, ValueError):
        try:
            prop = Property.objects.get(identificador=property_id)
        except Property.DoesNotExist:
            return {'error': f'Propiedad no encontrada: {property_id}'}

    # Verify availability first
    availability = check_availability(agent_id, date_str, time_str)
    if availability.get('error'):
        return availability
    if not availability.get('available', False):
        return {
            'error': 'El horario seleccionado no está disponible',
            'available_slots': availability.get('available_slots', []),
        }

    service = _get_calendar_service(agent)
    if not service:
        return {'error': 'No se pudo conectar con Google Calendar'}

    # Build event
    tz = ZoneInfo(TIMEZONE)
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        hour, minute = map(int, time_str.split(':'))
        start_dt = datetime.combine(target_date, dt_time(hour=hour, minute=minute), tzinfo=tz)
        end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MINUTES)
    except ValueError as e:
        return {'error': f'Error en formato de fecha/hora: {e}'}

    location = prop.direccion or prop.calle or prop.distrito
    event = {
        'summary': f'Visita: {prop.identificador} - {client_name}',
        'location': location,
        'description': (
            f'Visita a propiedad {prop.identificador} - {prop.nombre}\n'
            f'Cliente: {client_name}\n'
            f'Teléfono: {client_phone}\n'
            f'Dirección: {location}\n'
            f'Agendado desde chatbot Brikia'
        ),
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': TIMEZONE,
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': TIMEZONE,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }

    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
    except Exception as e:
        logger.error(f"Error creating Google Calendar event for agent {agent_id}: {e}")
        return {'error': 'Error al crear el evento en Google Calendar'}

    # Create local appointment record
    appointment = Appointment.objects.create(
        property=prop,
        agent=agent,
        client_name=client_name,
        client_phone=client_phone,
        datetime_start=start_dt,
        datetime_end=end_dt,
        google_event_id=created_event.get('id', ''),
        status=Appointment.Status.SCHEDULED,
        conversation_session_id=session_id,
    )

    return {
        'success': True,
        'appointment_id': appointment.id,
        'property': prop.identificador,
        'property_name': prop.nombre,
        'client_name': client_name,
        'date': date_str,
        'time': time_str,
        'agent': agent.name,
        'message': f'Cita agendada para {client_name} el {date_str} a las {time_str} en {prop.identificador} - {prop.nombre}',
    }
