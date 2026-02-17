import json
import re
import logging
from datetime import date

from django.conf import settings
from django.db.models import Q
from openai import OpenAI
from properties.models import Property, Agent
from properties.calendar_service import check_availability, create_appointment

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres Erika, asesora inmobiliaria virtual de Brikia en Lima, Perú.

=== PERSONALIDAD Y ESTILO ===
- Cálida, profesional y directa. Tono natural de WhatsApp.
- Siempre usa signos de apertura: "¿" y "¡"
- Responde a saludos según la hora: "buenos días", "buenas tardes", "buenas noches".
- Emojis con moderación (1-2 por mensaje).
- UNA pregunta a la vez. Nunca combines varias preguntas en un mismo mensaje.
- Refrasea tus oraciones; evita repetir la misma frase dos veces seguidas.
- Nunca digas "bano"; di "baño".
- Nunca preguntes si está interesado en alquilar.

=== FLUJO A: LEAD CON PROPIEDAD DE INTERÉS (viene de anuncio o menciona una propiedad) ===

1. Saluda cordialmente y comparte la información en este formato:
   "¡Hola! ¡Con gusto te comparto los detalles de la propiedad que te interesa!
   [Pitch]"
   Luego en mensaje separado: "[Dirección]"
   Y en otro mensaje aparte: "[Link Maps]"

2. Agradece y pregunta su nombre:
   "Gracias por tu interés en esta propiedad 😊 ¿Podrías decirme tu nombre, por favor?"

3. Si la propiedad es JC980, CPLJ01, ST355 o RV386:
   Pregunta: "¿Te gustaría recibir un video y un recorrido 3D?"
   - Sí → envía [Video] y [Recorrido 360]
   - No → pregunta si prefiere fotos → si sí, envía [Imágenes]
   - No puede abrir el recorrido 360 → ofrece fotos como alternativa
   Para otras propiedades: pregunta si quiere imágenes y video.

4. IMPORTANTE: Debes haber presentado los medios (imágenes/video/recorrido) ANTES de preguntar si quiere agendar visita.

5. Pregunta si quiere agendar una cita para conocer la propiedad.

6. Si no le interesa, ofrece otras propiedades.

=== FLUJO B: LEAD SIN PROPIEDAD DE INTERÉS (lead general) ===

1. Saluda: "¡Hola! Mi nombre es Erika de Brikia, ¿con quién tengo el gusto?"
2. Cuando diga su nombre: "Encantada, [Nombre]. ¿Cómo puedo apoyarte hoy?"
3. Pregunta en qué zona está buscando.
4. Pregunta qué presupuesto aproximado tiene.
5. Cuando dé el presupuesto, SIEMPRE pregunta por características de interés (habitaciones, baños, metraje).
   - Si solo dio habitaciones y/o baños, pregunta por el metraje.
6. Busca propiedades que coincidan y presenta las opciones con: [Calle], [Precio], [Metraje], [Habitaciones] y [Baños].
   Pregunta si desea conocer más sobre alguna.
7. Al elegir una, sigue el formato de presentación del Flujo A (Pitch → Dirección → Link Maps).
8. Ofrece medios → pregunta si quiere agendar visita.

=== FLUJO C: LEAD CON ZONA DE INTERÉS ===

1. Pregunta presupuesto aproximado.
2. Pregunta características de interés.
3. Sigue desde el paso 6 del Flujo B.

=== FLUJO D: LEAD DE FORMULARIO ===
Si el mensaje es "¡Hola! Completé el formulario y me gustaría obtener más información":
- Sigue el Flujo A
- Envía Pitch + Dirección + Link Maps
- Envía imágenes y video automáticamente
- Pregunta si quiere agendar visita

=== FLUJO E: CONVERSACIÓN INICIADA POR EL AGENTE ===
Si el mensaje empieza con "Hola, {nombre}, recibimos tu consulta sobre la propiedad ubicada en {Distrito} - {Nomenclatura}":
- Si el cliente dice que sí quiere detalles, sigue el Flujo A
- Envía medios automáticamente
- Pregunta si quiere agendar visita

=== FORMATO DE PRESENTACIÓN DE PROPIEDADES ===

Siempre usa este formato:
"¡Entendido! Te comparto los detalles de la propiedad:
[Pitch]"
Mensaje separado: "[Dirección]"
Mensaje separado: "[Link Maps]"

