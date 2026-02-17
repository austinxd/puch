import json
import re
import logging
from django.conf import settings
from django.db.models import Q
from openai import OpenAI
from properties.models import Property

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres Bri, asesora inmobiliaria virtual de Brikia en Lima, Perú. Hablas como una persona real, cercana y profesional.

PERSONALIDAD:
- Eres cálida, empática y conversacional. Usas un tono natural, como si hablaras por WhatsApp con un amigo.
- Respuestas CORTAS y directas. Máximo 2-3 oraciones por mensaje. No hagas listas largas.
- Usa emojis con moderación (1-2 por mensaje máximo).
- Tutea al cliente.

ESTRATEGIA DE CONVERSACIÓN:
- NO sueltes toda la información de golpe. Ve dosificando según lo que pregunte.
- Siempre haz una PREGUNTA al final para mantener la conversación. Ejemplos: "¿Te gustaría saber más?", "¿Qué es lo más importante para ti?", "¿Has visitado la zona?"
- Si el cliente muestra interés real, guíalo hacia agendar una visita o hablar con el agente.
- Si pregunta por precio, responde y pregunta si está dentro de su presupuesto.
- Si pregunta algo que no sabes (como si es negociable), no inventes. Di algo como "Eso lo maneja directamente nuestro asesor, te puedo conectar con él si quieres 😊"

FLUJO IDEAL:
1. Entender qué busca → preguntar zona, presupuesto, tipo de propiedad
2. Recomendar 1-2 opciones que encajen (no más)
3. Compartir info progresivamente según preguntas
4. Cerrar con: agendar visita o conectar con el agente

INFORMACIÓN DEL AGENTE:
- Cuando el cliente esté listo o pida hablar con alguien, comparte el contacto del agente de la propiedad.
- Frase ejemplo: "Te paso el contacto de [nombre], que es quien lleva esta propiedad. Le puedes escribir directo al [teléfono] 📱"

REGLAS:
- No inventes propiedades ni datos que no estén en el contexto.
- Si no hay propiedades que coincidan, pregunta más detalles o sugiere alternativas.
- Nunca respondas como un robot o un catálogo. Eres una persona."""


def search_properties(message):
    """Search for relevant properties based on the user message."""
    keywords = re.findall(r'\w+', message.lower())
    stopwords = {
        'busco', 'quiero', 'necesito', 'un', 'una', 'el', 'la', 'los', 'las',
        'de', 'en', 'con', 'para', 'por', 'que', 'es', 'y', 'o', 'me', 'mi',
        'hay', 'tiene', 'tienen', 'algo', 'como', 'más', 'mas', 'muy', 'bien',
        'hola', 'gracias', 'favor', 'puedes', 'puedo', 'sí', 'si', 'no',
        'a', 'al', 'del', 'se', 'lo', 'le', 'su', 'sus', 'este', 'esta',
    }
    keywords = [k for k in keywords if k not in stopwords and len(k) > 2]

    query = Q(activo=True)
    keyword_filter = Q()
    for kw in keywords:
        keyword_filter |= (
            Q(distrito__icontains=kw) |
            Q(tipologia__icontains=kw) |
            Q(nombre__icontains=kw) |
            Q(pitch__icontains=kw) |
            Q(clase__icontains=kw) |
            Q(operacion__icontains=kw) |
            Q(habitaciones__icontains=kw)
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

    properties = Property.objects.filter(query & keyword_filter).select_related('agent')[:5]

    if not properties.exists() and keywords:
        broad_filter = Q()
        for kw in keywords[:3]:
            broad_filter |= Q(distrito__icontains=kw) | Q(tipologia__icontains=kw)
        properties = Property.objects.filter(query & broad_filter).select_related('agent')[:5]

    if not properties.exists():
        properties = Property.objects.filter(activo=True).select_related('agent')[:5]

    return properties


def format_property(prop):
    """Format a property for the AI context."""
    lines = [
        f"- **{prop.nombre}** ({prop.identificador})",
        f"  Tipo: {prop.clase} | Operación: {prop.operacion}",
        f"  Distrito: {prop.distrito}",
        f"  Precio: ${prop.precio}" if prop.precio else "  Precio: Consultar",
        f"  Metraje: {prop.metraje}" if prop.metraje else "",
        f"  Habitaciones: {prop.habitaciones}" if prop.habitaciones else "",
        f"  Baños: {prop.banos}" if prop.banos else "",
        f"  Cocheras: {prop.cocheras}" if prop.cocheras else "",
        f"  Piso: {prop.piso}" if prop.piso else "",
        f"  Vista: {prop.vista}" if prop.vista else "",
        f"  Distribución: {prop.distribucion}" if prop.distribucion else "",
        f"  Pitch: {prop.pitch}" if prop.pitch else "",
        f"  Agente: {prop.agent.name} ({prop.agent.phone})" if prop.agent else "",
    ]
    images = [url for url in [prop.imagen_1, prop.imagen_2, prop.imagen_3, prop.imagen_4, prop.imagen_5] if url]
    if images:
        lines.append(f"  Imágenes: {', '.join(images)}")
    if prop.video:
        lines.append(f"  Video: {prop.video}")
    return '\n'.join(line for line in lines if line)


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
        # Clean markdown code block if present
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
    """Generate a chat response using OpenAI."""
    if not settings.OPENAI_API_KEY:
        return "Lo siento, el servicio de chat no está configurado. Contacta al administrador."

    history = conversation.messages.order_by('-created_at')[:10]
    history = list(reversed(history))

    properties = search_properties(user_message)
    property_context = ""
    if properties:
        formatted = [format_property(p) for p in properties]
        property_context = (
            "\n\n--- PROPIEDADES DISPONIBLES ---\n"
            + "\n\n".join(formatted)
            + "\n--- FIN DE PROPIEDADES ---"
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + property_context}
    ]
    for msg in history[:-1]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000,
        temperature=0.7,
    )

    reply = response.choices[0].message.content

    # Extract intent after every user message
    extract_intent(conversation)

    return reply
