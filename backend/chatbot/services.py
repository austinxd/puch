import json
import re
import logging
from datetime import date

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from openai import OpenAI
from properties.models import Property, Agent, Appointment
from properties.calendar_service import check_availability, create_appointment

logger = logging.getLogger(__name__)


def get_system_prompt():
    """Read the system prompt from DB, with fallback to a default message."""
    from .models import SystemPrompt
    try:
        return SystemPrompt.objects.get(pk=1).content
    except SystemPrompt.DoesNotExist:
        return "Eres Erika, asesora inmobiliaria virtual de Brikia en Lima, Perú."


SEARCH_STOPWORDS = {
    'busco', 'quiero', 'necesito', 'un', 'una', 'el', 'la', 'los', 'las',
    'de', 'en', 'con', 'para', 'por', 'que', 'es', 'y', 'o', 'me', 'mi',
    'hay', 'tiene', 'tienen', 'algo', 'como', 'más', 'mas', 'muy', 'bien',
    'hola', 'gracias', 'favor', 'puedes', 'puedo', 'sí', 'si', 'no',
    'a', 'al', 'del', 'se', 'lo', 'le', 'su', 'sus', 'este', 'esta',
    'información', 'informacion', 'info', 'sobre', 'detalles',
    'ver', 'foto', 'fotos', 'video', 'videos', 'imagen', 'imágenes',
    'precio', 'cita', 'visita', 'agendar', 'sacame', 'sacar', 'mañana',
    'hoy', 'pasado', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes',
    'sábado', 'domingo', 'porfavor', 'por', 'quiero', 'quisiera',
    'recorrido', 'enviar', 'mandar', 'dame', 'dime', 'puedo',
    'otra', 'otro', 'más', 'también', 'tambien', 'todas', 'todos',
    # Common follow-up verbs that cause false positive matches
    'pasa', 'pasar', 'paso', 'cuenta', 'contar', 'manda', 'mande',
    'buenas', 'buenos', 'buena', 'bueno', 'noches', 'noche', 'tardes',
    'tarde', 'dias', 'nombre', 'llamo', 'llama', 'soy',
    'ubicacion', 'ubicación', 'direccion', 'dirección',
    'puede', 'podria', 'podría', 'seria', 'sería', 'gustaria', 'gustaría',
    'igual', 'quiere', 'confirmo', 'confirmar', 'efectivo', 'listo', 'lista',
}


def _extract_keywords(text):
    """Extract meaningful keywords from text, filtering stopwords."""
    words = re.findall(r'\w+', text.lower())
    return [w for w in words if w not in SEARCH_STOPWORDS and len(w) > 2]


SEARCH_SYNONYMS = {
    'dormitorio': 'habitacion',
    'dormitorios': 'habitaciones',
    'cuarto': 'habitacion',
    'cuartos': 'habitaciones',
    'baño': 'bano',
    'baños': 'banos',
    'estacionamiento': 'cochera',
    'estacionamientos': 'cocheras',
    'garage': 'cochera',
    'primer': 'primer',
    'primero': 'primer',
}


def _search_by_text(text):
    """Search properties by a text string using identifier, keyword, and broad strategies.

    Returns a queryset of matching properties, or an empty queryset if nothing matches.
    """
    keywords = _extract_keywords(text)
    if not keywords:
        return Property.objects.none()

    # Expand synonyms: add the synonym as an extra search term
    expanded = list(keywords)
    for kw in keywords:
        syn = SEARCH_SYNONYMS.get(kw)
        if syn and syn not in expanded:
            expanded.append(syn)

    base_qs = Property.objects.filter(activo=True).select_related('agent').prefetch_related('images', 'videos')

    # Step 1: Exact identifier match (highest priority)
    id_filter = Q()
    for kw in expanded:
        id_filter |= Q(identificador__iexact=kw)
    id_matches = base_qs.filter(id_filter)
    if id_matches.exists():
        return id_matches[:10]

    # Step 2: Full keyword search across all property fields + agent name
    keyword_filter = Q()
    for kw in expanded:
        keyword_filter |= (
            Q(distrito__icontains=kw) |
            Q(tipologia__icontains=kw) |
            Q(nombre__icontains=kw) |
            Q(pitch__icontains=kw) |
            Q(clase__icontains=kw) |
            Q(operacion__icontains=kw) |
            Q(habitaciones__icontains=kw) |
            Q(piso__icontains=kw) |
            Q(calle__icontains=kw) |
            Q(agent__name__icontains=kw)
        )

    # Apply price filter if mentioned
    price_match = re.search(r'(\d[\d,\.]*)\s*(mil|k|soles|dolares|usd|\$)', text.lower())
    if price_match:
        price_str = price_match.group(1).replace(',', '').replace('.', '')
        multiplier = 1000 if price_match.group(2) in ('mil', 'k') else 1
        try:
            price = float(price_str) * multiplier
            keyword_filter &= Q(precio__lte=price * 1.2)
        except ValueError:
            pass

    properties = base_qs.filter(keyword_filter)[:10]

    # Step 3: Broader fallback (only distrito, tipologia, agent name)
    if not properties.exists():
        broad_filter = Q()
        for kw in keywords[:5]:
            broad_filter |= Q(distrito__icontains=kw) | Q(tipologia__icontains=kw) | Q(agent__name__icontains=kw)
        properties = base_qs.filter(broad_filter)[:10]

    return properties