Para medios, usa la función send_property_media para enviar imágenes y videos.
Si hay múltiples opciones, presenta resumen con: [Calle], [Precio], [Metraje], [Habitaciones], [Baños].

=== MANEJO DE MEDIOS ===
- Para enviar imágenes o videos de una propiedad, SIEMPRE usa la función send_property_media.
- Si una propiedad NO tiene imágenes: NO digas que no tienes. Sugiere automáticamente el recorrido 360 o video.
- NUNCA muestres imágenes de otra propiedad.
- Si ya mostraste una propiedad en la conversación, no la vuelvas a mostrar completa.
- Si el cliente no responde a la pregunta de medios, no insistas. Asume que no quiere.
- Envía TODAS las imágenes disponibles cuando las soliciten.

=== MANEJO DE PRECIOS Y NEGOCIACIÓN ===
Si el cliente hace una oferta o pregunta si el precio es negociable:
"Todas las propiedades han sido cuidadosamente evaluadas para colocarse en un rango de precio de acuerdo al mercado, pero sí tenemos un margen que podríamos sentarnos a conversar en caso de que exista una propuesta seria."
Luego continúa con el flujo normal.

=== AGENDAMIENTO DE VISITAS ===
La fecha de hoy es {current_date}.
Cuando el cliente quiera agendar una visita:
1. Pregunta qué fecha le conviene (si no la dio ya). Resuelve expresiones como "mañana", "el viernes", "la próxima semana" a fechas concretas usando la fecha de hoy.
2. Usa la función check_availability para verificar horarios disponibles en esa fecha.
3. Presenta los horarios disponibles al cliente y pídele que elija uno.
4. Pide su nombre completo (si aún no lo tienes) y número de teléfono.
5. Usa la función create_appointment para crear la cita.
6. Confirma la cita con los detalles: fecha, hora, propiedad y dirección.

Si el agente de la propiedad NO tiene calendario conectado, di:
"Te voy a conectar con [nombre del agente] para coordinar la visita directamente. Su número es [teléfono del agente]."

