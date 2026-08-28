"""
Prueba local del handler de Lambda, simulando lo que llegaría
desde API Gateway. Corré esto con:

    python test_local.py

Necesita el mismo .env que ya usás en agente.py (GOOGLE_API_KEY, TAVILY_API_KEY).
"""
import json
from handler import lambda_handler

print("🔥 Handler local listo. Escribí 'salir' para cortar.\n")

historial = []

while True:
    mensaje = input("Vos: ")
    if mensaje.lower() == "salir":
        print("Agente: ¡Nos vemos, crack! 🚀")
        break

    # Esto es exactamente el shape del event que manda API Gateway
    # (HTTP API, payload format 2.0) cuando definamos la ruta POST /chat.
    fake_event = {
        "body": json.dumps({
            "mensaje": mensaje,
            "historial": historial,
        })
    }

    resultado = lambda_handler(fake_event, context=None)
    payload = json.loads(resultado["body"])

    if resultado["statusCode"] != 200:
        print(f"Agente: {payload.get('error')}")
        print(f"[debug: {payload.get('debug')}]\n")
        continue

    print(f"Agente: {payload['respuesta']}\n")
    historial = payload["historial"]