"""Turn imported Markdown into the rich content the web editor stores.

The result is the editor's TipTap JSON (``content_json``) and the HTML the editor saves
beside it (``content_html``). Headings, paragraphs, bold, italic, strikethrough, inline
code, code blocks, links, bullet and numbered lists, block quotes, horizontal rules and
tables are kept. A ``{{NAME}}`` reference becomes the editor's parameter mention node.
A ``[[Title]]`` reference becomes the editor's artefact mention node when the caller
resolves it to an artefact; otherwise it stays text.
"""

import re
from html import escape
from typing import Any, Mapping, Optional

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.services.tag_links import TAG_TRIGGER

PARAMETER_TRIGGER = "{{"
SECTION_REFERENCE_RE = re.compile(r"\[\[([^\[\]\n]+)\]\]")
_TOKEN_RE = re.compile(r"\{\{(?P<parameter>[^{}]*)\}\}|\[\[(?P<title>[^\[\]\n]+)\]\]")
_SLOT_OPEN = "\ue000"
_SLOT_CLOSE = "\ue001"
_SLOT_RE = re.compile(_SLOT_OPEN + r"(\d+)" + _SLOT_CLOSE)
_ALIGN_RE = re.compile(r"text-align:\s*(left|center|right)")
_LINK_DEFAULTS = {"target": "_blank", "rel": "noopener noreferrer nofollow"}
_MARK_OPENERS = {"strong_open": "bold", "em_open": "italic", "s_open": "strike"}
_MARK_CLOSERS = {"strong_close": "bold", "em_close": "italic", "s_close": "strike"}
_CONTAINERS = {
    "paragraph_open": "paragraph",
    "bullet_list_open": "bulletList",
    "ordered_list_open": "orderedList",
    "list_item_open": "listItem",
    "blockquote_open": "blockquote",
    "table_open": "table",
    "tr_open": "tableRow",
    "th_open": "tableHeader",
    "td_open": "tableCell",
}
_SKIPPED_CLOSERS = {"thead_close", "tbody_close"}
_NEEDS_PARAGRAPH = {"listItem", "blockquote", "tableHeader", "tableCell"}
_CELLS = {"tableHeader", "tableCell"}
_MARK_TAGS = {"bold": "strong", "italic": "em", "strike": "s", "code": "code"}
_BLOCK_TAGS = {
    "paragraph": "p",
    "bulletList": "ul",
    "listItem": "li",
    "blockquote": "blockquote",
    "tableRow": "tr",
}


def _parser() -> MarkdownIt:
    """A CommonMark parser with tables and strikethrough and without raw HTML."""
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


def reference_name(raw: str) -> Optional[str]:
    """The parameter name a ``{{...}}`` holds, or None when it is not a plain name."""
    name = raw.strip()
    if not name or any(char in name for char in (":", ",", "\n")):
        return None
    return name


def section_key(title: str) -> str:
    """The form a section title is matched in: spacing collapsed, case folded."""
    return " ".join(title.split()).casefold()


def artefact_mention(type_code: str, row_id: int, public_id: str) -> dict:
    """The editor's artefact mention node, as written when a user picks an artefact after ``#``."""
    return {
        "type": "mention",
        "attrs": {
            "id": f"{type_code}:{row_id}",
            "label": public_id,
            "mentionSuggestionChar": TAG_TRIGGER,
        },
    }


def _mention(name: str, parameters: Mapping[str, tuple]) -> dict:
    """The editor's parameter mention node for a name, pointing at the project row when known."""
    row_id, key = parameters.get(name.lower(), (name, name))
    return {
        "type": "mention",
        "attrs": {"id": str(row_id), "label": key, "mentionSuggestionChar": PARAMETER_TRIGGER},
    }


def _with_marks(node: dict, marks: list) -> dict:
    """The node carrying a copy of the marks, when there are any."""
    if marks:
        node["marks"] = [dict(mark) for mark in marks]
    return node


def _append_text(nodes: list, text: str, marks: list) -> None:
    """Add a text node, merged into the previous one when both carry the same marks."""
    if not text:
        return
    previous = nodes[-1] if nodes else None
    if (
        previous is not None
        and previous.get("type") == "text"
        and previous.get("marks", []) == marks
    ):
        previous["text"] += text
        return
    nodes.append(_with_marks({"type": "text", "text": text}, marks))


def _child(parent: dict, node: dict) -> dict:
    """Append a node to the parent's content and return it."""
    parent.setdefault("content", []).append(node)
    return node


def _container(token: Token) -> dict:
    """The editor node a container token opens."""
    node_type = _CONTAINERS[token.type]
    node: dict = {"type": node_type}
    if node_type == "orderedList":
        node["attrs"] = {"start": int(token.attrs.get("start") or 1)}
    elif node_type in _CELLS:
        node["attrs"] = {"colspan": 1, "rowspan": 1, "colwidth": None}
        align = _ALIGN_RE.search(str(token.attrs.get("style") or ""))
        if align:
            node["align"] = align.group(1)
    return node


