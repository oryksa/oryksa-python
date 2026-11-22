<p align="center"><img src="https://app.oryksa.com/static/oryksa_logo.png" width="300" alt="ORYKSA"></p>

# oryksa

[![English](https://img.shields.io/badge/English-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.md) [![Português](https://img.shields.io/badge/Portugu%C3%AAs-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.pt.md) [![Español](https://img.shields.io/badge/Espa%C3%B1ol-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.es.md) [![Français](https://img.shields.io/badge/Fran%C3%A7ais-0891b2?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.fr.md)

SDK officiel Python d'**ORYKSA AI Employees** : placez un employé IA qui connaît déjà l'entreprise dans votre backend Python, vos scripts et workers ou votre app de bureau. Le même cerveau que WhatsApp et le chat du site web.

- Documentation : https://developer.oryksa.com
- API : `https://api.oryksa.com/v1`
- Python 3.9 ou plus récent, une seule dépendance (`httpx`), clients synchrones et asynchrones, typés.

## Installer

```bash
pip install oryksa
```

## Serveur (clé secrète)

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

Quand la réponse prend plus de temps que l'API n'attend, `r["status"]` vaut `"pending"` (HTTP 202) : lisez-la plus tard avec `oryksa.conversation(r["conversation_id"])`.

## Dans l'app (jeton de session, jamais la clé secrète)

Votre serveur crée un jeton de session de courte durée avec la clé secrète et ne donne que ce jeton à l'app. Le jeton fonctionne dans UNE conversation.

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

`get_token` est appelé quand le client a besoin d'un jeton et à nouveau quand il expire (`session_expired`). Pour un utilisateur connecté à votre app, passez `customer_email` et/ou `customer_phone` (avec l'indicatif du pays) à `create_session` : l'IA ne demande plus de coordonnées et sait que le client est connecté.

| | Clé secrète : `Oryksa` | Jeton de session : `OryksaClient` |
|---|---|---|
| Où | uniquement sur votre serveur | apps, bureau, workers, ou votre serveur pour le compte d'un utilisateur |
| Chat | `chat()` dans n'importe quelle conversation | `send()`, `send_and_wait()`, `messages()` dans sa propre conversation |
| Tâches d'IA | créez d'abord une session | `ai()` |
| L'employé IA | `agent.update()`, `agent.appearance()` | `agent()` (nom, photo, salutation) |
| Compte, connaissances, chat web, webhooks, sessions | oui | non |

## Vos propres fonctions d'IA : `ai`

Faites faire à l'IA ce dont votre app ou site a besoin (lire une photo, extraire des données, classer, traduire, rédiger) et payez en interactions ORYKSA : 1 par réponse. Votre prompt et votre JSON Schema restent dans votre code ; le jeton de session suffit (n'embarquez jamais la clé secrète). Aucune conversation n'est créée dans votre boîte.

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

`r.text` contient la réponse en texte, `r.json` l'objet (avec un schema), `r.interactions_spent` les interactions utilisées et `r.interactions_remaining` ce qui reste dans le forfait. Jusqu'à 4 photos, environ 1,5 Mo chacune. Quand les interactions du forfait sont épuisées, l'appel lève `OryksaError` avec le status 402.

Sur votre serveur, créez d'abord une session : la clé secrète n'appelle jamais `ai()`.

```python
s = oryksa.create_session(ttl_minutes=5)
r = OryksaClient(token=s["client_token"]).ai(instructions="Translate to Portuguese.", input="Good morning")
print(r.text)
```

## Joindre une photo ou un document

L'IA regarde une photo (jusqu'à 2 Mo) et lit un document (PDF, Word, texte, CSV, jusqu'à 8 Mo). `document_attachment` applique ces limites et envoie une petite image comme photo :

```python
from oryksa import document_attachment, document_from_path

att = document_attachment(document_from_path("quote.pdf"))
if "error" in att:
    print("Too large" if att["error"] == "big" else "Could not read the file")
else:
    r = client.send_and_wait("Can you check this quote?", **att)
```

Ou directement : `client.send(texte, image={"base64": ..., "mime": "image/jpeg"})` ou `file={"base64": ..., "name": "quote.pdf", "mime": "application/pdf"}`. Aussi exportés : `photo_attachment`, `mime_of`, `base64_bytes`, `scaled_size` (la taille à laquelle réduire une photo, 1600 px), `MAX_PHOTO_BYTES` et `MAX_FILE_BYTES`.

## Les liens des réponses

`links_in(text)` donne les liens web d'une réponse (3 au maximum, sans la ponctuation finale), `without_links(text)` le texte sans eux et `link_parts(text)` le texte en morceaux avec une `url` sur chaque lien (web, et e-mail en `mailto:`). `client.link_preview(url)` donne le titre et la photo d'un lien, pour une carte avec un bouton pour l'ouvrir : seules les pages du propre site de l'entreprise (les domaines de son chat web) les ont, et elle renvoie `None` quand la page ne peut pas être lue.

## Asynchrone

Chaque client a un jumeau asynchrone avec les mêmes méthodes : `AsyncOryksa` et `AsyncOryksaClient` (son `get_token` peut être synchrone ou asynchrone).

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

Passez le corps brut (les octets tels que reçus, avant toute lecture du JSON). Créez le webhook avec `oryksa.webhooks.create(url, events=[...])` : la réponse contient le `secret`.

## Méthodes du serveur

Les mêmes noms que le SDK JavaScript (`@oryksa/sdk`), en snake_case. Les réponses sont le JSON de l'API, en `dict`.

| Méthode | API |
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

Options de tous les clients : `base_url` (par défaut `https://api.oryksa.com/v1`), `timeout` en secondes (par défaut 60) et `http_client` (votre propre `httpx.Client` ou `httpx.AsyncClient`, pour les proxys). Utilisez-les avec `with` / `async with`, ou appelez `close()` / `aclose()`.

## Erreurs

Chaque appel qui échoue lève `OryksaError` avec `status`, `code` (par exemple `interaction_limit_reached`, `rate_limited`, `plan_required`, `session_expired`) et `message` ; les autres champs de l'erreur de l'API, comme `upgrade_url` et `retry_after`, sont aussi des attributs. Quand ORYKSA est injoignable : `status` 0 et `code` `network_error`. Les mauvais arguments (pas de clé, la clé secrète dans `OryksaClient`, `ai()` sans instructions, texte ni image) lèvent `ValueError` avant tout envoi.

## À propos de l'auteur

**Weslley Harakawa** - Fondateur d'ORYKSA AI. À Lisbonne, Portugal. Spécialités : intelligence artificielle, développement web et mobile, tokenisation blockchain. Formation : University of the People.

- LinkedIn: https://www.linkedin.com/in/weslleyharakawa/
- ORYKSA AI Employees: https://oryksa.com (X: https://x.com/oryksa, Instagram: https://www.instagram.com/oryksaai, YouTube: https://www.youtube.com/@ORYKSA)

---

MIT License · ORYKSA AI Employees · W8 Atlantic Unipessoal Lda
