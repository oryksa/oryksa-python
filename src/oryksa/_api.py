"""The calls of the ORYKSA API v1, built once and run by the sync and the async clients.

Every path, field and default here is the one the JS SDK (@oryksa/sdk 0.1.5) sends.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from ._http import Req, compact, q
from .errors import OryksaError
from .types import AiResult, ChatFile, ChatImage, LinkPreview

SECRET_PREFIX = "oryk_live_"
PLATFORM = "python"
MAX_AI_IMAGES = 4


# ------------------------------------------------------------------ keys and tokens

def secret_key(api_key: Any) -> str:
    if not api_key or not str(api_key).startswith(SECRET_PREFIX):
        raise ValueError("An ORYKSA API key (oryk_live_...) is required. Create one at developer.oryksa.com.")
    return str(api_key)


def session_token(token: Any, get_token: Any, cls: str) -> Optional[str]:
    if not token and get_token is None:
        raise ValueError(cls + " needs token= or get_token=.")
    if token and str(token).startswith(SECRET_PREFIX):
        raise ValueError("Never use the secret API key in an app. Use a session token (oryk_cs_...).")
    return str(token) if token else None


def checked_token(t: Any) -> str:
    """What get_token returned, checked like the token given to the constructor."""
    if t and str(t).startswith(SECRET_PREFIX):
        raise ValueError("Never use the secret API key in an app. Use a session token (oryk_cs_...).")
    if not t:
        raise OryksaError(401, "no_token", "No session token.")
    return str(t)


def should_refresh(e: OryksaError) -> bool:
    """A session token that expired (or was refused): ask get_token for a new one and try once more."""
    return e.code == "session_expired" or e.status == 401


def _fields(fields: Optional[Mapping[str, Any]], more: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(fields or {})
    out.update(more)
    return out


def _strings(v: Union[str, Iterable[str]]) -> List[str]:
    return [v] if isinstance(v, str) else list(v)


# ------------------------------------------------------------------ server (secret key)

def account() -> Req:
    return Req("GET", "/account")


def chat(message: str, conversation_id: Optional[str], customer_name: Optional[str]) -> Req:
    return Req("POST", "/chat", compact({"message": message, "conversation_id": conversation_id, "customer_name": customer_name}))


def conversations(limit: Optional[int]) -> Req:
    return Req("GET", "/conversations" + ("?limit=%d" % int(limit) if limit else ""))


def conversation(conversation_id: str) -> Req:
    return Req("GET", "/conversations/" + q(conversation_id))


def agent_update(fields: Optional[Mapping[str, Any]], more: Mapping[str, Any]) -> Req:
    return Req("PATCH", "/agent", _fields(fields, more))


def agent_appearance(fields: Optional[Mapping[str, Any]], more: Mapping[str, Any]) -> Req:
    return Req("PATCH", "/agent/appearance", _fields(fields, more))


def knowledge_get() -> Req:
    return Req("GET", "/knowledge")


def knowledge_set_pages(pages: Iterable[Mapping[str, Any]], business_summary: Optional[str], site_url: Optional[str]) -> Req:
    return Req("PUT", "/knowledge/pages", compact({"pages": [dict(p) for p in pages], "business_summary": business_summary, "site_url": site_url}))


def knowledge_crawl(url: str, max_pages: Optional[int]) -> Req:
    return Req("POST", "/knowledge/crawl", compact({"url": url, "max_pages": max_pages}))


def knowledge_add_faq(items: Iterable[Mapping[str, Any]]) -> Req:
    return Req("POST", "/knowledge/faq", {"items": [dict(i) for i in items]})


def widget_snippet(framework: str, lang: str, position: str) -> Req:
    return Req("GET", "/widget?framework=%s&lang=%s&position=%s" % (q(framework), q(lang), q(position)))


def widget_set_domains(domains: Union[str, Iterable[str]]) -> Req:
    return Req("PUT", "/widget/domains", {"domains": _strings(domains)})


def webhooks_list() -> Req:
    return Req("GET", "/webhooks")


def webhooks_create(url: str, events: Union[str, Iterable[str]]) -> Req:
    return Req("POST", "/webhooks", {"url": url, "events": _strings(events)})


def webhooks_delete(webhook_id: str) -> Req:
    return Req("DELETE", "/webhooks/" + q(webhook_id))


def webhooks_test(webhook_id: str) -> Req:
    return Req("POST", "/webhooks/" + q(webhook_id) + "/test")


def create_session(
    conversation_id: Optional[str],
    customer_name: Optional[str],
    customer_email: Optional[str],
    customer_phone: Optional[str],
    ttl_minutes: Optional[int],
) -> Req:
    return Req("POST", "/sessions", compact({
        "conversation_id": conversation_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "ttl_minutes": ttl_minutes,
    }))


def _setting_text(v: Any) -> str:
    """A settings value as JavaScript writes it in a template string (objects as compact JSON)."""
    if v is None or isinstance(v, (dict, list, tuple)):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def learn_app_plan(
    name: str,
    description: Optional[str],
    url: Optional[str],
    agent_name: Optional[str],
    languages: Optional[Sequence[str]],
    services: Optional[Sequence[str]],
    screens: Optional[Iterable[Mapping[str, Any]]],
    faq: Optional[Sequence[Mapping[str, Any]]],
    settings: Optional[Mapping[str, Any]],
) -> Tuple[Dict[str, Any], Optional[Req], Optional[Req]]:
    """learn_app as three calls: the profile (PATCH /agent), the pages (PUT /knowledge/pages), the FAQ (POST /knowledge/faq)."""
    if not name:
        raise ValueError("learn_app needs at least a name.")
    profile: Dict[str, Any] = {"business_name": name}
    if description:
        profile["business_description"] = description
    if agent_name:
        profile["agent_name"] = agent_name
    if isinstance(languages, (list, tuple)):
        profile["languages"] = list(languages)
    if isinstance(services, (list, tuple)):
        profile["services"] = list(services)
    pages: List[Dict[str, Any]] = []
    if description:
        pages.append({"title": name + " - overview", "content": description})
    for s in screens or []:
        if s and s.get("content"):
            pages.append(compact({"title": s.get("title") or "Screen", "url": s.get("url"), "content": str(s["content"])}))
    if isinstance(settings, Mapping):
        lines = ["%s: %s" % (k, _setting_text(v)) for k, v in settings.items()]
        pages.append({"title": name + " - configuration", "content": "\n".join(lines)})
    pages_req = knowledge_set_pages(pages, None, url) if pages else None
    faq_req = knowledge_add_faq(faq) if isinstance(faq, (list, tuple)) and faq else None
    return profile, pages_req, faq_req


# ------------------------------------------------------------------ app (session token)

def client_agent() -> Req:
    return Req("GET", "/client/agent")


def client_messages() -> Req:
    return Req("GET", "/client/messages")


def chat_body(message: str, image: Optional[ChatImage] = None, file: Optional[ChatFile] = None) -> Dict[str, Any]:
    """The JSON of POST /v1/client/chat: a photo as image_base64 / image_mime, a document as file_base64 / file_name / file_mime."""
    body: Dict[str, Any] = {"message": message}
    if image and image.get("base64"):
        body["image_base64"] = image["base64"]
        body["image_mime"] = image.get("mime") or "image/jpeg"
    if file and isinstance(file.get("base64"), str):
        body["file_base64"] = file["base64"]
        body["file_name"] = file.get("name") or "file"
        body["file_mime"] = file.get("mime") or "application/octet-stream"
    return body


def client_send(message: str, image: Optional[ChatImage], file: Optional[ChatFile]) -> Req:
    return Req("POST", "/client/chat", chat_body(message, image, file))


def client_link_preview(url: str) -> Req:
    return Req("GET", "/client/link-preview?url=" + q(url))


def ai_body(
    *,
    instructions: Optional[str] = None,
    input: Optional[str] = None,
    images: Optional[Sequence[ChatImage]] = None,
    schema: Optional[Mapping[str, Any]] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """The JSON of POST /v1/client/ai. Raises ValueError without instructions, input or an image, or with more than 4 images."""
    if isinstance(images, Mapping):
        raise TypeError("images is a list of {'base64': ..., 'mime': ...}.")
    imgs = list(images or [])
    for i in imgs:
        if not isinstance(i, Mapping):
            raise TypeError("each image is a dict {'base64': ..., 'mime': ...}.")
    if not instructions and not input and not imgs:
        raise ValueError("ai() needs instructions, input or an image.")
    if len(imgs) > MAX_AI_IMAGES:
        raise ValueError("ai() takes at most 4 images.")
    body: Dict[str, Any] = {"platform": PLATFORM}
    if instructions:
        body["instructions"] = str(instructions)
    if input:
        body["input"] = str(input)
    if imgs:
        body["images"] = [{"base64": i.get("base64"), "mime": i.get("mime") or "image/jpeg"} for i in imgs]
    if schema is not None:
        body["schema"] = dict(schema)
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if temperature is not None:
        body["temperature"] = temperature
    return body


def client_ai(**opts: Any) -> Req:
    return Req("POST", "/client/ai", ai_body(**opts))


def _int(v: Any, default: Optional[int]) -> Optional[int]:
    if v is None or isinstance(v, bool):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def ai_result(d: Any) -> AiResult:
    """Reads an ai_result answer."""
    d = d if isinstance(d, dict) else {}
    use = d.get("oryksa") if isinstance(d.get("oryksa"), dict) else {}
    j = d.get("json")
    return AiResult(
        text=str(d.get("text") or ""),
        json=j if isinstance(j, (dict, list)) else None,
        interactions_spent=_int(use.get("interactions_spent"), 0) or 0,
        interactions_remaining=_int(use.get("interactions_remaining"), None),
    )


def _text(v: Any) -> str:
    """A value as text, as JavaScript's String() writes it (None is empty)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return str(int(v))
    return str(v)


def link_preview_of(d: Any) -> LinkPreview:
    d = d if isinstance(d, dict) else {}
    return {
        "object": "link_preview",
        "url": _text(d.get("url")),
        "title": _text(d.get("title")),
        "image": _text(d.get("image")),
        "site": _text(d.get("site")),
        "price": _text(d.get("price")),
    }


def replied(r: Mapping[str, Any], last: Any) -> Optional[Dict[str, Any]]:
    """send_and_wait: the reply once the last message of the conversation is the AI's."""
    if isinstance(last, dict) and last.get("role") == "assistant":
        return {"object": "chat_reply", "conversation_id": r.get("conversation_id"), "status": "replied", "reply": last.get("content")}
    return None


def last_message(conv: Mapping[str, Any]) -> Any:
    msgs = conv.get("messages")
    return msgs[-1] if isinstance(msgs, list) and msgs else None