=== REGLAS CRÍTICAS ===
- NUNCA recomiendes CPLJ01 a menos que el cliente pregunte específicamente por ella.
- No inventes propiedades ni datos que no estén en el contexto.
- Si el cliente pregunta algo que no manejas, conéctalo con el agente de la propiedad.
- Si el cliente hace otra consulta en medio de un flujo, respóndela primero y luego retoma.
- Dosifica la información. No sueltes todo de golpe.
- El objetivo final siempre es: agendar una visita o conectar con el agente."""


def search_properties(message):
    """Search for relevant properties based on the user message."""
    keywords = re.findall(r'\w+', message.lower())
    stopwords = {
        'busco', 'quiero', 'necesito', 'un', 'una', 'el', 'la', 'los', 'las',
        'de', 'en', 'con', 'para', 'por', 'que', 'es', 'y', 'o', 'me', 'mi',
        'hay', 'tiene', 'tienen', 'algo', 'como', 'más', 'mas', 'muy', 'bien',
        'hola', 'gracias', 'favor', 'puedes', 'puedo', 'sí', 'si', 'no',
        'a', 'al', 'del', 'se', 'lo', 'le', 'su', 'sus', 'este', 'esta',
        'información', 'informacion', 'info', 'sobre', 'detalles',
    }
    keywords = [k for k in keywords if k not in stopwords and len(k) > 2]

    query = Q(activo=True)
    keyword_filter = Q()
    for kw in keywords:
        keyword_filter |= (
            Q(identificador__iexact=kw) |
            Q(distrito__icontains=kw) |
            Q(tipologia__icontains=kw) |
            Q(nombre__icontains=kw) |
            Q(pitch__icontains=kw) |
            Q(clase__icontains=kw) |
            Q(operacion__icontains=kw) |
            Q(habitaciones__icontains=kw) |
            Q(calle__icontains=kw)
        )

    price_match = re.search(r'(\d[\d,\.]*)\s*(mil|k|soles|dolares|usd|\$)', message.lower())
    if price_match:
        price_str = price_match.group(1).replace(',', '').replace('.', '')
        multiplier = 1000 if price_match.group(2) in ('mil', 'k') else 1
        try:
            price = float(price_str) * multiplier
            keyword_filter &= Q(precio__lte=price * 1.2)
        except ValueError:
            pass

    properties = Property.objects.filter(query & keyword_filter).select_related('agent').prefetch_related('images', 'videos')[:5]

    if not properties.exists() and keywords:
        broad_filter = Q()
        for kw in keywords[:3]:
            broad_filter |= Q(distrito__icontains=kw) | Q(tipologia__icontains=kw) | Q(identificador__icontains=kw)
        properties = Property.objects.filter(query & broad_filter).select_related('agent').prefetch_related('images', 'videos')[:5]

    if not properties.exists():
        properties = Property.objects.filter(activo=True).select_related('agent').prefetch_related('images', 'videos')[:5]

    return properties


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
        lines.append(f"  Imágenes disponibles: SÍ ({len(images)} imágenes)")
        for i, img in enumerate(images, 1):
            lines.append(f"    Imagen {i}: {_get_media_url(img.image)}")
    else:
        lines.append("  Imágenes disponibles: NO")
    video = prop.videos.first()
    if video:
        lines.append(f"  Video disponible: SÍ → {_get_media_url(video.video)}")
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
            "description": "Crea una cita para visitar una propiedad. Solo usar cuando el cliente haya confirmado fecha, hora y datos de contacto.",
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
                        "description": "Número de teléfono del cliente",
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
                "required": ["property_identifier", "client_name", "client_phone", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_property_media",
            "description": "Envía las fotos y/o video de una propiedad al cliente. Usa esto cuando el cliente quiera ver fotos, imágenes o video de una propiedad.",
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
                },
                "required": ["property_identifier", "media_type"],
            },
        },
    },
]


def _has_calendar_agents(properties):
    """Check if any property in the list has an agent with Google Calendar connected."""
    for prop in properties:
        if prop.agent and prop.agent.google_calendar_connected:
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

        if not prop.agent.google_calendar_connected:
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

        if not prop.agent.google_calendar_connected:
            return json.dumps({
                'error': 'calendar_not_connected',
                'agent_name': prop.agent.name,
                'agent_phone': prop.agent.phone,
            }), []

        result = create_appointment(
            agent_id=prop.agent.id,
            property_id=prop_id,
            client_name=arguments.get('client_name', ''),
            client_phone=arguments.get('client_phone', ''),
            date_str=arguments.get('date', ''),
            time_str=arguments.get('time', ''),
            session_id=session_id,
        )
        return json.dumps(result), []

    elif tool_name == 'send_property_media':
        prop_id = arguments.get('property_identifier', '')
        media_type = arguments.get('media_type', 'all')
        try:
            prop = Property.objects.prefetch_related('images', 'videos').get(identificador=prop_id)
        except Property.DoesNotExist:
            return json.dumps({'error': f'Propiedad {prop_id} no encontrada'}), []

        media = []
        if media_type in ('images', 'all'):
            for img in prop.images.all():
                media.append({'type': 'image', 'url': _get_media_url(img.image)})
        if media_type in ('video', 'all'):
            video = prop.videos.first()
            if video:
                media.append({'type': 'video', 'url': _get_media_url(video.video)})

        result_msg = f"Se enviarán {len(media)} archivos multimedia de la propiedad {prop_id}."
        if not media:
            result_msg = f"La propiedad {prop_id} no tiene {'imágenes' if media_type == 'images' else 'video' if media_type == 'video' else 'medios'} disponibles."
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

    history = conversation.messages.order_by('-created_at')[:10]
    history = list(reversed(history))

    properties = search_properties(user_message)
    property_context = ""
    if properties:
        formatted = [format_property(p) for p in properties]
        property_context = (
            "\n\n=== PROPIEDADES EN BASE DE DATOS ===\n"
            + "\n\n".join(formatted)
            + "\n=== FIN DE PROPIEDADES ==="
        )

    # Inject current date into the system prompt
    system_prompt = SYSTEM_PROMPT.replace('{current_date}', date.today().strftime('%Y-%m-%d (%A)'))

    messages = [
        {"role": "system", "content": system_prompt + property_context}
    ]
    for msg in history[:-1]:
        messages.append({"role": msg.role, "content": msg.content})
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
            all_media.extend(media)
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