def assign_conversation_agent(conversation, first_message):
    """Assign the conversation to the agent of the first property mentioned."""
    results = _search_by_text(first_message)
    if results.exists():
        prop = results.first()
        if prop.agent:
            conversation.agent = prop.agent
            conversation.save(update_fields=['agent'])


def _find_conversation_property(conversation_messages, base_qs):
    """Find the main property being discussed from conversation history.

    Checks ALL messages (user + assistant) for property identifiers.
    The most recently mentioned property wins (latest in conversation).
    """
    if not conversation_messages:
        return None
    # Collect all keywords from user AND assistant messages
    # (the bot may mention a property identifier the user never typed)
    all_keywords = []
    for msg in conversation_messages:
        all_keywords.extend(_extract_keywords(msg['content']))
    if not all_keywords:
        return None
    # Single query: check if any keyword matches a property identifier
    id_filter = Q()
    for kw in set(all_keywords):
        id_filter |= Q(identificador__iexact=kw)
    matches = list(base_qs.filter(id_filter)[:5])

    # Fallback: also check assistant messages for property names (e.g. "Santo Toribio")
    if len(matches) <= 1:
        all_props = list(base_qs.values_list('id', 'identificador', 'nombre', 'calle'))
        for prop_id, ident, nombre, calle in all_props:
            if ident.lower() in {kw.lower() for kw in all_keywords}:
                continue  # already matched by identifier
            # Check if property name words appear in assistant messages
            for msg in conversation_messages:
                if msg.get('role') != 'assistant':
                    continue
                content_lower = msg['content'].lower()
                name_words = [w for w in re.findall(r'\w+', nombre.lower()) if len(w) > 3]
                if name_words and all(w in content_lower for w in name_words):
                    # Found a property name match in assistant message - add it
                    prop_obj = base_qs.filter(id=prop_id).first()
                    if prop_obj and prop_obj not in matches:
                        matches.append(prop_obj)
                    break

    if not matches:
        return None
    # Return the last match in conversation order (most recently mentioned property wins)
    match_by_id = {m.identificador.lower(): m for m in matches}
    for kw in reversed(all_keywords):
        if kw.lower() in match_by_id:
            return match_by_id[kw.lower()]
    # If no identifier matched in keyword order, return the last name-matched property
    return matches[-1]


