# Agente de IA en AWS Lambda + API Gateway

Despliegue serverless de un agente de IA conversacional (personalidad definida, tools propias) originalmente construido como script de consola, migrado a una arquitectura 100% serverless en AWS.

**Endpoint público (HTTP API abierta):**
```
POST https://<api-id>.execute-api.us-east-2.amazonaws.com/default/agente-ia
Body: { "mensaje": "texto del usuario", "historial": [...] }  // historial opcional
```

## Arquitectura

```
Cliente (curl / frontend)
   │
   ▼
API Gateway (HTTP API, pública)
   │
   ▼
AWS Lambda (imagen de contenedor, arm64)
   │
   ├──► Google Gemini API (gemini-3.6-flash)
   ├──► Tavily API (búsqueda web)
   └──► Open-Meteo API (clima)
```

- **Cómputo:** AWS Lambda, desplegada como imagen de contenedor (no ZIP), arquitectura `arm64` (Graviton — más barato que x86_64 en Lambda).
- **Registro de imágenes:** Amazon ECR, repositorio privado.
- **Exposición HTTP:** API Gateway HTTP API (no REST API — más simple y más barata para este caso de uso).
- **IAM:** rol de ejecución dedicado (`agente-ia-lambda-role`) con permisos mínimos — solo escritura de logs en CloudWatch. El usuario administrador de la cuenta (`juandi-admin`) nunca se usa como identidad de ejecución de la función.
- **Secretos:** `GOOGLE_API_KEY` y `TAVILY_API_KEY` como variables de entorno de Lambda (cifradas en reposo por AWS por defecto). Ver sección de trade-offs.

## De script a función serverless: el cambio de diseño clave

El agente original (`agente.py`) corría como un loop de consola con un objeto `chat` de la SDK de Gemini creado una única vez, que mantenía el historial de conversación en memoria mientras el proceso vivía.

Lambda no garantiza que una instancia persista entre invocaciones — cada request puede caer en un entorno de ejecución nuevo. Por eso el agente se refactorizó a un **handler stateless** (`handler.py`):

- El historial de conversación viaja en el body del request/response (`historial`), no en memoria del proceso.
- El cliente de Gemini y la configuración de tools se instancian **fuera** del handler, a nivel de módulo — así se reutilizan en invocaciones "calientes" (warm start) sin pagar el costo de inicialización en cada mensaje.
- Las tools (`obtener_clima`, `buscar_web`) no cambiaron: siguen siendo funciones Python pasadas directamente a la configuración de la SDK, que maneja el function calling automático.

## Empaquetado: por qué imagen de contenedor y no ZIP

Las dependencias (`google-genai`, `tavily-python` y sus transitivas) superan cómodamente el límite de 250MB sin comprimir de un ZIP/Layer de Lambda. Empaquetar como imagen de contenedor (`Dockerfile` basado en `public.ecr.aws/lambda/python:3.13`, la imagen base oficial de AWS con el Runtime Interface Client incluido) evita ese límite y es el patrón recomendado para funciones con dependencias pesadas.

## Trade-offs documentados

| Decisión | Alternativa "ideal" | Por qué se eligió así |
|---|---|---|
| API Gateway sin autenticación (Open) | API key / IAM auth / Cognito | Simplicidad para la primera versión funcional. Mejora obvia siguiente: agregar un API key con usage plan para evitar abuso y controlar costos. |
| Secrets en variables de entorno de Lambda | AWS Secrets Manager | Secrets Manager tiene costo mensual por secreto; SSM Parameter Store (gratis) o las variables de entorno cifradas son suficientes para un proyecto de portfolio con presupuesto en $0. |
| Historial de conversación viaja en el request/response | Persistencia en DynamoDB | Mantiene el proyecto acotado a "serverless + contenedor". La persistencia real de conversaciones es el objetivo del Proyecto 4 (dashboard con DynamoDB). |
| HTTP API (no REST API) | REST API con más features | HTTP API cubre el 100% de lo que necesita este caso (proxy simple a Lambda) a menor costo y complejidad. |

## Troubleshooting real (para la posteridad / entrevistas)

1. **Serialización del historial:** el primer intento de reconstruir el historial pasaba las partes como strings planos (`"texto"`); la SDK de `google-genai` espera objetos (`{"text": "texto"}`). Error: `1 validation error for Content... Input should be a valid dictionary`.
2. **Modelo deprecado:** `gemini-2.5-flash` dejó de estar disponible para cuentas nuevas durante el desarrollo; el propio error 404 de la API indicó el modelo de reemplazo (`gemini-3.6-flash`).
3. **Manifest de imagen incompatible con Lambda:** Docker Desktop reciente arma imágenes en formato OCI (con attestations de provenance/SBOM) que Lambda no soporta (`The image manifest, config or layer media type... is not supported`). Solución: build con `docker buildx build --provenance=false --sbom=false --output type=image,oci-mediatypes=false,push=true`, forzando el formato de manifest Docker v2 clásico.
4. **Arquitectura de Python en Apple Silicon:** el entorno virtual original apuntaba a un intérprete x86_64 corriendo bajo Rosetta (en vez de nativo arm64), lo que rompía la instalación de paquetes con extensiones nativas (`cryptography`, que requiere compilar con Rust). Solución: Homebrew nativo (`/opt/homebrew`) + Python instalado con `brew install python@3.13`.

## Costo

Diseñado para mantenerse dentro de la capa gratuita de AWS:
- Lambda: 1M invocaciones/mes gratis (permanente, no solo primer año).
- API Gateway HTTP API: 1M llamadas/mes gratis durante los primeros 12 meses.
- ECR: 500MB de almacenamiento gratis/mes durante los primeros 12 meses.

El costo variable real de este proyecto está fuera de AWS: las llamadas a la API de Gemini y de Tavily.

## Cómo correr localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Crear .env con GOOGLE_API_KEY y TAVILY_API_KEY
python3 test_local.py
```

## Cómo probar el contenedor local (simulando Lambda)

```bash
docker build --provenance=false --sbom=false -t agente-ia .
docker run -p 9000:8080 --env-file .env agente-ia

# En otra terminal:
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"body": "{\"mensaje\": \"hola\"}"}'
```

## Mejoras futuras

- API key / usage plan en API Gateway para controlar acceso y costos.
- Migrar secretos a SSM Parameter Store.
- Medir y documentar cold start vs warm start.
- Persistir historial de conversación en DynamoDB (en vez de viajar en cada request).
