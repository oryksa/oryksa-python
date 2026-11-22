<p align="center"><img src="https://app.oryksa.com/static/oryksa_logo.png" width="300" alt="ORYKSA"></p>

# oryksa

[![English](https://img.shields.io/badge/English-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.md) [![Português](https://img.shields.io/badge/Portugu%C3%AAs-0891b2?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.pt.md) [![Español](https://img.shields.io/badge/Espa%C3%B1ol-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.es.md) [![Français](https://img.shields.io/badge/Fran%C3%A7ais-30363d?style=for-the-badge)](https://github.com/oryksa/oryksa-python/blob/main/README.fr.md)

SDK oficial de Python da **ORYKSA AI Employees**: põe um colaborador de IA que já conhece o negócio dentro do teu backend Python, dos teus scripts e workers ou da tua app de secretária. O mesmo cérebro do WhatsApp e do chat do site.

- Documentação: https://developer.oryksa.com
- API: `https://api.oryksa.com/v1`
- Python 3.10 ou mais recente, uma só dependência (`httpx`), clientes síncronos e assíncronos, com tipos.

## Instalar

```bash
pip install oryksa
```

## Servidor (chave secreta)

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

Quando a resposta demora mais do que a API espera, `r["status"]` é `"pending"` (HTTP 202): lê-a depois com `oryksa.conversation(r["conversation_id"])`.

## Na app (token de sessão, nunca a chave secreta)

O teu servidor cria um token de sessão de curta duração com a chave secreta e dá à app só esse token. O token funciona dentro de UMA conversa.

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

O `get_token` é chamado quando o cliente precisa de um token e outra vez quando ele expira (`session_expired`). Para um utilizador com sessão iniciada na tua app, passa `customer_email` e/ou `customer_phone` (com o indicativo do país) ao `create_session`: a IA deixa de pedir contactos e sabe que o cliente tem sessão iniciada.

| | Chave secreta: `Oryksa` | Token de sessão: `OryksaClient` |
|---|---|---|
| Onde | só no teu servidor | apps, secretária, workers, ou o teu servidor em nome de um utilizador |
| Chat | `chat()` em qualquer conversa | `send()`, `send_and_wait()`, `messages()` na sua própria conversa |
| Tarefas de IA | cria primeiro uma sessão | `ai()` |
| O colaborador de IA | `agent.update()`, `agent.appearance()` | `agent()` (nome, foto, saudação) |
| Conta, conhecimento, chat do site, webhooks, sessões | sim | não |

## As tuas funções de IA: `ai`

Põe a IA a fazer o que a tua app ou site precisa (ler uma foto, extrair dados, classificar, traduzir, escrever) e paga com interações ORYKSA: 1 por resposta. O teu prompt e o teu JSON Schema ficam no teu código; basta o token de sessão (nunca leves a chave secreta). Não cria conversa na tua caixa.

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

`r.text` tem a resposta em texto, `r.json` o objeto (com schema), `r.interactions_spent` as interações gastas e `r.interactions_remaining` o que resta no plano. Até 4 fotos, cerca de 1,5 MB cada. Quando as interações do plano acabam, a chamada lança `OryksaError` com status 402.

No teu servidor, cria primeiro uma sessão: a chave secreta nunca chama o `ai()`.

```python
s = oryksa.create_session(ttl_minutes=5)
r = OryksaClient(token=s["client_token"]).ai(instructions="Translate to Portuguese.", input="Good morning")
print(r.text)
```

## Anexar uma foto ou um documento

A IA vê uma foto (até 2 MB) e lê um documento (PDF, Word, texto, CSV, até 8 MB). O `document_attachment` aplica estes limites e envia uma imagem pequena como foto:

```python
from oryksa import document_attachment, document_from_path

att = document_attachment(document_from_path("quote.pdf"))
if "error" in att:
    print("Too large" if att["error"] == "big" else "Could not read the file")
else:
    r = client.send_and_wait("Can you check this quote?", **att)
```

Ou diretamente: `client.send(texto, image={"base64": ..., "mime": "image/jpeg"})` ou `file={"base64": ..., "name": "quote.pdf", "mime": "application/pdf"}`. Também são exportados: `photo_attachment`, `mime_of`, `base64_bytes`, `scaled_size` (o tamanho para reduzir uma foto, 1600 px), `MAX_PHOTO_BYTES` e `MAX_FILE_BYTES`.

## Links nas respostas

`links_in(text)` dá os links web de uma resposta (3 no máximo, sem a pontuação final), `without_links(text)` o texto sem eles e `link_parts(text)` o texto em pedaços com um `url` em cada link (web, e e-mail como `mailto:`). `client.link_preview(url)` dá o título e a foto de um link, para um cartão com um botão **Abrir**: só as páginas do próprio site do negócio (os domínios do seu chat do site) os têm, e devolve `None` quando a página não se consegue ler.

## Assíncrono

Cada cliente tem um gémeo assíncrono com os mesmos métodos: `AsyncOryksa` e `AsyncOryksaClient` (o seu `get_token` pode ser síncrono ou assíncrono).

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

Passa o corpo em bruto (os bytes tal como chegaram, antes de ler o JSON). Cria o webhook com `oryksa.webhooks.create(url, events=[...])`: a resposta traz o `secret`.

## Métodos do servidor

Os mesmos nomes do SDK de JavaScript (`@oryksa/sdk`), em snake_case. As respostas são o JSON da API, como `dict`.

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

Opções de todos os clientes: `base_url` (por omissão `https://api.oryksa.com/v1`), `timeout` em segundos (por omissão 60) e `http_client` (o teu próprio `httpx.Client` ou `httpx.AsyncClient`, para proxies). Usa-os com `with` / `async with`, ou chama `close()` / `aclose()`.

## Erros

Cada chamada falhada lança `OryksaError` com `status`, `code` (por exemplo `interaction_limit_reached`, `rate_limited`, `plan_required`, `session_expired`) e `message`; os outros campos do erro da API, como `upgrade_url` e `retry_after`, também são atributos. Quando não se consegue chegar à ORYKSA: `status` 0 e `code` `network_error`. Argumentos errados (sem chave, a chave secreta no `OryksaClient`, `ai()` sem instruções, texto ou imagem) lançam `ValueError` antes de se enviar seja o que for.

## Sobre o autor

**Weslley Harakawa** - Fundador da ORYKSA AI. Em Lisboa, Portugal. Especialidades: inteligência artificial, desenvolvimento web e mobile, tokenização em blockchain. Formação: University of the People.

- LinkedIn: https://www.linkedin.com/in/weslleyharakawa/
- ORYKSA AI Employees: https://oryksa.com (X: https://x.com/oryksa, Instagram: https://www.instagram.com/oryksaai, YouTube: https://www.youtube.com/@ORYKSA)

---

MIT License · ORYKSA AI Employees · W8 Atlantic Unipessoal Lda
