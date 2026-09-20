"""Parse and classify a Markdown document into Bloom artefacts.

The import format lets an uploaded Markdown file declare, per section, which
artefact type it becomes, plus a parameters section the backend uses to fill the
document. Classification is driven by a heading tag (``## [REQ] Title``), by
frontmatter (``type: requirement``), or by a default type chosen at import.
Parameters are ``parameter:``/``value:`` pairs; a name that already exists is a
collision that requires an action and is never silently overwritten.
"""

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

TYPE_TOKENS = {
    "req": "REQ",
    "requirement": "REQ",
    "spec": "SPEC",
    "specification": "SPEC",
    "std": "STD",
    "standard": "STD",
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

_HEADING_TAG_RE = re.compile(r"^\s*#{1,6}\s*\[(?P<tag>[A-Za-z-]+)\]\s*(?P<title>.*)$")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.*)$")
_PARAM_RE = re.compile(r"^\s*parameter\s*:\s*(?P<name>.+?)\s*$", re.IGNORECASE)
_VALUE_RE = re.compile(r"^\s*value\s*:\s*(?P<value>.*)$", re.IGNORECASE)


@dataclass
class Parameter:
    """A ``parameter:``/``value:`` pair declared in the document."""

    name: str
    value: str


@dataclass
class Section:
    """A classified section of the document."""

    type_code: Optional[str]
    title: str
    body: str


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


def parse_markdown_document(text: str, default_type: Optional[str] = None) -> ParsedMarkdown:
    """Parse a Markdown document into its doc type, parameters and classified sections."""
    lines = text.splitlines()
    frontmatter, body_lines = _parse_frontmatter(lines)
    doc_type = normalize_type(frontmatter.get("type")) or normalize_type(default_type)

    parameters = []
    sections = []
    current = None
    pending_param = None

    for line in body_lines:
        param_match = _PARAM_RE.match(line)
        if param_match:
            pending_param = param_match.group("name").strip()
            continue
        value_match = _VALUE_RE.match(line)
        if value_match and pending_param is not None:
            parameters.append(
                Parameter(name=pending_param, value=value_match.group("value").strip())
            )
            pending_param = None
            continue

        tag_match = _HEADING_TAG_RE.match(line)
        if tag_match:
            current = Section(
                type_code=normalize_type(tag_match.group("tag")) or doc_type,
                title=tag_match.group("title").strip(),
                body="",
            )
            sections.append(current)
            continue
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            current = Section(
                type_code=doc_type, title=heading_match.group("title").strip(), body=""
            )
            sections.append(current)
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
