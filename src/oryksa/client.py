"""App clients: they only use a short-lived session token (oryk_cs_...), never the secret key.

Your server creates the token with ``Oryksa.create_session()``. Pass ``get_token`` so the client can
ask your server for a new token when the current one expires.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Sequence, Union

import httpx

from . import _api as api
from ._http import DEFAULT_TIMEOUT, AsyncTransport, Req, SyncTransport, as_dict
from .errors import OryksaError
from .types import AgentInfo, AiResult, ChatFile, ChatImage, ChatReply, Conversation, LinkPreview

_MAX_PREVIEWS = 200


class OryksaClient:
    """In-app client (a desktop app, a worker, a script, or your server acting for one app user).

    The session token can chat inside ONE conversation, read the public look of the AI employee,
    run ``ai()`` tasks and read link previews. It cannot touch the account, the knowledge, the
    webhooks or create other sessions.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        get_token: Optional[Callable[[], str]] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._token = api.session_token(token, get_token, "OryksaClient")
        self._get_token = get_token
        self._t = SyncTransport(base_url, timeout, http_client)
        self._previews: Dict[str, LinkPreview] = {}

    def _tok(self, force: bool) -> str:
        if (not self._token or force) and self._get_token is not None:
            t: Any = self._get_token()
            if inspect.isawaitable(t):
                close = getattr(t, "close", None)
                if callable(close):
                    close()
                raise TypeError("get_token returned an awaitable: use AsyncOryksaClient for an async get_token.")
            self._token = api.checked_token(t)
        return api.checked_token(self._token)

    def _call(self, req: Req) -> Dict[str, Any]:
        try:
            return as_dict(self._t.send(self._tok(False), req))
        except OryksaError as e:
            if api.should_refresh(e) and self._get_token is not None:
                return as_dict(self._t.send(self._tok(True), req))
            raise

    def agent(self) -> AgentInfo:
        """Name, photo, greeting and suggestions of the AI employee."""
        return self._call(api.client_agent())  # type: ignore[return-value]

    def send(self, message: str, *, image: Optional[ChatImage] = None, file: Optional[ChatFile] = None) -> ChatReply:
        """Sends a message. ``image``: a photo ({base64, mime}, up to 2 MB), the AI looks at it.
        ``file``: a document ({base64, name, mime}: PDF, Word, text, CSV, up to 8 MB), the AI reads it.
        ``status`` is ``pending`` when the AI needs a few more seconds: use :meth:`send_and_wait`.
        """
        return self._call(api.client_send(message, image, file))  # type: ignore[return-value]

    def send_and_wait(
        self,
        message: str,
        *,
        image: Optional[ChatImage] = None,
        file: Optional[ChatFile] = None,
        max_wait: float = 40.0,
        poll_interval: float = 1.5,
    ) -> ChatReply:
        """Like :meth:`send`, but when the reply is ``pending`` it reads the conversation until the AI's
        answer lands (up to ``max_wait`` seconds). Still ``pending`` after that: read :meth:`messages` later.
        """
        r = self.send(message, image=image, file=file)
        if r.get("status") != "pending":
            return r
        end = time.monotonic() + max_wait
        while time.monotonic() < end:
            time.sleep(poll_interval)
            done = api.replied(r, api.last_message(self.messages()))
            if done is not None:
                return done  # type: ignore[return-value]
        return r

    def messages(self) -> Conversation:
        """Messages of this conversation."""
        return self._call(api.client_messages())  # type: ignore[return-value]

    def ai(
        self,
        *,
        instructions: Optional[str] = None,
        input: Optional[str] = None,
        images: Optional[Sequence[ChatImage]] = None,
        schema: Optional[Mapping[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AiResult:
        """An AI task of your own app, counted as ORYKSA interactions (1 per answer): read a photo,
        extract data, classify, translate, write. It never creates a conversation in the business's
        inbox and never acts on the account. Your prompt (``instructions``) and your JSON Schema
        (``schema``) live in your code. ``images``: up to 4 photos ({base64, mime}, about 1.5 MB each;
        resize to 1600 px). With a schema, the answer is in ``result.json``.
        """
        req = api.client_ai(
            instructions=instructions, input=input, images=images, schema=schema, max_tokens=max_tokens, temperature=temperature
        )
        return api.ai_result(self._call(req))

    def link_preview(self, url: str) -> Optional[LinkPreview]:
        """Title and picture of a link the AI gave: {object, url, title, image, site, price}. Only the
        pages of the business's own site (its website chat domains) get a title and a picture.
        None when it cannot be read; never raises. Kept in memory for this client.
        """
        key = "" if url is None else str(url)
        hit = self._previews.get(key)
        if hit is not None:
            return dict(hit)  # type: ignore[return-value]
        try:
            p = api.link_preview_of(self._call(api.client_link_preview(key)))
        except Exception:
            return None
        if len(self._previews) > _MAX_PREVIEWS:
            self._previews.clear()
        self._previews[key] = p
        return dict(p)  # type: ignore[return-value]

    def close(self) -> None:
        """Closes the HTTP connections (not the ``http_client`` you passed)."""
        self._t.close()

    def __enter__(self) -> "OryksaClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncOryksaClient:
    """:class:`OryksaClient` for asyncio: the same methods, awaited. ``get_token`` may be sync or async."""

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        get_token: Optional[Callable[[], Union[str, Awaitable[str]]]] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._token = api.session_token(token, get_token, "AsyncOryksaClient")
        self._get_token = get_token
        self._t = AsyncTransport(base_url, timeout, http_client)
        self._previews: Dict[str, LinkPreview] = {}

    async def _tok(self, force: bool) -> str:
        if (not self._token or force) and self._get_token is not None:
            t: Any = self._get_token()
            if inspect.isawaitable(t):
                t = await t
            self._token = api.checked_token(t)
        return api.checked_token(self._token)

    async def _call(self, req: Req) -> Dict[str, Any]:
        try:
            return as_dict(await self._t.send(await self._tok(False), req))
        except OryksaError as e:
            if api.should_refresh(e) and self._get_token is not None:
                return as_dict(await self._t.send(await self._tok(True), req))
            raise

    async def agent(self) -> AgentInfo:
        return await self._call(api.client_agent())  # type: ignore[return-value]

    async def send(self, message: str, *, image: Optional[ChatImage] = None, file: Optional[ChatFile] = None) -> ChatReply:
        return await self._call(api.client_send(message, image, file))  # type: ignore[return-value]

    async def send_and_wait(
        self,
        message: str,
        *,
        image: Optional[ChatImage] = None,
        file: Optional[ChatFile] = None,
        max_wait: float = 40.0,
        poll_interval: float = 1.5,
    ) -> ChatReply:
        r = await self.send(message, image=image, file=file)
        if r.get("status") != "pending":
            return r
        end = time.monotonic() + max_wait
        while time.monotonic() < end:
            await asyncio.sleep(poll_interval)
            done = api.replied(r, api.last_message(await self.messages()))
            if done is not None:
                return done  # type: ignore[return-value]
        return r

    async def messages(self) -> Conversation:
        return await self._call(api.client_messages())  # type: ignore[return-value]

    async def ai(
        self,
        *,
        instructions: Optional[str] = None,
        input: Optional[str] = None,
        images: Optional[Sequence[ChatImage]] = None,
        schema: Optional[Mapping[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AiResult:
        req = api.client_ai(
            instructions=instructions, input=input, images=images, schema=schema, max_tokens=max_tokens, temperature=temperature
        )
        return api.ai_result(await self._call(req))

    async def link_preview(self, url: str) -> Optional[LinkPreview]:
        key = "" if url is None else str(url)
        hit = self._previews.get(key)
        if hit is not None:
            return dict(hit)  # type: ignore[return-value]
        try:
            p = api.link_preview_of(await self._call(api.client_link_preview(key)))
        except Exception:
            return None
        if len(self._previews) > _MAX_PREVIEWS:
            self._previews.clear()
        self._previews[key] = p
        return dict(p)  # type: ignore[return-value]

    async def aclose(self) -> None:
        await self._t.aclose()

    async def __aenter__(self) -> "AsyncOryksaClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