def search_properties(current_message, conversation_messages=None):
    """Hybrid property search: try current message first, fall back to full history.

    Always ensures the "active property" (identified from conversation history)
    is included in results, even when the current message matches other properties.
    """
    current_keywords = _extract_keywords(current_message)
    base_qs = Property.objects.filter(activo=True).select_related('agent').prefetch_related('images', 'videos')

    # Always find the "active property" from conversation history
    active_prop = _find_conversation_property(conversation_messages, base_qs)

    # Step 1: Identifier match on current message (always check)
    if current_keywords:
        id_filter = Q()
        for kw in current_keywords:
            id_filter |= Q(identificador__iexact=kw)
        id_matches = base_qs.filter(id_filter)
        if id_matches.exists():
            return id_matches[:10]

    # Step 2: Keyword search on current message
    if len(current_keywords) >= 2:
        results = _search_by_text(current_message)
        if results.exists():
            # If results don't include the active property, add it
            if active_prop:
                result_ids = set(results.values_list('id', flat=True))
                if active_prop.id not in result_ids:
                    logger.info(f"Search returned {list(result_ids)} but active property is {active_prop.identificador}, adding it")
                    return base_qs.filter(Q(id=active_prop.id) | Q(id__in=result_ids))[:10]
            return results
    elif len(current_keywords) == 1:
        kw = current_keywords[0]
        # Expand synonym for single-keyword search too
        syn = SEARCH_SYNONYMS.get(kw)
        kw_filter = Q(distrito__icontains=kw) | Q(tipologia__icontains=kw) | Q(habitaciones__icontains=kw) | Q(piso__icontains=kw)
        if syn:
            kw_filter |= Q(habitaciones__icontains=syn) | Q(piso__icontains=syn)
        single_kw_qs = base_qs.filter(kw_filter)
        if single_kw_qs.exists():
            if active_prop:
                result_ids = set(single_kw_qs.values_list('id', flat=True))
                if active_prop.id not in result_ids:
                    return base_qs.filter(Q(id=active_prop.id) | Q(id__in=result_ids))[:10]
            return single_kw_qs[:10]

    # Step 3: Return active property if we have one (follow-up questions)
    if active_prop:
        logger.info(f"No current-message match, using active property: {active_prop.identificador}")
        return base_qs.filter(id=active_prop.id)

    # Step 4: Full search on conversation history
    if conversation_messages:
        combined_text = ' '.join(
            msg['content'] for msg in conversation_messages
            if msg.get('role') == 'user'
        )
        return _search_by_text(combined_text)

    return Property.objects.none()


def _get_media_url(file_field):
    """Build an absolute URL for a media file."""
    base_url = getattr(settings, 'BASE_URL', 'https://api.brikia.tech')
    return f"{base_url}{file_field.url}"


def format_property(prop):
    """Format a property for the AI context."""
    lines = [
        f"- PROPIEDAD: {prop.nombre} (Identificador: {prop.identificador})",
        f"  Clase: {prop.clase} | Operación: {prop.operacion}",
        f"  Tipología: {prop.tipologia}" if prop.tipologia else "",
        f"  Distrito: {prop.distrito}",
        f"  Dirección: {prop.direccion}" if prop.direccion else "",
        f"  Calle: {prop.calle}" if prop.calle else "",
        f"  Link Maps: {prop.link_maps}" if prop.link_maps else "",
        f"  Referencia: {prop.referencia}" if prop.referencia else "",
        f"  Precio: ${prop.precio}" if prop.precio else "  Precio: Consultar",
        f"  Metraje: {prop.metraje}" if prop.metraje else "",
        f"  Antigüedad: {prop.antiguedad}" if prop.antiguedad else "",
        f"  Habitaciones: {prop.habitaciones}" if prop.habitaciones else "",
        f"  Baños: {prop.banos}" if prop.banos else "",
        f"  Cocheras: {prop.cocheras}" if prop.cocheras else "",
        f"  Piso: {prop.piso}" if prop.piso else "",
        f"  Cantidad de pisos: {prop.cantidad_pisos}" if prop.cantidad_pisos else "",
        f"  Vista: {prop.vista}" if prop.vista else "",
        f"  Ascensor: {prop.ascensor}" if prop.ascensor else "",
        f"  Tipo cocina: {prop.tipo_cocina}" if prop.tipo_cocina else "",
        f"  Terraza/Balcón: {prop.terraza_balcon}" if prop.terraza_balcon else "",
        f"  Cuarto de servicio: {prop.cuarto_servicio}" if prop.cuarto_servicio else "",
        f"  Baño de servicio: {prop.bano_servicio}" if prop.bano_servicio else "",
        f"  Costo mantenimiento: {prop.costo_mantenimiento}" if prop.costo_mantenimiento else "",
        f"  Distribución: {prop.distribucion}" if prop.distribucion else "",
        f"  Pitch: {prop.pitch}" if prop.pitch else "",
        f"  Documentación: {prop.documentacion}" if prop.documentacion else "",
        f"  Parámetros/Usos: {prop.parametros_usos}" if prop.parametros_usos else "",
        f"  Financiamiento: {prop.financiamiento}" if prop.financiamiento else "",
        f"  Agente: {prop.agent.name} (Tel: {prop.agent.phone}, Email: {prop.agent.email})" if prop.agent else "",
    ]
    images = list(prop.images.all())
    if images:
        tags = set(img.tag for img in images if img.tag)
        tag_info = f" - Áreas: {', '.join(tags)}" if tags else ""
        lines.append(f"  Imágenes disponibles: SÍ ({len(images)} fotos{tag_info})")
    else:
        lines.append("  Imágenes disponibles: NO")
    video = prop.videos.first()
    if video:
        lines.append("  Video disponible: SÍ (usar send_property_media para enviar)")
    else:
        lines.append("  Video disponible: NO")
    if prop.recorrido_360:
        lines.append(f"  Recorrido 360 disponible: SÍ → {prop.recorrido_360}")
    else:
        lines.append("  Recorrido 360 disponible: NO")

    return '\n'.join(line for line in lines if line)


