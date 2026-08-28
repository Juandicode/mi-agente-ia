import requests

def obtener_clima(ciudad: str) -> str:
    """Obtiene el clima actual de una ciudad."""
    
    # Primero geocodificamos la ciudad para obtener lat/lon
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {"name": ciudad, "count": 1, "language": "es"}
    geo_resp = requests.get(geo_url, params=geo_params).json()
    
    if "results" not in geo_resp or len(geo_resp["results"]) == 0:
        return f"No encontré la ciudad '{ciudad}'."
    
    lugar = geo_resp["results"][0]
    lat, lon = lugar["latitude"], lugar["longitude"]
    nombre_real = lugar["name"]
    
    # Ahora pedimos el clima con esas coordenadas
    clima_url = "https://api.open-meteo.com/v1/forecast"
    clima_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m"
    }
    clima_resp = requests.get(clima_url, params=clima_params).json()
    
    temp = clima_resp["current"]["temperature_2m"]
    viento = clima_resp["current"]["wind_speed_10m"]
    
    return f"En {nombre_real}: {temp}°C, viento de {viento} km/h."

import os
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def buscar_web(consulta: str) -> str:
    """Busca información actualizada en internet sobre un tema."""
    resultado = tavily_client.search(query=consulta, max_results=3)
    
    resumen = []
    for r in resultado["results"]:
        resumen.append(f"- {r['title']}: {r['content'][:200]}...")
    
    return "\n".join(resumen)

