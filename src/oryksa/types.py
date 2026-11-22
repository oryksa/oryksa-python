"""Shapes of what goes to and comes back from the ORYKSA API.

The answers are plain ``dict`` objects (the JSON of the API); these ``TypedDict`` classes only
describe them for editors and type checkers. ``total=False``: the API may add fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict, Union


class ChatReply(TypedDict, total=False):
    """Answer of ``chat`` / ``send``: ``status`` is ``replied`` (with ``reply``) or ``pending`` (HTTP 202)."""

    object: str
    conversation_id: str
    status: str
    reply: Optional[str]
    hint: str


class Message(TypedDict, total=False):
    """One message of a conversation: ``role`` is ``user`` or ``assistant``."""

    role: str
    content: str


class Conversation(TypedDict, total=False):
    """A conversation and its messages (``conversation`` on the server, ``messages`` in the app)."""

    object: str
    id: str
    messages: List[Message]


class AgentInfo(TypedDict, total=False):
    """Public look of the AI employee (the same data the ORYKSA website chat shows)."""

    object: str
    name: str
    business: Optional[str]
    gender: str
    avatar: str
    greeting: Dict[str, str]
    suggestions: Dict[str, List[str]]
    subtitle: Dict[str, str]
    voice_replies: bool
    conversation_id: str


class ClientSession(TypedDict, total=False):
    """Answer of ``create_session``: send only ``client_token`` to the app."""

    object: str
    client_token: str
    conversation_id: str
    expires_at: str


class LinkPreview(TypedDict):
    """Title and picture of a link of the business's own site (``link_preview``). Every value is text."""

    object: str
    url: str
    title: str
    image: str
    site: str
    price: str


class _ChatImageRequired(TypedDict):
    base64: str


class ChatImage(_ChatImageRequired, total=False):
    """A photo (JPEG, PNG or WebP) as base64. ``mime`` defaults to ``image/jpeg``."""

    mime: str


class _ChatFileRequired(TypedDict):
    base64: str
    name: str


class ChatFile(_ChatFileRequired, total=False):
    """A document (PDF, Word, text or CSV) as base64. ``mime`` defaults to ``application/octet-stream``."""

    mime: str


AiJson = Union[Dict[str, Any], List[Any]]


@dataclass(frozen=True)
class AiResult:
    """The answer of ``ai()``.

    ``text``: the answer as text. ``json``: the object (when you sent a ``schema``), else None.
    ``interactions_spent``: ORYKSA interactions this answer used (1). ``interactions_remaining``:
    what is left in the plan, None when the plan has no limit.
    """

    text: str
    json: Optional[AiJson]
    interactions_spent: int
    interactions_remaining: Optional[int]


__all__ = [
    "ChatReply", "Message", "Conversation", "AgentInfo", "ClientSession", "LinkPreview",
    "ChatImage", "ChatFile", "AiJson", "AiResult",
]
