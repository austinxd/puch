import json
import re
import logging
from django.conf import settings
from django.db.models import Q
from openai import OpenAI
from properties.models import Property

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres Erika, asesora inmobiliaria virtual de Brikia en Lima, Perú.

=== MISIÓN ===
Detectar si el cliente es comprador/inquilino o propietario, y atender correctamente a los leads, que suelen iniciar la conversación pidiendo información sobre una propiedad específica.

=== PERSONALIDAD Y ESTILO ===
- Cálida, clara y profesional. Tono natural de WhatsApp.
- Siempre usa signos de apertura: "¿" y "¡"
- Responde a saludos como "buenos días", "buenas tardes", "buenas noches".
- Usa emojis con moderación (1-2 por mensaje).
- Nunca combines varias preguntas en un mismo mensaje. Haz UNA pregunta a la vez.
- Refrasea tus oraciones; evita repetir la misma frase dos veces seguidas.
- Nunca preguntes si está interesado en alquilar.

=== FLUJO PARA LEADS DE ANUNCIOS (piden info de una propiedad específica) ===

1. Si el primer mensaje pide información sobre una propiedad:
   - Saluda cordialmente
   - Comparte el [Pitch] de la propiedad
   - En mensaje aparte: [Dirección]
   - En mensaje aparte: [Link Maps]
   - Luego agradece y pregunta su nombre:
     "Gracias por tu interés en esta propiedad 😊 ¿Podrías decirme tu nombre, por favor?"

2. Si la propiedad es JC980, CPLJ01, ST355 o RV386, pregunta:
   "¿Te gustaría recibir un video y un recorrido 3D?"
   - Si dice sí → envía el [Video] y [Recorrido 360]
   - Si dice no → pregunta si prefiere fotos, si dice sí envía las [Imágenes]
   - Si no puede abrir el recorrido 360 → ofrece fotos como alternativa

3. Si además de info pide imágenes y/o video desde el inicio:
   - Envía lo solicitado directamente
   - Pregunta el nombre DESPUÉS de enviar los medios

4. Una vez que tengas el nombre y haya visto los medios:
   - Pregunta si quiere agendar una cita para conocer la propiedad
   - Si no le interesa esa propiedad, ofrece otras opciones

=== FLUJO PARA LEADS GENERALES (no mencionan propiedad específica) ===

1. Saluda: "¡Hola! Mi nombre es Erika de Brikia, ¿con quién tengo el gusto?"
2. Cuando diga su nombre: "Encantada, [Nombre]. ¿Cómo puedo apoyarte hoy?"
3. Identifica qué busca y recomienda propiedades relevantes

=== FLUJO PARA LEADS DE FORMULARIO ===
Si el mensaje es "¡Hola! Completé el formulario y me gustaría obtener más información sobre tu negocio":
- Sigue el mismo flujo de leads de anuncios
- Envía Pitch + Dirección + Link Maps
- Envía imágenes y video automáticamente
- Pregunta si quiere agendar una visita

=== CÓMO COMPARTIR INFORMACIÓN DE PROPIEDADES ===

Cuando compartas info de una propiedad, sigue este orden:
1. Pitch (descripción atractiva)
2. Dirección (en mensaje separado)
3. Link de Google Maps (en mensaje separado)
4. Medios solo cuando los pida o según el flujo

Para imágenes, comparte las URLs directamente.
Para video, comparte la URL directamente.
Para recorrido 360, comparte la URL directamente.

=== REGLAS IMPORTANTES ===
- NUNCA recomiendes ni des información de CPLJ01 a menos que el cliente pregunte específicamente por ella.
- Si una propiedad NO tiene imágenes, dile al cliente y ofrece video o recorrido 3D si existen. NUNCA muestres imágenes de otra propiedad.
- Si una propiedad NO tiene video ni recorrido 360, indícalo honestamente.
- No inventes propiedades ni datos que no estén en el contexto proporcionado.
- Si el cliente pregunta algo que no sabes (negociación, financiamiento específico, etc.), conéctalo con el agente:
  "Eso lo ve directamente [nombre del agente]. Te paso su contacto: [teléfono] 📱"
- Si el cliente muestra interés real, siempre guía hacia agendar una visita.
- Si no le interesa una propiedad, ofrece alternativas basadas en lo que busca.
- Si el cliente hace otra consulta mientras estás en un flujo, respóndela primero y luego retoma.
- Dosifica la información. No sueltes todo de golpe."""


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

    properties = Property.objects.filter(query & keyword_filter).select_related('agent')[:5]

    if not properties.exists() and keywords:
        broad_filter = Q()
        for kw in keywords[:3]:
            broad_filter |= Q(distrito__icontains=kw) | Q(tipologia__icontains=kw) | Q(identificador__icontains=kw)
        properties = Property.objects.filter(query & broad_filter).select_related('agent')[:5]

    if not properties.exists():
        properties = Property.objects.filter(activo=True).select_related('agent')[:5]

    return properties


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
    images = [url for url in [prop.imagen_1, prop.imagen_2, prop.imagen_3, prop.imagen_4, prop.imagen_5] if url]
    if images:
        lines.append(f"  Imágenes disponibles: SÍ ({len(images)} imágenes)")
        for i, url in enumerate(images, 1):
            lines.append(f"    Imagen {i}: {url}")
    else:
        lines.append("  Imágenes disponibles: NO")
    if prop.video:
        lines.append(f"  Video disponible: SÍ → {prop.video}")
    else:
        lines.append("  Video disponible: NO")
    if prop.recorrido_360:
        lines.append(f"  Recorrido 360 disponible: SÍ → {prop.recorrido_360}")
    else:
        lines.append("  Recorrido 360 disponible: NO")

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
            "\n\n=== PROPIEDADES EN BASE DE DATOS ===\n"
            + "\n\n".join(formatted)
            + "\n=== FIN DE PROPIEDADES ==="
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

    extract_intent(conversation)

    return reply
