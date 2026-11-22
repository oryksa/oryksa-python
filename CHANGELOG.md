# Changelog

## 1.0.0

First version of the official Python SDK (`pip install oryksa`). The same calls as the JavaScript SDK (`@oryksa/sdk` 0.1.5), with the names in snake_case. Python 3.9 or newer; the only dependency is `httpx`.

- **Server client with the secret key: `Oryksa`.** `chat`, `conversations`, `conversation`, `account`, `create_session` (with `customer_email` / `customer_phone` for a signed-in user), `learn_app`, `agent.update` / `agent.appearance`, `knowledge.get` / `set_pages` / `crawl` / `add_faq`, `widget.snippet` / `set_domains` and `webhooks.list` / `create` / `delete` / `test`. A reply that is still being written comes back as `status: "pending"` (HTTP 202), not as an error.
- **App client with a session token: `OryksaClient`.** It never takes the secret key (`ValueError`). `agent`, `send`, `messages`, `ai`, `link_preview`, and `send_and_wait`, which reads the conversation until a pending reply lands (as `sendAndWait` in the Android, iOS and Flutter SDKs). `get_token` is asked for a new token when the current one expires (`session_expired` or HTTP 401), and the call is made once more.
- **The AI doing what your app needs: `client.ai(...)`.** Instructions, text, up to 4 photos and an optional JSON Schema; the answer comes back as `text` and, with a schema, as an object in `json`. Each answer counts as 1 ORYKSA interaction; it does not create a conversation and never acts on the account (`POST /v1/client/ai`). `ai_body` and `ai_result` are exported too.
- **Attachments.** `send(text, image=...)` / `send(text, file=...)` (`image_base64` / `image_mime`, `file_base64` / `file_name` / `file_mime`), with the limits of the ORYKSA chats: photos up to 2 MB, documents up to 8 MB. `document_from_path`, `document_attachment`, `photo_attachment`, `mime_of`, `base64_bytes`, `scaled_size`.
- **Links of the replies.** `links_in`, `without_links`, `link_parts` and `client.link_preview(url)` (`GET /v1/client/link-preview`, kept in memory, never raises).
- **Async twins**: `AsyncOryksa` and `AsyncOryksaClient`, the same methods awaited.
- **Webhooks**: `verify_webhook(raw_body, signature_header, secret)` checks `ORYKSA-Signature` (HMAC-SHA256, 5 minutes of tolerance).
- **Errors**: `OryksaError` with `status`, `code`, `message` and the other fields of the API error (`upgrade_url`, `retry_after`...); `status` 0 and `code` `network_error` when ORYKSA cannot be reached.
- Every request says `X-ORYKSA-SDK: python/1.0.0`; a test fails if the version in the code ever drifts from `pyproject.toml`.
- Offline tests with `pytest` and `httpx.MockTransport` (no key, no network); CI runs them on Python 3.9 to 3.13.
