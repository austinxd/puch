import re
from django.conf import settings
from django.db.models import Q
from openai import OpenAI
from properties.models import Property

SYSTEM_PROMPT = """Eres el asistente virtual de Brikia, una inmobiliaria en Lima, Perú.
Tu rol es ayudar a los clientes a encontrar propiedades que se ajusten a sus necesidades.
Responde en español, sé amable y profesional.
Cuando recomiendes propiedades, incluye: nombre, ubicación, precio, metraje y características principales.
Si el cliente pide más detalles, proporciona la información completa incluyendo links de imágenes si están disponibles.
Si no hay propiedades que coincidan, indícalo amablemente y sugiere alternativas o pide más detalles.
No inventes propiedades que no estén en el contexto proporcionado."""


def search_properties(message):
    """Search for relevant properties based on the user message."""
    keywords = re.findall(r'\w+', message.lower())
    # Remove common words
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

    # Detect price range
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
        # Fallback: broader search
        broad_filter = Q()
        for kw in keywords[:3]:
            broad_filter |= Q(distrito__icontains=kw) | Q(tipologia__icontains=kw)
        properties = Property.objects.filter(query & broad_filter).select_related('agent')[:5]

    if not properties.exists():
        # Return some recent active properties
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


def get_chat_response(conversation, user_message):
    """Generate a chat response using OpenAI."""
    if not settings.OPENAI_API_KEY:
        return "Lo siento, el servicio de chat no está configurado. Contacta al administrador."

    # Get conversation history (last 10 messages)
    history = conversation.messages.order_by('-created_at')[:10]
    history = list(reversed(history))

    # Search relevant properties
    properties = search_properties(user_message)
    property_context = ""
    if properties:
        formatted = [format_property(p) for p in properties]
        property_context = (
            "\n\n--- PROPIEDADES DISPONIBLES ---\n"
            + "\n\n".join(formatted)
            + "\n--- FIN DE PROPIEDADES ---"
        )

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + property_context}
    ]
    # Add history (skip the current user message, it's added at the end)
    for msg in history[:-1]:  # Skip last one (current user message already saved)
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000,
        temperature=0.7,
    )

    return response.choices[0].message.content