CALENDAR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Verifica los horarios disponibles de un agente para una fecha específica. Usa esto cuando el cliente quiera agendar una visita.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_identifier": {
                        "type": "string",
                        "description": "El identificador de la propiedad (ej: JC980, ST355)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Fecha en formato YYYY-MM-DD",
                    },
                    "time": {
                        "type": "string",
                        "description": "Hora específica en formato HH:MM (opcional, para verificar un horario puntual)",
                    },
                },
                "required": ["property_identifier", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": "Crea una cita para visitar una propiedad. Solo usar cuando el cliente haya confirmado fecha, hora y nombre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_identifier": {
                        "type": "string",
                        "description": "El identificador de la propiedad (ej: JC980, ST355)",
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Nombre completo del cliente",
                    },
                    "client_phone": {
                        "type": "string",
                        "description": "Número de teléfono del cliente (opcional, se usa el de la conversación si no se proporciona)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Fecha en formato YYYY-MM-DD",
                    },
                    "time": {
                        "type": "string",
                        "description": "Hora en formato HH:MM",
                    },
                },
                "required": ["property_identifier", "client_name", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_property_media",
            "description": "Envía las fotos y/o video de una propiedad al cliente. Usa esto cuando el cliente quiera ver fotos, imágenes o video de una propiedad. Puedes filtrar por área específica (sala, cocina, habitacion, bano, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_identifier": {
                        "type": "string",
                        "description": "El identificador de la propiedad (ej: JC980, ST355)",
                    },
                    "media_type": {
                        "type": "string",
                        "enum": ["images", "video", "all"],
                        "description": "Tipo de media a enviar: 'images' para fotos, 'video' para video, 'all' para ambos",
                    },
                    "area": {
                        "type": "string",
                        "description": "Área específica para filtrar imágenes (ej: sala, cocina, habitacion, bano, fachada, terraza, vista, cochera, lobby, piscina, areas_comunes). Si no se especifica, envía todas.",
                    },
                    "max_photos": {
                        "type": "integer",
                        "description": "Número máximo de fotos a enviar (por defecto 5). Aumentar solo si el cliente solicita más fotos.",
                    },
                },
                "required": ["property_identifier", "media_type"],
            },
        },
    },
]


def _has_calendar_agents(properties):
    """Check if any property in the list has an agent with Google Calendar connected."""
    for prop in properties:
        if prop.agent and prop.agent.google_calendar_id:
            return True
    return False


