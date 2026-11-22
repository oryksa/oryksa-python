"""Server-side clients: they use the SECRET API key (oryk_live_...). Never ship it in an app or a browser."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Iterable, Mapping, Optional, Sequence, Union

import httpx

from . import _api as api
from ._http import DEFAULT_TIMEOUT, AsyncTransport, Req, SyncTransport, as_dict
from .types import ChatReply, ClientSession, Conversation

_Call = Callable[[Req], Dict[str, Any]]
_AsyncCall = Callable[[Req], Awaitable[Dict[str, Any]]]


# ------------------------------------------------------------------ sync

class AgentAPI:
    """``oryksa.agent``: the profile and the look of the AI employee."""

    def __init__(self, call: _Call) -> None:
        self._call = call

    def update(self, fields: Optional[Mapping[str, Any]] = None, /, **more: Any) -> Dict[str, Any]:
        """PATCH /v1/agent: business_name, agent_name, business_description, services, languages, tone..."""
        return self._call(api.agent_update(fields, more))

    def appearance(self, fields: Optional[Mapping[str, Any]] = None, /, **more: Any) -> Dict[str, Any]:
        """PATCH /v1/agent/appearance: agent_name, gender, avatar_url, greeting, subtitle, suggestions."""
        return self._call(api.agent_appearance(fields, more))


class KnowledgeAPI:
    """``oryksa.knowledge``: what the AI employee knows (the Brain)."""

    def __init__(self, call: _Call) -> None:
        self._call = call

    def get(self) -> Dict[str, Any]:
        return self._call(api.knowledge_get())

    def set_pages(
        self, pages: Iterable[Mapping[str, Any]], *, business_summary: Optional[str] = None, site_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """PUT /v1/knowledge/pages with pages = [{title, url, content}]."""
        return self._call(api.knowledge_set_pages(pages, business_summary, site_url))

    def crawl(self, url: str, *, max_pages: Optional[int] = None) -> Dict[str, Any]:
        return self._call(api.knowledge_crawl(url, max_pages))

    def add_faq(self, items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        """POST /v1/knowledge/faq with items = [{question, answer}]."""
        return self._call(api.knowledge_add_faq(items))


class WidgetAPI:
    """``oryksa.widget``: the website chat."""

    def __init__(self, call: _Call) -> None:
        self._call = call

    def snippet(self, *, framework: str = "html", lang: str = "", position: str = "") -> Dict[str, Any]:
        return self._call(api.widget_snippet(framework, lang, position))

    def set_domains(self, domains: Union[str, Iterable[str]]) -> Dict[str, Any]:
        return self._call(api.widget_set_domains(domains))


class WebhooksAPI:
    """``oryksa.webhooks``: events sent to your server (check them with ``verify_webhook``)."""

    def __init__(self, call: _Call) -> None:
        self._call = call

    def list(self) -> Dict[str, Any]:
        return self._call(api.webhooks_list())

    def create(self, url: str, *, events: Union[str, Iterable[str]] = ("*",)) -> Dict[str, Any]:
        """POST /v1/webhooks. The answer has the ``secret`` (whsec_...) to check the signature."""
        return self._call(api.webhooks_create(url, events))

    def delete(self, webhook_id: str) -> Dict[str, Any]:
        return self._call(api.webhooks_delete(webhook_id))

    def test(self, webhook_id: str) -> Dict[str, Any]:
        return self._call(api.webhooks_test(webhook_id))


class Oryksa:
    """Server-side client. Uses the SECRET API key (``oryk_live_...``): keep it on your server.

    Apps get a short-lived session token from :meth:`create_session` and use ``OryksaClient``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._key = api.secret_key(api_key)
        self._t = SyncTransport(base_url, timeout, http_client)
        self.agent = AgentAPI(self._call)
        self.knowledge = KnowledgeAPI(self._call)
        self.widget = WidgetAPI(self._call)
        self.webhooks = WebhooksAPI(self._call)

    def _call(self, req: Req) -> Dict[str, Any]:
        return as_dict(self._t.send(self._key, req))

    def account(self) -> Dict[str, Any]:
        return self._call(api.account())

    def chat(self, message: str, *, conversation_id: Optional[str] = None, customer_name: Optional[str] = None) -> ChatReply:
        """Chat with the AI employee. Reuse ``conversation_id`` to keep the context.

        ``status`` is ``pending`` (HTTP 202) when the reply takes longer: read it later with :meth:`conversation`.
        """
        return self._call(api.chat(message, conversation_id, customer_name))  # type: ignore[return-value]

    def conversations(self, *, limit: Optional[int] = None) -> Dict[str, Any]:
        return self._call(api.conversations(limit))

    def conversation(self, conversation_id: str) -> Conversation:
        return self._call(api.conversation(conversation_id))  # type: ignore[return-value]

    def create_session(
        self,
        *,
        conversation_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        ttl_minutes: Optional[int] = 60,
    ) -> ClientSession:
        """Short-lived token for an app user. Send only ``client_token`` to the app.

        For a user signed in to your app, pass ``customer_email`` and/or ``customer_phone`` (with the
        country code): the AI then asks for no contact details and knows the customer is signed in.
        """
        req = api.create_session(conversation_id, customer_name, customer_email, customer_phone, ttl_minutes)
        return self._call(req)  # type: ignore[return-value]

    def learn_app(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        url: Optional[str] = None,
        agent_name: Optional[str] = None,
        languages: Optional[Sequence[str]] = None,
        services: Optional[Sequence[str]] = None,
        screens: Optional[Iterable[Mapping[str, Any]]] = None,
        faq: Optional[Sequence[Mapping[str, Any]]] = None,
        settings: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Teach the AI employee about an app: what it is, its screens and its FAQ (for example on every release).

        Returns ``{"agent": ..., "pages": ..., "faq": ...}`` (the answers of the calls it made).
        """
        profile, pages, faq_req = api.learn_app_plan(name, description, url, agent_name, languages, services, screens, faq, settings)
        out: Dict[str, Any] = {"agent": self.agent.update(profile)}
        if pages is not None:
            out["pages"] = self._call(pages)
        if faq_req is not None:
            out["faq"] = self._call(faq_req)
        return out

    def close(self) -> None:
        """Closes the HTTP connections (not the ``http_client`` you passed)."""
        self._t.close()

    def __enter__(self) -> "Oryksa":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# ------------------------------------------------------------------ async

class AsyncAgentAPI:
    """``oryksa.agent`` of :class:`AsyncOryksa`."""

    def __init__(self, call: _AsyncCall) -> None:
        self._call = call

    async def update(self, fields: Optional[Mapping[str, Any]] = None, /, **more: Any) -> Dict[str, Any]:
        return await self._call(api.agent_update(fields, more))

    async def appearance(self, fields: Optional[Mapping[str, Any]] = None, /, **more: Any) -> Dict[str, Any]:
        return await self._call(api.agent_appearance(fields, more))


class AsyncKnowledgeAPI:
    """``oryksa.knowledge`` of :class:`AsyncOryksa`."""

    def __init__(self, call: _AsyncCall) -> None:
        self._call = call

    async def get(self) -> Dict[str, Any]:
        return await self._call(api.knowledge_get())

    async def set_pages(
        self, pages: Iterable[Mapping[str, Any]], *, business_summary: Optional[str] = None, site_url: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._call(api.knowledge_set_pages(pages, business_summary, site_url))

    async def crawl(self, url: str, *, max_pages: Optional[int] = None) -> Dict[str, Any]:
        return await self._call(api.knowledge_crawl(url, max_pages))

    async def add_faq(self, items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        return await self._call(api.knowledge_add_faq(items))


class AsyncWidgetAPI:
    """``oryksa.widget`` of :class:`AsyncOryksa`."""

    def __init__(self, call: _AsyncCall) -> None:
        self._call = call

    async def snippet(self, *, framework: str = "html", lang: str = "", position: str = "") -> Dict[str, Any]:
        return await self._call(api.widget_snippet(framework, lang, position))

    async def set_domains(self, domains: Union[str, Iterable[str]]) -> Dict[str, Any]:
        return await self._call(api.widget_set_domains(domains))


class AsyncWebhooksAPI:
    """``oryksa.webhooks`` of :class:`AsyncOryksa`."""

    def __init__(self, call: _AsyncCall) -> None:
        self._call = call

    async def list(self) -> Dict[str, Any]:
        return await self._call(api.webhooks_list())

    async def create(self, url: str, *, events: Union[str, Iterable[str]] = ("*",)) -> Dict[str, Any]:
        return await self._call(api.webhooks_create(url, events))

    async def delete(self, webhook_id: str) -> Dict[str, Any]:
        return await self._call(api.webhooks_delete(webhook_id))

    async def test(self, webhook_id: str) -> Dict[str, Any]:
        return await self._call(api.webhooks_test(webhook_id))


class AsyncOryksa:
    """:class:`Oryksa` for asyncio (FastAPI, aiohttp, Starlette...): the same methods, awaited."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._key = api.secret_key(api_key)
        self._t = AsyncTransport(base_url, timeout, http_client)
        self.agent = AsyncAgentAPI(self._call)
        self.knowledge = AsyncKnowledgeAPI(self._call)
        self.widget = AsyncWidgetAPI(self._call)
        self.webhooks = AsyncWebhooksAPI(self._call)

    async def _call(self, req: Req) -> Dict[str, Any]:
        return as_dict(await self._t.send(self._key, req))

    async def account(self) -> Dict[str, Any]:
        return await self._call(api.account())

    async def chat(self, message: str, *, conversation_id: Optional[str] = None, customer_name: Optional[str] = None) -> ChatReply:
        return await self._call(api.chat(message, conversation_id, customer_name))  # type: ignore[return-value]

    async def conversations(self, *, limit: Optional[int] = None) -> Dict[str, Any]:
        return await self._call(api.conversations(limit))

    async def conversation(self, conversation_id: str) -> Conversation:
        return await self._call(api.conversation(conversation_id))  # type: ignore[return-value]

    async def create_session(
        self,
        *,
        conversation_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        ttl_minutes: Optional[int] = 60,
    ) -> ClientSession:
        req = api.create_session(conversation_id, customer_name, customer_email, customer_phone, ttl_minutes)
        return await self._call(req)  # type: ignore[return-value]

    async def learn_app(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        url: Optional[str] = None,
        agent_name: Optional[str] = None,
        languages: Optional[Sequence[str]] = None,
        services: Optional[Sequence[str]] = None,
        screens: Optional[Iterable[Mapping[str, Any]]] = None,
        faq: Optional[Sequence[Mapping[str, Any]]] = None,
        settings: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        profile, pages, faq_req = api.learn_app_plan(name, description, url, agent_name, languages, services, screens, faq, settings)
        out: Dict[str, Any] = {"agent": await self.agent.update(profile)}
        if pages is not None:
            out["pages"] = await self._call(pages)
        if faq_req is not None:
            out["faq"] = await self._call(faq_req)
        return out

    async def aclose(self) -> None:
        """Closes the HTTP connections (not the ``http_client`` you passed)."""
        await self._t.aclose()

    async def __aenter__(self) -> "AsyncOryksa":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
