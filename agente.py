import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from personalidad import SYSTEM_PROMPT
from tools import obtener_clima, buscar_web

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[obtener_clima, buscar_web],
)

chat = client.chats.create(model="gemini-flash-lite-latest", config=config)

print("🔥 Agente listo. Escribí 'salir' para cortar.\n")

while True:
    mensaje = input("Vos: ")
    if mensaje.lower() == "salir":
        print("Agente: ¡Nos vemos, crack! 🚀")
        break

    try:
        respuesta = chat.send_message(mensaje)
        print(f"Agente: {respuesta.text}\n")
    except Exception as e:
        print("Agente: Uy, se me trabó la cabeza un segundo. Probá de nuevo en unos segundos. 🔧\n")
        print(f"[debug: {e}]\n")