def execute_tool(tool_name, arguments, session_id=''):
    """Execute a tool call and return the result."""
    if tool_name == 'check_availability':
        prop_id = arguments.get('property_identifier', '')
        try:
            prop = Property.objects.select_related('agent').get(identificador=prop_id)
        except Property.DoesNotExist:
            return json.dumps({'error': f'Propiedad {prop_id} no encontrada'}), []

        if not prop.agent:
            return json.dumps({'error': f'La propiedad {prop_id} no tiene agente asignado'}), []

        if not prop.agent.google_calendar_id:
            return json.dumps({
                'error': 'calendar_not_connected',
                'agent_name': prop.agent.name,
                'agent_phone': prop.agent.phone,
            }), []

        result = check_availability(
            agent_id=prop.agent.id,
            date_str=arguments.get('date', ''),
            time_str=arguments.get('time'),
        )
        return json.dumps(result), []

    elif tool_name == 'create_appointment':
        prop_id = arguments.get('property_identifier', '')
        try:
            prop = Property.objects.select_related('agent').get(identificador=prop_id)
        except Property.DoesNotExist:
            return json.dumps({'error': f'Propiedad {prop_id} no encontrada'}), []

        if not prop.agent:
            return json.dumps({'error': f'La propiedad {prop_id} no tiene agente asignado'}), []

        if not prop.agent.google_calendar_id:
            return json.dumps({
                'error': 'calendar_not_connected',
                'agent_name': prop.agent.name,
                'agent_phone': prop.agent.phone,
            }), []

        client_phone = arguments.get('client_phone', '')
        if not client_phone and session_id and len(session_id) >= 7 and session_id.isdigit():
            client_phone = session_id

        result = create_appointment(
            agent_id=prop.agent.id,
            property_id=prop_id,
            client_name=arguments.get('client_name', ''),
            client_phone=client_phone,
            date_str=arguments.get('date', ''),
            time_str=arguments.get('time', ''),
            session_id=session_id,
        )
        return json.dumps(result), []

    elif tool_name == 'send_property_media':
        prop_id = arguments.get('property_identifier', '')
        media_type = arguments.get('media_type', 'all')
        area = arguments.get('area', '')
        try:
            prop = Property.objects.prefetch_related('images', 'videos').get(identificador=prop_id)
        except Property.DoesNotExist:
            return json.dumps({'error': f'Propiedad {prop_id} no encontrada'}), []

        media = []
        image_details = []
        total_images = 0
        if media_type in ('images', 'all'):
            images = prop.images.all()
            if area:
                images = images.filter(tag__iexact=area)
            max_photos = arguments.get('max_photos', 5)
            total_images = images.count()
            images = images[:max_photos]
            for img in images:
                url = _get_media_url(img.image)
                media.append({'type': 'image', 'url': url})
                tag_label = img.tag if img.tag else 'sin etiqueta'
                image_details.append(f"- Imagen ({tag_label}): {url}")
        if media_type in ('video', 'all'):
            video = prop.videos.first()
            if video:
                url = _get_media_url(video.video)
                media.append({'type': 'video', 'url': url})
                image_details.append(f"- Video: {url}")

        area_label = f" del área '{area}'" if area else ""
        if not media:
            result_msg = f"La propiedad {prop_id} no tiene {'imágenes' if media_type == 'images' else 'video' if media_type == 'video' else 'medios'}{area_label} disponibles."
        else:
            remaining = total_images - len([m for m in media if m['type'] == 'image']) if media_type in ('images', 'all') else 0
            result_msg = f"Se enviarán {len(media)} archivos multimedia de la propiedad {prop_id}{area_label}."
            if remaining > 0:
                result_msg += f" Hay {remaining} fotos adicionales disponibles si el cliente desea verlas."
            result_msg += "\nDetalle de lo enviado:\n" + '\n'.join(image_details)
        return json.dumps({'message': result_msg, 'media_count': len(media)}), media

    return json.dumps({'error': f'Función desconocida: {tool_name}'}), []


def extract_intent(conversation):
    """Extract client intent from conversation using AI."""
    if not settings.OPENAI_API_KEY:
        return

    from .models import ClientIntent

    user_messages = conversation.messages.filter(role='user')
    if user_messages.count() < 1:
        return

    messages_text = '\n'.join(f'- {m.content}' for m in user_messages)

    prompt = f"""Analiza los siguientes mensajes de un cliente de una inmobiliaria en Lima, Perú.
Extrae su intención de búsqueda en formato JSON con estos campos exactos:
- "operacion": "Venta" o "Alquiler" o "" si no se menciona
- "tipo_propiedad": tipo que busca (departamento, casa, local, terreno, etc.) o ""
- "distritos": distritos mencionados separados por coma, o ""
- "precio_min": número o null
- "precio_max": número o null
- "habitaciones": cantidad mencionada o ""
- "caracteristicas": otras características mencionadas (cochera, vista, piso, etc.) o ""
- "resumen": resumen breve de lo que busca el cliente en 1-2 oraciones

Mensajes del cliente:
{messages_text}

Responde SOLO el JSON, sin markdown ni explicación."""

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
        data = json.loads(raw)

        ClientIntent.objects.update_or_create(
            conversation=conversation,
            defaults={
                'phone': conversation.session_id if conversation.session_id.isdigit() else '',
                'operacion': data.get('operacion', ''),
                'tipo_propiedad': data.get('tipo_propiedad', ''),
                'distritos': data.get('distritos', ''),
                'precio_min': data.get('precio_min'),
                'precio_max': data.get('precio_max'),
                'habitaciones': data.get('habitaciones', ''),
                'caracteristicas': data.get('caracteristicas', ''),
                'resumen': data.get('resumen', ''),
            },
        )
    except Exception as e:
        logger.error(f"Error extracting intent: {e}")


