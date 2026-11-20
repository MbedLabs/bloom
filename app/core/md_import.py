"""Parse and classify a Markdown document into Bloom artefacts.

The import format lets an uploaded Markdown file declare, per section, which
artefact type it becomes. Classification is driven by a heading tag
(``## [REQ] Title``), by frontmatter (``type: requirement``), or by a default type
chosen at import. A parameter is written inside a sentence as
``{{parameter: NAME, value: VALUE}}`` and a variable as
``{{variable: NAME, value: VALUE}}``; the backend recognises either wherever it appears,
records it with its kind, and replaces it in place with ``{{NAME}}``. A name the
project holds is a collision that requires an action and is never silently overwritten.
Inside a section opened by a type tag, a deeper heading without a tag stays in the
section body, and lines inside a fenced code block are body text.
"""

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from app.core.tc_steps import continue_row, parse_row

TYPE_TOKENS = {
    "req": "REQ",
    "requirement": "REQ",
    "spec": "SPEC",
    "specification": "SPEC",
    "std": "STD",
    "standard": "STD",
    "vis": "VIS",
    "vision": "VIS",
    "des": "DES",
    "design": "DES",
    "rsk": "RSK",
    "risk": "RSK",
    "chg": "CHG",
    "change": "CHG",
    "change-request": "CHG",
    "cpt": "CPT",
    "concept": "CPT",
    "test-concept": "CPT",
    "tc": "TC",
    "test-case": "TC",
    "def": "DEF",
    "defect": "DEF",
}

_HEADING_TAG_RE = re.compile(r"^\s*(?P<hashes>#{1,6})\s*\[(?P<tag>[A-Za-z-]+)\](?P<title>.*)$")
_HEADING_RE = re.compile(r"^\s*(?P<hashes>#{1,6})\s(?P<title>.*)$")
_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
_PARAM_RE = re.compile(
    r"\{\{\s*(?P<kind>parameter|variable)\s*:(?P<name>[^{},]+),"
    r"\s*value\s*:(?P<value>[^{}]*)\}\}",
    re.IGNORECASE,
)


@dataclass
class Parameter:
    """A ``{{parameter: NAME, value: VALUE}}`` or ``{{variable: NAME, value: VALUE}}``
    written in the document; ``kind`` is ``parameter`` or ``variable``."""

    name: str
    value: str
    kind: str = "parameter"


@dataclass
class Section:
    """A classified section of the document; a test case also carries step rows."""

    type_code: Optional[str]
    title: str
    body: str
    steps: list = field(default_factory=list)


@dataclass
class ParsedMarkdown:
    """The result of parsing a Markdown import document."""

    doc_type: Optional[str]
    parameters: list = field(default_factory=list)
    sections: list = field(default_factory=list)


def normalize_type(token: Optional[str]) -> Optional[str]:
    """Map a type token (tag or frontmatter) to a canonical artefact type code."""
    if not token:
        return None
    return TYPE_TOKENS.get(token.strip().lower())


def _parse_frontmatter(lines: list) -> tuple:
    """Split a leading ``---`` frontmatter block from the body lines."""
    if not lines or lines[0].strip() != "---":
        return {}, lines
    frontmatter = {}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return frontmatter, lines[index + 1 :]
        if ":" in lines[index]:
            key, _, value = lines[index].partition(":")
            frontmatter[key.strip().lower()] = value.strip()
    return {}, lines


def _replace_parameters(line: str, parameters: list) -> str:
    """Record each wrapped parameter in the line and replace it with ``{{NAME}}``."""

    def _placeholder(match: re.Match) -> str:
        name = match.group("name").strip()
        parameters.append(
            Parameter(
                name=name,
                value=match.group("value").strip(),
                kind=match.group("kind").lower(),
            )
        )
        return "{{" + name + "}}"

    return _PARAM_RE.sub(_placeholder, line)


def _fence_state(line: str, fence: Optional[str]) -> tuple:
    """Whether the line belongs to a fenced code block, and the fence open after it."""
    if fence is None:
        match = _FENCE_RE.match(line)
        return (True, match.group("fence")) if match else (False, None)
    marker = line.strip()
    closes = len(marker) >= len(fence) and set(marker) == {fence[0]}
    return True, None if closes else fence


def parse_markdown_document(text: str, default_type: Optional[str] = None) -> ParsedMarkdown:
    """Parse a Markdown document into its doc type, parameters and classified sections."""
    lines = text.splitlines()
    frontmatter, body_lines = _parse_frontmatter(lines)
    doc_type = normalize_type(frontmatter.get("type")) or normalize_type(default_type)

    parameters = []
    sections = []
    current = None
    tagged_level = 0
    fence = None

    for raw_line in body_lines:
        line = _replace_parameters(raw_line, parameters)
        in_fence, fence = _fence_state(line, fence)
        if in_fence:
            if current is not None:
                current.body += line + "\n"
            continue
        tag_match = _HEADING_TAG_RE.match(line)
        if tag_match:
            current = Section(
                type_code=normalize_type(tag_match.group("tag")) or doc_type,
                title=tag_match.group("title").strip(),
                body="",
            )
            sections.append(current)
            tagged_level = len(tag_match.group("hashes"))
            continue
        heading_match = _HEADING_RE.match(line)
        if heading_match and not (
            current is not None and 0 < tagged_level < len(heading_match.group("hashes"))
        ):
            current = Section(
                type_code=doc_type, title=heading_match.group("title").strip(), body=""
            )
            sections.append(current)
            tagged_level = 0
            continue
        if current is not None and current.type_code == "TC":
            row = parse_row(line, len(current.steps))
            if row is not None:
                current.steps.append(row)
                continue
            if current.steps and line[:1] in (" ", "\t") and line.strip():
                continue_row(current.steps[-1], line)
                continue
        if current is not None:
            current.body += line + "\n"

    for section in sections:
        section.body = section.body.strip()
    return ParsedMarkdown(doc_type=doc_type, parameters=parameters, sections=sections)


def parameter_name_collisions(parameters: list, existing_names: Iterable) -> list:
    """Return parameter names that already exist; these require an action, never overwrite."""
    existing = {name.strip().lower() for name in existing_names}
    seen = set()
    collisions = []
    for parameter in parameters:
        key = parameter.name.strip().lower()
        if key in existing and key not in seen:
            collisions.append(parameter.name)
            seen.add(key)
    return collisions


_BARE_PARAM_RE = re.compile(r"\{\{([^{}]*)\}\}")


def rename_parameters(text: str, renames: dict) -> str:
    """Give parameters new names, in their wrapped form and in every ``{{NAME}}``
    reference; names are matched without regard to case."""
    lookup = {old.strip().lower(): new.strip() for old, new in renames.items()}

    def _wrapped(match: re.Match) -> str:
        new = lookup.get(match.group("name").strip().lower())
        if not new:
            return match.group(0)
        kind = match.group("kind").lower()
        return "{{" + kind + ": " + new + ", value: " + match.group("value").strip() + "}}"

    def _bare(match: re.Match) -> str:
        raw = match.group(1)
        name = raw.strip()
        if not raw.replace("\n", "") or any(char in name for char in (":", ",", "\n")):
            return match.group(0)
        new = lookup.get(name.lower())
        return "{{" + new + "}}" if new else match.group(0)

    return _BARE_PARAM_RE.sub(_bare, _PARAM_RE.sub(_wrapped, text))
