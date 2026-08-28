import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from personalidad import SYSTEM_PROMPT
from tools import obtener_clima, buscar_web

load_dotenv()

# Todo esto se crea UNA sola vez cuando la Lambda arranca en frío,
# y se reutiliza en las invocaciones siguientes mientras la instancia
# siga "tibia". Por eso va afuera del handler, no adentro.
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[obtener_clima, buscar_web],
)

MODEL = "gemini-3.6-flash"


def lambda_handler(event, context):
    """
    Espera un POST con body JSON:
      { "mensaje": "hola crack", "historial": [...] }  # historial es opcional

    Devuelve:
      { "respuesta": "...", "historial": [...] }  # el cliente debe guardar
      este historial y devolverlo en el siguiente request para mantener
      el contexto de la conversación.
    """
    try:
        body = _parsear_body(event)
        mensaje = (body.get("mensaje") or "").strip()
        historial_previo = body.get("historial") or []

        if not mensaje:
            return _response(400, {"error": "Falta el campo 'mensaje'."})

        chat = client.chats.create(
            model=MODEL,
            config=config,
            history=historial_previo,
        )
        respuesta = chat.send_message(mensaje)

        nuevo_historial = _serializar_historial(chat.get_history())

        return _response(200, {
            "respuesta": respuesta.text,
            "historial": nuevo_historial,
        })

    except Exception as e:
        # Mismo espíritu que el try/except de agente.py original,
        # pero devolviendo un JSON en vez de un print.
        return _response(500, {
            "error": "Uy, se me trabó la cabeza un segundo. Probá de nuevo en unos segundos.",
            "debug": str(e),
        })


def _parsear_body(event):
    """API Gateway (HTTP API) manda el body como string JSON."""
    raw = event.get("body")
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def _serializar_historial(contenidos):
    """
    Convierte los Content del SDK a algo JSON-serializable simple.
    Nota: esto guarda solo las partes de texto. Si en algún momento
    agregás tools que devuelven cosas más complejas dentro del historial,
    esto hay que revisarlo — por ahora cubre el caso de texto plano,
    que es el que usa este agente.
    """
    historial = []
    for contenido in contenidos:
        partes_texto = [{"text": p.text} for p in contenido.parts if getattr(p, "text", None)]
        if partes_texto:
            historial.append({"role": contenido.role, "parts": partes_texto})
    return historial


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, ensure_ascii=False),
    }