def get_chat_response(conversation, user_message):
    """Generate a chat response using OpenAI with optional tool calling for calendar and media."""
    if not settings.OPENAI_API_KEY:
        return {
            'text': "Lo siento, el servicio de chat no está configurado. Contacta al administrador.",
            'media': [],
        }

    history = conversation.messages.order_by('-created_at')[:100]
    history = list(reversed(history))

    # Build conversation context for property search fallback (all user messages)
    conversation_msgs = [
        {'role': msg.role, 'content': msg.content}
        for msg in history
    ]
    conversation_msgs.append({'role': 'user', 'content': user_message})

    properties = search_properties(user_message, conversation_messages=conversation_msgs)
    prop_ids = [p.identificador for p in properties] if properties else []
    logger.info(f"[{conversation.session_id}] msg={user_message!r} → properties={prop_ids}")
    property_context = ""
    if properties:
        formatted = [format_property(p) for p in properties]
        property_context = (
            "\n\n=== PROPIEDADES EN BASE DE DATOS ===\n"
            "IMPORTANTE: Solo menciona información que aparece explícitamente aquí. "
            "Si un campo no aparece o dice NO, no inventes ni asumas que existe.\n"
            + "\n\n".join(formatted)
            + "\n=== FIN DE PROPIEDADES ==="
        )

    # Query future scheduled appointments for this conversation
    appointment_context = ""
    appointments = Appointment.objects.filter(
        Q(conversation_session_id=conversation.session_id) |
        Q(client_phone=conversation.session_id),
        status=Appointment.Status.SCHEDULED,
        datetime_start__gte=timezone.now(),
    ).select_related('property', 'agent').order_by('datetime_start')

    if appointments.exists():
        appt_lines = [
            "\n\n=== CITAS ACTIVAS DEL CLIENTE ===",
            "El cliente tiene citas programadas. Ayúdalo con dirección, cómo llegar, detalles de la visita.",
        ]
        for appt in appointments:
            local_dt = timezone.localtime(appt.datetime_start)
            line = f"- Propiedad: {appt.property.nombre} ({appt.property.identificador}) el {local_dt.strftime('%Y-%m-%d')} a las {local_dt.strftime('%H:%M')}"
            appt_lines.append(line)
            if appt.property.direccion:
                appt_lines.append(f"  Dirección: {appt.property.direccion}")
            if appt.property.link_maps:
                appt_lines.append(f"  Link Maps: {appt.property.link_maps}")
            if appt.agent:
                appt_lines.append(f"  Agente: {appt.agent.name} (Tel: {appt.agent.phone})")
        appt_lines.append("=== FIN DE CITAS ===")
        appointment_context = '\n'.join(appt_lines)

    # Inject current date into the system prompt
    system_prompt = get_system_prompt().replace('{current_date}', date.today().strftime('%Y-%m-%d (%A)'))

    media_instructions = (
        "\n\n=== INSTRUCCIONES IMPORTANTES ==="
        "\n\nORDEN DE ENVÍO DE MEDIA:"
        "\n1. Al presentar una propiedad, envía PRIMERO el VIDEO (send_property_media con media_type='video')."
        "\n2. Luego comparte el enlace del RECORRIDO 360 si existe (menciónalo en tu texto)."
        "\n3. Las FOTOS solo se envían si el cliente las pide. NO envíes fotos automáticamente."
        "\n4. Al enviar fotos, se envían máximo 5. Si el cliente quiere más, usa max_photos con un número mayor."
        "\n\nREGLAS DE MEDIA:"
        "\n- NUNCA escribas URLs de imágenes ni videos como texto en tu respuesta. SIEMPRE usa el tool send_property_media."
        "\n- Confía en el resultado del tool. Si reporta éxito, responde con seguridad. NUNCA te disculpes si fue exitoso."
        "\n- Si el cliente pregunta de qué es una foto, responde con seguridad usando el tag de la imagen."
        "\n- NUNCA mezcles información de una propiedad con otra."
        "\n\nINFORMACIÓN DE PROPIEDADES (REGLAS OBLIGATORIAS):"
        "\n- Si la información de una propiedad aparece en el contexto de arriba, ÚSALA. Tienes toda la info disponible."
        "\n- NUNCA digas 'no tengo esa información' o 'no cuento con esos datos' si la info está en el contexto de propiedades."
        "\n- Solo di que no tienes info si realmente NO aparece en el contexto."
        "\n- OBLIGATORIO: SIEMPRE incluye el código identificador entre paréntesis cuando menciones una propiedad. Ejemplo: 'el departamento en San Isidro (ST355)'. Esto aplica CADA VEZ que nombres una propiedad, sin excepción."
        "\n- NUNCA menciones, sugieras ni hables de una propiedad que NO aparece en el contexto de propiedades de arriba. Solo puedes recomendar propiedades que están listadas en '=== PROPIEDADES EN BASE DE DATOS ==='."
        "\n- Si el cliente cambia de criterio (más habitaciones, otro distrito, etc.) y el contexto tiene propiedades que cumplen con lo que pide, recomiéndalas de inmediato con sus datos. NO preguntes si quiere ver opciones cuando ya las tienes disponibles."
        "\n\nAGENTE DE LA PROPIEDAD (CRÍTICO):"
        "\n- Cada propiedad tiene un agente asignado que aparece en el contexto como 'Agente: Nombre (Tel: ..., Email: ...)'."
        "\n- Cuando necesites referir al cliente con un agente, SIEMPRE usa el nombre y teléfono del agente que aparece en la ficha de ESA propiedad."
        "\n- NUNCA inventes ni asumas el nombre del agente. NUNCA uses el nombre de un agente de otra propiedad."
        "\n- Si no hay agente en el contexto de la propiedad, di que vas a conectarlo con un asesor sin inventar nombres."
        "\n\nCITAS Y CALENDARIO:"
        "\n- NUNCA inventes horarios disponibles. SIEMPRE usa el tool check_availability ANTES de sugerir horarios."
        "\n- Primero pregunta al cliente qué fecha prefiere, luego usa check_availability para ver los horarios reales."
        "\n- Solo después de verificar disponibilidad real, ofrece los horarios al cliente."
        "\n\nMEMORIA Y PERSONALIZACIÓN:"
        "\n- RECUERDA el nombre del cliente y úsalo para dirigirte a él/ella durante toda la conversación."
        "\n- Recuerda las propiedades discutidas, preferencias mencionadas y todo lo hablado anteriormente."
        "\n- Presta atención a cada dato que el cliente comparte (nombre, teléfono, preferencias) y úsalo."
    )

    messages = [
        {"role": "system", "content": system_prompt + property_context + appointment_context + media_instructions}
    ]
    for msg in history[:-1]:
        # Map admin messages to assistant role for OpenAI
        role = 'assistant' if msg.role == 'admin' else msg.role
        messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Always include tools (calendar + media)
    api_kwargs = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7,
        "tools": CALENDAR_TOOLS,
    }

    response = client.chat.completions.create(**api_kwargs)
    response_message = response.choices[0].message

    # Tool calling loop: handle tool calls from the model
    all_media = []
    max_tool_rounds = 5
    rounds = 0
    while response_message.tool_calls and rounds < max_tool_rounds:
        rounds += 1
        messages.append(response_message)

        for tool_call in response_message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            logger.info(f"Tool call: {func_name}({func_args})")
            result, media = execute_tool(func_name, func_args, session_id=conversation.session_id)
            # Deduplicate: only add media URLs not already in the list
            existing_urls = {m['url'] for m in all_media}
            for item in media:
                if item['url'] not in existing_urls:
                    all_media.append(item)
                    existing_urls.add(item['url'])
            logger.info(f"Tool result: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        response = client.chat.completions.create(**api_kwargs)
        response_message = response.choices[0].message

    reply = response_message.content

    extract_intent(conversation)

    return {'text': reply, 'media': all_media}
