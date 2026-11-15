"""Plain text of editor content, as a requirement description holds it."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

BLOCK_TYPES = frozenset(
    {
        "paragraph",
        "heading",
        "blockquote",
        "codeBlock",
        "listItem",
        "taskItem",
        "tableRow",
        "horizontalRule",
    }
)
MENTION_PREFIXES = {"@": "@", "#": "#"}
LINE_END_TAGS = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "blockquote", "pre"}
)
BLANK_LINES = re.compile(r"\n{3,}")


class _HtmlText(HTMLParser):
    """Collects the text of HTML with a line break after each block and at each br."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Add a line break at a br."""
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Add a line break after a block."""
        if tag in LINE_END_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Keep the text."""
        self.parts.append(data)


def _html_text(content_html: str) -> str:
    """The text of HTML with a line break after each block and at each br."""
    parser = _HtmlText()
    parser.feed(content_html)
    parser.close()
    return "".join(parser.parts)


def _node_text(node: Any) -> str:
    """The text of one editor node, mentions written as @Name, #ID and {{KEY}}."""
    if not isinstance(node, dict):
        return ""
    kind = node.get("type")
    if kind == "text":
        return str(node.get("text") or "")
    if kind == "hardBreak":
        return "\n"
    if kind == "mention":
        attrs = node.get("attrs") or {}
        label = str(attrs.get("label") or attrs.get("id") or "")
        trigger = attrs.get("mentionSuggestionChar")
        if trigger in MENTION_PREFIXES:
            return f"{MENTION_PREFIXES[trigger]}{label}"
        return "{{" + label + "}}"
    inner = "".join(_node_text(child) for child in node.get("content") or [])
    if kind in BLOCK_TYPES:
        return inner.strip("\n") + "\n"
    return inner


def plain_text(content_json: Any, content_html: str | None) -> str:
    """The plain text of editor content, from its JSON when present, else from its HTML."""
    if isinstance(content_json, dict):
        text = _node_text(content_json)
    elif content_html:
        text = _html_text(content_html)
    else:
        text = ""
    return BLANK_LINES.sub("\n\n", text).strip()


def description_with_content(
    description: str | None, content_json: Any, content_html: str | None
) -> str | None:
    """The description followed by the plain text of the editor content it does not hold."""
    text = plain_text(content_json, content_html)
    current = (description or "").strip()
    if not text or text in current:
        return description
    if not current:
        return text
    return f"{current}\n\n{text}"
