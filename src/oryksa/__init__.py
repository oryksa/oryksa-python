"""oryksa: the official Python SDK for ORYKSA AI Employees.

Server (secret key)::

    from oryksa import Oryksa
    oryksa = Oryksa(os.environ["ORYKSA_API_KEY"])
    print(oryksa.chat("Are you open on Saturday?")["reply"])

App (session token from ``oryksa.create_session()``, never the secret key)::

    from oryksa import OryksaClient
    client = OryksaClient(token=session["client_token"])
    result = client.ai(instructions="Translate to Portuguese.", input="Good morning")

Docs: https://developer.oryksa.com   License: MIT
"""

from ._api import ai_body, ai_result
from ._http import DEFAULT_BASE
from ._version import VERSION
from .attachments import (
    MAX_FILE_BYTES,
    MAX_PHOTO_BYTES,
    Size,
    base64_bytes,
    document_attachment,
    document_from_path,
    mime_of,
    photo_attachment,
    scaled_size,
)
from .client import AsyncOryksaClient, OryksaClient
from .errors import OryksaError
from .links import LinkPart, link_parts, links_in, without_links
from .server import AsyncOryksa, Oryksa
from .types import (
    AgentInfo,
    AiResult,
    ChatFile,
    ChatImage,
    ChatReply,
    ClientSession,
    Conversation,
    LinkPreview,
    Message,
)
from .webhooks import verify_webhook

__version__ = VERSION

__all__ = [
    "VERSION", "__version__", "DEFAULT_BASE",
    "Oryksa", "AsyncOryksa", "OryksaClient", "AsyncOryksaClient", "OryksaError", "verify_webhook",
    "ai_body", "ai_result", "AiResult",
    "MAX_PHOTO_BYTES", "MAX_FILE_BYTES", "Size", "mime_of", "base64_bytes", "scaled_size",
    "photo_attachment", "document_attachment", "document_from_path",
    "LinkPart", "links_in", "without_links", "link_parts",
    "AgentInfo", "ChatFile", "ChatImage", "ChatReply", "ClientSession", "Conversation", "LinkPreview", "Message",
]
