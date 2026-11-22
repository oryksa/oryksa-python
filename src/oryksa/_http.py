"""HTTP plumbing shared by the sync and the async clients: one call is one JSON exchange."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, NamedTuple, Optional
from urllib.parse import quote

import httpx

from ._version import VERSION
from .errors import OryksaError

DEFAULT_BASE = "https://api.oryksa.com/v1"
DEFAULT_TIMEOUT = 60.0
SDK_HEADER = "python/" + VERSION
# The edge in front of the API blocks anonymous library user agents, so every request says who it is.
USER_AGENT = "oryksa-python/" + VERSION + " (+https://developer.oryksa.com)"


class Req(NamedTuple):
    """One API call: method, path under the base URL (with its query) and the JSON body (None: no body)."""

    method: str
    path: str
    body: Any = None


def compact(d: Mapping[str, Any]) -> Dict[str, Any]:
    """The body without the options that were not given (like JSON.stringify drops undefined)."""
    return {k: v for k, v in d.items() if v is not None}


def q(v: Any) -> str:
    """A path segment or a query value, fully percent-encoded."""
    return quote("" if v is None else str(v), safe="")


def headers(token: str, has_body: bool) -> Dict[str, str]:
    h = {
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "X-ORYKSA-SDK": SDK_HEADER,
    }
    if has_body:
        h["Content-Type"] = "application/json"
    return h


def encode(body: Any) -> bytes:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def handle(status: int, content: bytes) -> Any:
    """The JSON of a 2xx answer (None when there is none); OryksaError for anything else."""
    try:
        data = json.loads(content) if content else None
    except ValueError:
        data = None
    if 200 <= status < 300:
        return data
    err = data.get("error") if isinstance(data, dict) else None
    if not isinstance(err, dict):
        err = {}
    extra = {k: v for k, v in err.items() if k not in ("code", "message")}
    raise OryksaError(
        status,
        str(err.get("code") or "http_%d" % status),
        str(err.get("message") or "Request failed with HTTP %d" % status),
        extra,
    )


def network_error(e: Exception) -> OryksaError:
    detail = str(e)
    return OryksaError(0, "network_error", "Could not reach ORYKSA: " + type(e).__name__ + (": " + detail if detail else ""))


def as_dict(data: Any) -> Dict[str, Any]:
    return data if isinstance(data, dict) else {}


def _base(base_url: Optional[str]) -> str:
    return (base_url or DEFAULT_BASE).rstrip("/")


class SyncTransport:
    def __init__(self, base_url: Optional[str], timeout: Optional[float], http_client: Optional[httpx.Client]) -> None:
        self.base = _base(base_url)
        self.timeout = timeout or DEFAULT_TIMEOUT
        self._own = http_client is None
        self._http = http_client if http_client is not None else httpx.Client()

    def send(self, token: str, req: Req) -> Any:
        body = None if req.body is None else encode(req.body)
        try:
            r = self._http.request(
                req.method, self.base + req.path, headers=headers(token, body is not None), content=body, timeout=self.timeout
            )
        except httpx.RequestError as e:
            raise network_error(e) from e
        return handle(r.status_code, r.content)

    def close(self) -> None:
        if self._own:
            self._http.close()


class AsyncTransport:
    def __init__(self, base_url: Optional[str], timeout: Optional[float], http_client: Optional[httpx.AsyncClient]) -> None:
        self.base = _base(base_url)
        self.timeout = timeout or DEFAULT_TIMEOUT
        self._own = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient()

    async def send(self, token: str, req: Req) -> Any:
        body = None if req.body is None else encode(req.body)
        try:
            r = await self._http.request(
                req.method, self.base + req.path, headers=headers(token, body is not None), content=body, timeout=self.timeout
            )
        except httpx.RequestError as e:
            raise network_error(e) from e
        return handle(r.status_code, r.content)

    async def aclose(self) -> None:
        if self._own:
            await self._http.aclose()
