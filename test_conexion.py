import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Decime hola en una frase graciosa"
)

print(response.text)