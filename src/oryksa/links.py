"""The links of the AI's replies: the same rules as the ORYKSA chats (cards with an Open button, tappable e-mails)."""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional

_URL = re.compile(r"""https?://[^\s<>"')\]]+""", re.IGNORECASE)
_MAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", re.ASCII)
_END = re.compile(r"[.,;:!?…]+$")


class LinkPart(NamedTuple):
    """A piece of a message: ``url`` is set only on the links (web, and e-mail as ``mailto:``)."""

    text: str
    url: Optional[str]


def _trim(u: str) -> str:
    return _END.sub("", u)


def links_in(text: Optional[str], max: int = 3) -> List[str]:
    """The distinct web links of text, in order, without the punctuation that ends the sentence (at most max)."""
    out: List[str] = []
    for m in _URL.finditer(str(text or "")):
        u = _trim(m.group(0))
        if u not in out:
            out.append(u)
        if len(out) >= max:
            break
    return out


def without_links(text: Optional[str]) -> str:
    """text without its web links (what a voice screen shows: the link is on the button)."""
    s = _URL.sub("", str(text or ""))
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\s+([.,;!?])", r"\1", s)
    s = re.sub(r":\s*$", "", s, flags=re.MULTILINE)
    return s.strip()


def link_parts(text: Optional[str]) -> List[LinkPart]:
    """text as parts: ``url`` only on the links (web, and e-mail as ``mailto:``)."""
    s = str(text or "")
    hits = []
    for m in _URL.finditer(s):
        u = _trim(m.group(0))
        hits.append((m.start(), m.start() + len(u), u))
    for m in _MAIL.finditer(s):
        start, end = m.start(), m.end()
        if any(start < h[1] and end > h[0] for h in hits):
            continue
        hits.append((start, end, "mailto:" + m.group(0)))
    hits.sort(key=lambda h: h[0])
    out: List[LinkPart] = []
    at = 0
    for start, end, url in hits:
        if start < at:
            continue
        if start > at:
            out.append(LinkPart(s[at:start], None))
        out.append(LinkPart(s[start:end], url))
        at = end
    if at < len(s):
        out.append(LinkPart(s[at:], None))
    return out


__all__ = ["LinkPart", "links_in", "without_links", "link_parts"]