def _finish(node: dict) -> None:
    """Give a closed node the content the editor requires and drop working fields."""
    node.pop("align", None)
    if node["type"] not in _NEEDS_PARAGRAPH:
        return
    content = node.setdefault("content", [])
    if not content or (node["type"] == "listItem" and content[0]["type"] != "paragraph"):
        content.insert(0, {"type": "paragraph"})


def _close_mark(marks: list, mark_type: str) -> None:
    """Remove the innermost open mark of the type."""
    for index in range(len(marks) - 1, -1, -1):
        if marks[index]["type"] == mark_type:
            del marks[index]
            return


class _Converter:
    """Converts one Markdown text, holding the mention nodes of the references it set aside."""

    def __init__(self, parameters: Mapping[str, tuple], artefacts: Mapping[str, tuple]) -> None:
        self.parameters = parameters
        self.artefacts = artefacts
        self.references: list = []

    def _node(self, match: re.Match) -> Optional[dict]:
        """The mention node a reference stands for, or None when it stays text."""
        if match.group("parameter") is not None:
            name = reference_name(match.group("parameter"))
            return _mention(name, self.parameters) if name else None
        target = self.artefacts.get(section_key(match.group("title")))
        return artefact_mention(*target) if target else None

    def protect(self, text: str) -> str:
        """Replace each reference that becomes a mention by a slot the Markdown parser
        leaves untouched."""

        def _slot(match: re.Match) -> str:
            node = self._node(match)
            if node is None:
                return match.group(0)
            self.references.append((match.group(0), node))
            return f"{_SLOT_OPEN}{len(self.references) - 1}{_SLOT_CLOSE}"

        return _TOKEN_RE.sub(_slot, text)

    def _original(self, match: re.Match) -> str:
        """The reference text a slot stands for, or the slot itself when unknown."""
        index = int(match.group(1))
        return self.references[index][0] if index < len(self.references) else match.group(0)

    def restore(self, text: str) -> str:
        """Put the original reference text back in place of each slot."""
        return _SLOT_RE.sub(self._original, text)

    def text_nodes(self, nodes: list, text: str, marks: list) -> None:
        """Add text, turning each reference slot into its mention."""
        position = 0
        for match in _SLOT_RE.finditer(text):
            index = int(match.group(1))
            if index >= len(self.references):
                continue
            _append_text(nodes, text[position : match.start()], marks)
            node = dict(self.references[index][1], attrs=dict(self.references[index][1]["attrs"]))
            nodes.append(_with_marks(node, marks))
            position = match.end()
        _append_text(nodes, text[position:], marks)

    def _image(self, nodes: list, token: Token, marks: list) -> None:
        """An inline image kept as its alternative text linked to its source."""
        src = str(token.attrs.get("src") or "")
        linked = [mark for mark in marks if mark["type"] != "link"]
        if src:
            linked.append({"type": "link", "attrs": {"href": src, **_LINK_DEFAULTS}})
        self.text_nodes(nodes, token.content or src, linked)

    def inline(self, children: list) -> list:
        """The editor's inline nodes for the children of one inline token."""
        nodes: list = []
        marks: list = []
        for token in children:
            kind = token.type
            if kind in ("text", "text_special", "html_inline"):
                self.text_nodes(nodes, token.content, marks)
            elif kind == "softbreak":
                _append_text(nodes, " ", marks)
            elif kind == "hardbreak":
                nodes.append({"type": "hardBreak"})
            elif kind == "code_inline":
                _append_text(nodes, self.restore(token.content), [{"type": "code"}])
            elif kind in _MARK_OPENERS:
                marks.append({"type": _MARK_OPENERS[kind]})
            elif kind == "link_open":
                href = str(token.attrs.get("href") or "")
                marks.append({"type": "link", "attrs": {"href": href, **_LINK_DEFAULTS}})
            elif kind in _MARK_CLOSERS or kind == "link_close":
                _close_mark(marks, _MARK_CLOSERS.get(kind, "link"))
            elif kind == "image":
                self._image(nodes, token, marks)
        return nodes

    def _inline_into(self, parent: dict, token: Token) -> None:
        """Add the inline content of a token to its block, inside a paragraph in a table cell."""
        content = self.inline(token.children or [])
        if parent["type"] in _CELLS:
            paragraph: dict = {"type": "paragraph"}
            if parent.get("align"):
                paragraph["attrs"] = {"textAlign": parent["align"]}
            parent = _child(parent, paragraph)
        if content:
            parent.setdefault("content", []).extend(content)

    def _code_block(self, token: Token) -> dict:
        """A code block with its language and its text, references kept as written."""
        language = (token.info or "").strip().split(" ")[0] or None
        node: dict = {"type": "codeBlock", "attrs": {"language": language}}
        text = self.restore(token.content).rstrip("\n")
        if text:
            node["content"] = [{"type": "text", "text": text}]
        return node

    def blocks(self, tokens: list) -> list:
        """The editor's block nodes for a Markdown token stream."""
        root: dict = {"type": "doc", "content": []}
        stack = [root]
        for token in tokens:
            kind = token.type
            parent = stack[-1]
            if kind == "inline":
                self._inline_into(parent, token)
            elif kind == "heading_open":
                heading = {"type": "heading", "attrs": {"level": int(token.tag[1])}}
                stack.append(_child(parent, heading))
            elif kind in _CONTAINERS:
                stack.append(_child(parent, _container(token)))
            elif kind.endswith("_close") and kind not in _SKIPPED_CLOSERS:
                _finish(stack.pop())
            elif kind in ("fence", "code_block"):
                _child(parent, self._code_block(token))
            elif kind == "hr":
                _child(parent, {"type": "horizontalRule"})
        return root["content"]


