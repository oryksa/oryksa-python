<p align="center"><img src="https://app.oryksa.com/static/oryksa_logo.png" width="300" alt="ORYKSA"></p>

# oryksa

[![English](https://img.shields.io/badge/English-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.md) [![Português](https://img.shields.io/badge/Portugu%C3%AAs-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.pt.md) [![Español](https://img.shields.io/badge/Espa%C3%B1ol-0891b2?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.es.md) [![Français](https://img.shields.io/badge/Fran%C3%A7ais-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.fr.md)

SDK oficial de Python de **ORYKSA AI Employees**: pon un empleado de IA que ya conoce el negocio dentro de tu backend Python, tus scripts y workers o tu app de escritorio. El mismo cerebro de WhatsApp y del chat del sitio web.

- Documentación: https://developer.oryksa.com
- API: `https://api.oryksa.com/v1`
- Python 3.10 o más reciente, una sola dependencia (`httpx`), clientes síncronos y asíncronos, con tipos.

## Instalar

```bash
pip install oryksa
```

## Servidor (clave secreta)

```python
import os
from oryksa import Oryksa

oryksa = Oryksa(os.environ["ORYKSA_API_KEY"])  # developer.oryksa.com > Keys

r = oryksa.chat("Are you open on Saturday?")
print(r["reply"], r["conversation_id"])

# Teach the AI employee about your app (e.g. on every release)
oryksa.learn_app(
    "FitTrack",
    description="Fitness app to log workouts and follow training plans.",
    screens=[{"title": "Workouts", "content": "Tap + to log a workout."}],
    faq=[{"question": "How do I cancel Premium?", "answer": "Settings > Subscription > Cancel."}],
)
```

Cuando la respuesta tarda más de lo que espera la API, `r["status"]` es `"pending"` (HTTP 202): léela después con `oryksa.conversation(r["conversation_id"])`.

## En la app (token de sesión, nunca la clave secreta)

Tu servidor crea un token de sesión de corta duración con la clave secreta y le da a la app solo ese token. El token funciona dentro de UNA conversación.

```python
# your server (FastAPI)
@app.get("/oryksa-token")
def oryksa_token(user=Depends(current_user)):
    s = oryksa.create_session(conversation_id=f"user-{user.id}", customer_name=user.first_name)
    return {"token": s["client_token"]}
```

```python
# your app (desktop app, worker, script): only the session token
import httpx
from oryksa import OryksaClient

client = OryksaClient(get_token=lambda: httpx.get("https://your-server.example/oryksa-token").json()["token"])
r = client.send_and_wait("Is there a 5K plan?")
print(r["reply"])
```

`get_token` se llama cuando el cliente necesita un token y otra vez cuando caduca (`session_expired`). Para un usuario con sesión iniciada en tu app, pasa `customer_email` y/o `customer_phone` (con el prefijo del país) a `create_session`: la IA deja de pedir datos de contacto y sabe que el cliente ha iniciado sesión.

| | Clave secreta: `Oryksa` | Token de sesión: `OryksaClient` |
|---|---|---|
| Dónde | solo en tu servidor | apps, escritorio, workers, o tu servidor en nombre de un usuario |
| Chat | `chat()` en cualquier conversación | `send()`, `send_and_wait()`, `messages()` en su propia conversación |
| Tareas de IA | crea primero una sesión | `ai()` |
| El empleado de IA | `agent.update()`, `agent.appearance()` | `agent()` (nombre, foto, saludo) |
| Cuenta, conocimiento, chat web, webhooks, sesiones | sí | no |

## Tus funciones de IA: `ai`

Haz que la IA haga lo que tu app o web necesita (leer una foto, extraer datos, clasificar, traducir, escribir) y paga con interacciones ORYKSA: 1 por respuesta. Tu prompt y tu JSON Schema viven en tu código; basta el token de sesión (nunca lleves la clave secreta). No crea una conversación en tu bandeja.

```python
import base64
from oryksa import OryksaClient

client = OryksaClient(token=session_token)
with open("tyre.jpg", "rb") as f:  # resized to 1600 px
    photo = base64.b64encode(f.read()).decode()

r = client.ai(
    instructions="Read the tyre on the photo: brand, model and size exactly as written on the sidewall. "
    "If the size is not legible, readable=false and size=null. Never invent.",
    images=[{"base64": photo, "mime": "image/jpeg"}],
    schema={
        "type": "object",
        "properties": {"readable": {"type": "boolean"}, "brand": {"type": ["string", "null"]}, "size": {"type": ["string", "null"]}},
        "required": ["readable", "brand", "size"],
    },
)
if r.json and r.json["readable"]:
    show_products(r.json["size"])
```

`r.text` trae la respuesta en texto, `r.json` el objeto (con schema), `r.interactions_spent` las interacciones usadas y `r.interactions_remaining` lo que queda en el plan. Hasta 4 fotos, unos 1,5 MB cada una. Cuando se agotan las interacciones del plan, la llamada lanza `OryksaError` con status 402.

En tu servidor, crea primero una sesión: la clave secreta nunca llama a `ai()`.

```python
s = oryksa.create_session(ttl_minutes=5)
r = OryksaClient(token=s["client_token"]).ai(instructions="Translate to Portuguese.", input="Good morning")
print(r.text)
```

## Adjuntar una foto o un documento

La IA ve una foto (hasta 2 MB) y lee un documento (PDF, Word, texto, CSV, hasta 8 MB). `document_attachment` aplica estos límites y envía una imagen pequeña como foto:

```python
from oryksa import document_attachment, document_from_path

att = document_attachment(document_from_path("quote.pdf"))
if "error" in att:
    print("Too large" if att["error"] == "big" else "Could not read the file")
else:
    r = client.send_and_wait("Can you check this quote?", **att)
```

O directamente: `client.send(texto, image={"base64": ..., "mime": "image/jpeg"})` o `file={"base64": ..., "name": "quote.pdf", "mime": "application/pdf"}`. También se exportan: `photo_attachment`, `mime_of`, `base64_bytes`, `scaled_size` (el tamaño al que reducir una foto, 1600 px), `MAX_PHOTO_BYTES` y `MAX_FILE_BYTES`.

## Enlaces en las respuestas

`links_in(text)` da los enlaces web de una respuesta (3 como máximo, sin la puntuación final), `without_links(text)` el texto sin ellos y `link_parts(text)` el texto en partes con un `url` en cada enlace (web, y e-mail como `mailto:`). `client.link_preview(url)` da el título y la foto de un enlace, para una tarjeta con un botón **Abrir**: solo las páginas del propio sitio del negocio (los dominios de su chat web) los tienen, y devuelve `None` cuando la página no se puede leer.

## Asíncrono

Cada cliente tiene un gemelo asíncrono con los mismos métodos: `AsyncOryksa` y `AsyncOryksaClient` (su `get_token` puede ser síncrono o asíncrono).

```python
import asyncio
import os
from oryksa import AsyncOryksa, AsyncOryksaClient


async def main():
    async with AsyncOryksa(os.environ["ORYKSA_API_KEY"]) as oryksa:
        s = await oryksa.create_session(customer_name="Ana")

    async with AsyncOryksaClient(token=s["client_token"]) as client:
        r = await client.ai(instructions="Summarise in one sentence.", input="The staff were friendly and the room was clean.")
        print(r.text)

asyncio.run(main())
```

## Webhooks

```python
import os
from flask import Flask, request
from oryksa import verify_webhook

app = Flask(__name__)

@app.post("/oryksa-webhook")
def oryksa_webhook():
    event = verify_webhook(request.get_data(), request.headers.get("ORYKSA-Signature"), os.environ["ORYKSA_WEBHOOK_SECRET"])
    if event["type"] == "booking.created":
        ...  # save it
    return "", 200
```

Pasa el cuerpo en bruto (los bytes tal como llegan, antes de leer el JSON). Crea el webhook con `oryksa.webhooks.create(url, events=[...])`: la respuesta trae el `secret`.

## Métodos del servidor

Los mismos nombres del SDK de JavaScript (`@oryksa/sdk`), en snake_case. Las respuestas son el JSON de la API, como `dict`.

| Método | API |
|---|---|
| `account()` | `GET /v1/account` |
| `chat(message, conversation_id=, customer_name=)` | `POST /v1/chat` |
| `conversations(limit=)`, `conversation(id)` | `GET /v1/conversations` |
| `create_session(conversation_id=, customer_name=, customer_email=, customer_phone=, ttl_minutes=60)` | `POST /v1/sessions` |
| `learn_app(name, description=, url=, agent_name=, languages=, services=, screens=, faq=, settings=)` | `PATCH /v1/agent`, `PUT /v1/knowledge/pages`, `POST /v1/knowledge/faq` |
| `agent.update(...)`, `agent.appearance(...)` | `PATCH /v1/agent`, `PATCH /v1/agent/appearance` |
| `knowledge.get()`, `knowledge.set_pages(pages)`, `knowledge.crawl(url)`, `knowledge.add_faq(items)` | `/v1/knowledge` |
| `widget.snippet(framework=, lang=, position=)`, `widget.set_domains(domains)` | `/v1/widget` |
| `webhooks.list()`, `webhooks.create(url, events=)`, `webhooks.delete(id)`, `webhooks.test(id)` | `/v1/webhooks` |

Opciones de todos los clientes: `base_url` (por defecto `https://api.oryksa.com/v1`), `timeout` en segundos (por defecto 60) y `http_client` (tu propio `httpx.Client` o `httpx.AsyncClient`, para proxies). Úsalos con `with` / `async with`, o llama a `close()` / `aclose()`.

## Errores

Cada llamada que falla lanza `OryksaError` con `status`, `code` (por ejemplo `interaction_limit_reached`, `rate_limited`, `plan_required`, `session_expired`) y `message`; los otros campos del error de la API, como `upgrade_url` y `retry_after`, también son atributos. Cuando no se puede llegar a ORYKSA: `status` 0 y `code` `network_error`. Los argumentos incorrectos (sin clave, la clave secreta en `OryksaClient`, `ai()` sin instrucciones, texto o imagen) lanzan `ValueError` antes de enviar nada.

## Sobre el autor

**Weslley Harakawa** - Fundador de ORYKSA AI. En Lisboa, Portugal. Especialidades: inteligencia artificial, desarrollo web y móvil, tokenización en blockchain. Formación: University of the People.

- LinkedIn: https://www.linkedin.com/in/weslleyharakawa/
- ORYKSA AI Employees: https://oryksa.com (X: https://x.com/oryksa, Instagram: https://www.instagram.com/oryksaai, YouTube: https://www.youtube.com/@ORYKSA)

---

MIT License · ORYKSA AI Employees · W8 Atlantic Unipessoal Lda
