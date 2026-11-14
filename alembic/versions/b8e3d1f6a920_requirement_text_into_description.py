"""requirements: move editor content into the description

Revision ID: b8e3d1f6a920
Revises: a7d2c5f81b39
Create Date: 2026-11-13

A requirement is a title and a plain description. The plain text of each requirement's editor
content is added to its description, mentions written as @Name, #ID and {{KEY}}, and the editor
content is cleared. The downgrade leaves the descriptions as they are.
"""

import html
import json
import re

import sqlalchemy as sa

from alembic import op

revision = "b8e3d1f6a920"
down_revision = "a7d2c5f81b39"
branch_labels = None
depends_on = None

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
HTML_BREAKS = re.compile(r"<\s*(br|/p|/h[1-6]|/li|/tr|/blockquote|/pre)\s*/?\s*>", re.IGNORECASE)
HTML_TAGS = re.compile(r"<[^>]+>")
BLANK_LINES = re.compile(r"\n{3,}")


def _node_text(node):
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
        if trigger in ("@", "#"):
            return f"{trigger}{label}"
        return "{{" + label + "}}"
    inner = "".join(_node_text(child) for child in node.get("content") or [])
    if kind in BLOCK_TYPES:
        return inner.strip("\n") + "\n"
    return inner


def _plain_text(content_json, content_html):
    """The plain text of editor content, from its JSON when present, else from its HTML."""
    if isinstance(content_json, str):
        content_json = json.loads(content_json)
    if isinstance(content_json, dict):
        text = _node_text(content_json)
    elif content_html:
        text = html.unescape(HTML_TAGS.sub("", HTML_BREAKS.sub("\n", content_html)))
    else:
        text = ""
    return BLANK_LINES.sub("\n\n", text).strip()


def upgrade() -> None:
    """Add each requirement's editor text to its description and clear the editor content."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, description, content_json, content_html FROM requirements "
            "WHERE content_json IS NOT NULL OR content_html IS NOT NULL"
        )
    ).all()
    for row_id, description, content_json, content_html in rows:
        text = _plain_text(content_json, content_html)
        current = (description or "").strip()
        if text and text not in current:
            description = f"{current}\n\n{text}" if current else text
        bind.execute(
            sa.text(
                "UPDATE requirements SET description = :description, content_json = NULL, "
                "content_html = NULL WHERE id = :id"
            ),
            {"description": description, "id": row_id},
        )


def downgrade() -> None:
    """Keep the descriptions; the editor content is not restored."""