def markdown_content(
    text: Optional[str],
    parameters: Optional[Mapping[str, tuple]] = None,
    artefacts: Optional[Mapping[str, tuple]] = None,
) -> Optional[dict]:
    """The editor document for Markdown text, or None when the text holds nothing.

    ``parameters`` maps a lower-case parameter name to its project row id and its key;
    a ``{{NAME}}`` the map does not hold becomes a mention whose id and label are NAME.
    ``artefacts`` maps ``section_key(title)`` to the type code, row id and document ID
    of an artefact; a ``[[Title]]`` the map does not hold stays text.
    """
    if not text or not text.strip():
        return None
    converter = _Converter(parameters or {}, artefacts or {})
    content = converter.blocks(_parser().parse(converter.protect(text)))
    if not content:
        return None
    return {"type": "doc", "content": content}


def _attributes(values: Mapping[str, Any]) -> str:
    """HTML attributes for the values that are set."""
    return "".join(
        f' {name}="{escape(str(value), quote=True)}"'
        for name, value in values.items()
        if value is not None
    )


def _wrap_marks(html: str, marks: list) -> str:
    """The HTML wrapped in the tags of its marks."""
    for mark in reversed(marks or []):
        mark_type = mark.get("type")
        if mark_type == "link":
            html = f"<a{_attributes(mark.get('attrs') or {})}>{html}</a>"
        elif mark_type in _MARK_TAGS:
            tag = _MARK_TAGS[mark_type]
            html = f"<{tag}>{html}</{tag}>"
    return html


def _html_mention(node: dict) -> str:
    """The HTML the editor writes for a parameter or artefact mention."""
    attrs = node.get("attrs") or {}
    label = str(attrs.get("label") or attrs.get("id") or "")
    artefact = attrs.get("mentionSuggestionChar") == TAG_TRIGGER
    span_attrs = {
        "data-type": "mention",
        "data-id": attrs.get("id"),
        "data-label": attrs.get("label"),
        "data-mention-suggestion-char": attrs.get("mentionSuggestionChar"),
        "class": "mention-artefact" if artefact else "mention",
    }
    text = escape(label if artefact else "{{" + label + "}}", quote=False)
    return _wrap_marks(f"<span{_attributes(span_attrs)}>{text}</span>", node.get("marks"))


def _align(attrs: Mapping[str, Any]) -> str:
    """The style attribute for a paragraph or heading alignment."""
    align = attrs.get("textAlign")
    return f' style="text-align: {escape(str(align), quote=True)}"' if align else ""


def _html_block(node_type: str, attrs: Mapping[str, Any], inner: str) -> str:
    """The HTML of a block node around its rendered content."""
    if node_type == "heading":
        level = int(attrs.get("level") or 1)
        return f"<h{level}{_align(attrs)}>{inner}</h{level}>"
    if node_type == "paragraph":
        return f"<p{_align(attrs)}>{inner}</p>"
    if node_type == "orderedList":
        start = int(attrs.get("start") or 1)
        return f"<ol{_attributes({'start': start if start != 1 else None})}>{inner}</ol>"
    if node_type == "codeBlock":
        language = attrs.get("language")
        css = _attributes({"class": f"language-{language}" if language else None})
        return f"<pre><code{css}>{inner}</code></pre>"
    if node_type == "table":
        return f"<table><tbody>{inner}</tbody></table>"
    if node_type in _CELLS:
        tag = "th" if node_type == "tableHeader" else "td"
        return f'<{tag} colspan="1" rowspan="1">{inner}</{tag}>'
    if node_type in _BLOCK_TAGS:
        tag = _BLOCK_TAGS[node_type]
        return f"<{tag}>{inner}</{tag}>"
    return inner


def _html_node(node: dict) -> str:
    """The HTML of one editor node and its content."""
    node_type = node.get("type")
    if node_type == "text":
        return _wrap_marks(escape(str(node.get("text") or ""), quote=False), node.get("marks"))
    if node_type == "mention":
        return _html_mention(node)
    if node_type == "hardBreak":
        return "<br>"
    if node_type == "horizontalRule":
        return "<hr>"
    inner = "".join(_html_node(child) for child in node.get("content") or [])
    return _html_block(str(node_type), node.get("attrs") or {}, inner)


def content_html(content: Optional[dict]) -> Optional[str]:
    """The HTML of an editor document, as the editor saves it beside its JSON."""
    if not content:
        return None
    return _html_node(content)
