<p align="center"><img src="https://app.oryksa.com/static/oryksa_logo.png" width="300" alt="ORYKSA"></p>

# oryksa

[![English](https://img.shields.io/badge/English-0891b2?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.md) [![Português](https://img.shields.io/badge/Portugu%C3%AAs-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.pt.md) [![Español](https://img.shields.io/badge/Espa%C3%B1ol-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.es.md) [![Français](https://img.shields.io/badge/Fran%C3%A7ais-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.fr.md)

Official Python SDK for **ORYKSA AI Employees**: put an AI employee that already knows the business inside your Python backend, your scripts and workers, or your desktop app. Same brain as WhatsApp and the website chat.

- Docs: https://developer.oryksa.com
- API: `https://api.oryksa.com/v1`
- Python 3.9 or newer, one dependency (`httpx`), sync and async clients, fully typed.

## Install

```bash
pip install oryksa
```

## Server (secret key)

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

When the reply takes longer than the API waits, `r["status"]` is `"pending"` (HTTP 202): read it later with `oryksa.conversation(r["conversation_id"])`.

## In the app (session token, never the secret key)

Your server creates a short-lived session token with the secret key and gives only that token to the app. The token works inside ONE conversation.

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

`get_token` is called when the client needs a token and again when it expires (`session_expired`). For a user signed in to your app, pass `customer_email` and/or `customer_phone` (with the country code) to `create_session`: the AI then asks for no contact details and knows the customer is signed in.

| | Secret key: `Oryksa` | Session token: `OryksaClient` |
|---|---|---|
| Where | your server only | apps, desktop, workers, or your server acting for one user |
| Chat | `chat()` in any conversation | `send()`, `send_and_wait()`, `messages()` in its own conversation |
| AI tasks | create a session first | `ai()` |
| The AI employee | `agent.update()`, `agent.appearance()` | `agent()` (name, photo, greeting) |
| Account, knowledge, website chat, webhooks, sessions | yes | no |

## Your own AI features: `ai`

Have the AI do what your app or site needs (read a photo, extract data, classify, translate, write) and pay with ORYKSA interactions: 1 per answer. Your prompt and your JSON Schema live in your code; the session token is enough (never ship the secret key). It does not create a conversation in your inbox.

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

`r.text` has the answer as text, `r.json` the object (with a schema), `r.interactions_spent` the interactions used and `r.interactions_remaining` what is left in the plan. Up to 4 photos, about 1.5 MB each. When the plan's interactions are used up the call raises `OryksaError` with status 402.

On your server, create a session first: the secret key itself never calls `ai()`.

```python
s = oryksa.create_session(ttl_minutes=5)
r = OryksaClient(token=s["client_token"]).ai(instructions="Translate to Portuguese.", input="Good morning")
print(r.text)
```

## Attach a photo or a document

The AI looks at a photo (up to 2 MB) and reads a document (PDF, Word, text, CSV, up to 8 MB). `document_attachment` applies these limits and sends a small picture as a photo:

```python
from oryksa import document_attachment, document_from_path

att = document_attachment(document_from_path("quote.pdf"))
if "error" in att:
    print("Too large" if att["error"] == "big" else "Could not read the file")
else:
    r = client.send_and_wait("Can you check this quote?", **att)
```

Or directly: `client.send(text, image={"base64": ..., "mime": "image/jpeg"})` or `file={"base64": ..., "name": "quote.pdf", "mime": "application/pdf"}`. Also exported: `photo_attachment`, `mime_of`, `base64_bytes`, `scaled_size` (the size to resize a photo to, 1600 px), `MAX_PHOTO_BYTES` and `MAX_FILE_BYTES`.

## Links in the replies

`links_in(text)` gives the web links of a reply (3 at most, without the final punctuation), `without_links(text)` the text without them and `link_parts(text)` the text in pieces with a `url` on each link (web, and e-mail as `mailto:`). `client.link_preview(url)` gives the title and picture of a link, for a card with an **Open** button: only the pages of the business's own site (the domains of its website chat) get them, and it returns `None` when the page cannot be read.

## Async

Every client has an async twin with the same methods: `AsyncOryksa` and `AsyncOryksaClient` (its `get_token` may be sync or async).

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

Pass the raw body (the bytes as received, before any JSON parsing). Create the webhook with `oryksa.webhooks.create(url, events=[...])`: the answer has the `secret`.

## Server methods

The same names as the JavaScript SDK (`@oryksa/sdk`), in snake_case. The answers are the JSON of the API, as `dict`.

| Method | API |
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

Options of every client: `base_url` (default `https://api.oryksa.com/v1`), `timeout` in seconds (default 60) and `http_client` (your own `httpx.Client` or `httpx.AsyncClient`, for proxies). Use them with `with` / `async with`, or call `close()` / `aclose()`.

## Errors

Every failed call raises `OryksaError` with `status`, `code` (for example `interaction_limit_reached`, `rate_limited`, `plan_required`, `session_expired`) and `message`; the other fields of the API error, such as `upgrade_url` and `retry_after`, are attributes too. When ORYKSA cannot be reached: `status` 0 and `code` `network_error`. Wrong arguments (no key, the secret key in `OryksaClient`, `ai()` without instructions, input or an image) raise `ValueError` before anything is sent.

## About the author

**Weslley Harakawa** - Founder of ORYKSA AI. Based in Lisbon, Portugal. Specialties: artificial intelligence, web and mobile development, blockchain tokenization. Education: University of the People.

- LinkedIn: https://www.linkedin.com/in/weslleyharakawa/
- ORYKSA AI Employees: https://oryksa.com (X: https://x.com/oryksa, Instagram: https://www.instagram.com/oryksaai, YouTube: https://www.youtube.com/@ORYKSA)

---

MIT License · ORYKSA AI Employees · W8 Atlantic Unipessoal Lda
