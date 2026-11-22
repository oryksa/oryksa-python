"""Offline tests: no key, no network. Every request goes to an httpx.MockTransport that records it."""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
import pytest

SECRET = "oryk_live_test_example_key"
TOKEN = "oryk_cs_test_example_token"

Answer = Union[Tuple[int, Any], Callable[[httpx.Request], httpx.Response]]


class Recorder:
    """Answers each request with the next queued answer (default 200 {}) and keeps what was sent."""

    def __init__(self) -> None:
        self.requests: List[httpx.Request] = []
        self.answers: List[Answer] = []

    def queue(self, status: int = 200, body: Any = None, raw: Optional[bytes] = None) -> "Recorder":
        self.answers.append((status, raw if raw is not None else body))
        return self

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self.answers:
            return httpx.Response(200, json={})
        a = self.answers.pop(0)
        if callable(a):
            return a(request)
        status, body = a
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        if body is None:
            return httpx.Response(status)
        return httpx.Response(status, json=body)

    # what the last (or the n-th) request carried
    def req(self, n: int = -1) -> httpx.Request:
        return self.requests[n]

    def body(self, n: int = -1) -> Dict[str, Any]:
        return json.loads(self.requests[n].content)

    def target(self, n: int = -1) -> str:
        """Method and the path with its query, exactly as sent."""
        r = self.requests[n]
        return r.method + " " + r.url.raw_path.decode("ascii")

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def rec() -> Recorder:
    return Recorder()
