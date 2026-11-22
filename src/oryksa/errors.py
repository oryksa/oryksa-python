"""The error every failed ORYKSA call raises."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

_OWN = ("status", "code", "message", "extra", "args", "upgrade_url", "retry_after")


class OryksaError(Exception):
    """An error returned by the ORYKSA API (or a network failure, with ``status`` 0).

    ``code`` is stable, for example ``interaction_limit_reached``, ``rate_limited``,
    ``plan_required``, ``session_expired``, ``invalid_request`` or ``network_error``.
    Any other field of the API error (``upgrade_url``, ``retry_after``, ``param``...) is in
    ``extra`` and also readable as an attribute.
    """

    status: int
    code: str
    message: str
    extra: Dict[str, Any]
    upgrade_url: Optional[str]
    retry_after: Optional[Any]

    def __init__(self, status: int, code: str, message: str, extra: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = dict(extra or {})
        self.upgrade_url = self.extra.get("upgrade_url")
        self.retry_after = self.extra.get("retry_after")
        for k, v in self.extra.items():
            if isinstance(k, str) and k.isidentifier() and k not in _OWN and not k.startswith("_"):
                setattr(self, k, v)

    def __reduce__(self) -> Tuple[Any, ...]:  # keeps the error picklable (multiprocessing, task queues)
        return (type(self), (self.status, self.code, self.message, self.extra))

    def __repr__(self) -> str:
        return "OryksaError(%r, %r, %r)" % (self.status, self.code, self.message)
