"""
ReqIF import parser.

Parses OMG ReqIF (Requirements Interchange Format) 1.x exports into a normalized,
tool-agnostic structure that the import API maps onto Bloom requirements.

Design notes:
- Uses only the Python standard library (``xml.etree.ElementTree`` + ``zipfile``);
  no third-party dependency is added.
- Matching is *namespace-agnostic*: elements are compared by their local name so
  that files from DOORS, Polarion, Jama and PTC (which use slightly different
  namespace URIs and prefixes) all parse the same way.
- The parser is pure and side-effect free; persistence lives in the API layer.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

# Attribute long-names commonly used by tools for the requirement heading/title.
TITLE_ATTRIBUTE_HINTS = (
    "reqif.chaptername",
    "reqif.name",
    "object heading",
    "objectheading",
    "heading",
    "title",
    "name",
)

# Attribute long-names commonly used for the requirement body/statement.
TEXT_ATTRIBUTE_HINTS = (
    "reqif.text",
    "object text",
    "objecttext",
    "text",
    "statement",
    "description",
)

# Attribute long-names commonly carrying the originating tool's own id.
FOREIGN_ID_HINTS = (
    "reqif.foreignid",
    "foreign id",
    "foreignid",
    "puid",
    "absolute number",
)

_XHTML_KEEP_TAGS = {
    "div",
    "p",
    "br",
    "span",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "td",
    "th",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
    "pre",
    "code",
    "blockquote",
}


class ReqIFParseError(ValueError):
    """Raised when the supplied bytes are not a readable ReqIF document."""


@dataclass
class ReqIFObject:
    """A single SPEC-OBJECT (a requirement candidate)."""

    identifier: str
    long_name: Optional[str] = None
    # attribute long-name (lower-cased) -> plain-text value
    attributes: Dict[str, str] = field(default_factory=dict)
    # attribute long-name (lower-cased) -> html value (only for XHTML attributes)
    html_attributes: Dict[str, str] = field(default_factory=dict)

    def first_attr(self, hints: tuple) -> Optional[str]:
        """Return the first non-empty attribute value whose name matches a hint."""
        for hint in hints:
            for name, value in self.attributes.items():
                if name == hint and value and value.strip():
                    return value.strip()
        # fall back to a substring match (e.g. "reqif.text" inside a longer name)
        for hint in hints:
            for name, value in self.attributes.items():
                if hint in name and value and value.strip():
                    return value.strip()
        return None

    def first_html(self, hints: tuple) -> Optional[str]:
        for hint in hints:
            for name, value in self.html_attributes.items():
                if (hint == name or hint in name) and value and value.strip():
                    return value
        return None


@dataclass
class ReqIFHierarchyNode:
    object_ref: str
    children: List["ReqIFHierarchyNode"] = field(default_factory=list)


@dataclass
class ReqIFSpecification:
    identifier: str
    long_name: Optional[str]
    roots: List[ReqIFHierarchyNode] = field(default_factory=list)


@dataclass
class ReqIFRelation:
    identifier: str
    source_ref: str
    target_ref: str
    type_name: Optional[str] = None


@dataclass
class ReqIFBundle:
    objects: Dict[str, ReqIFObject] = field(default_factory=dict)
    specifications: List[ReqIFSpecification] = field(default_factory=list)
    relations: List[ReqIFRelation] = field(default_factory=list)

    def ordered_object_refs(self) -> List[tuple]:
        """
        Flatten every specification hierarchy into ``(object_ref, parent_ref)``
        pairs in document order, parents always before their children.

        Objects that are not referenced by any specification hierarchy are
        appended afterwards (parent ``None``) so nothing is silently dropped.
        """
        ordered: List[tuple] = []
        seen: set = set()

        def walk(node: ReqIFHierarchyNode, parent_ref: Optional[str]) -> None:
            if node.object_ref in self.objects and node.object_ref not in seen:
                ordered.append((node.object_ref, parent_ref))
                seen.add(node.object_ref)
                effective_parent = node.object_ref
            else:
                # keep descending even if this node's object is missing/duplicate
                effective_parent = parent_ref
            for child in node.children:
                walk(child, effective_parent)

        for spec in self.specifications:
            for root in spec.roots:
                walk(root, None)

        for identifier in self.objects:
            if identifier not in seen:
                ordered.append((identifier, None))
                seen.add(identifier)

        return ordered


def _local(tag: str) -> str:
    """Strip an XML namespace: ``{ns}SPEC-OBJECT`` -> ``spec-object`` (lower)."""
    if "}" in tag:
        tag = tag.rsplit("}", 1)[1]
    return tag.lower()


def _find_all(elem: ET.Element, local_name: str) -> List[ET.Element]:
    """All descendants (any depth) whose local name matches, namespace-agnostic."""
    target = local_name.lower()
    return [e for e in elem.iter() if _local(e.tag) == target]


def _first_child(elem: ET.Element, local_name: str) -> Optional[ET.Element]:
    target = local_name.lower()
    for child in elem:
        if _local(child.tag) == target:
            return child
    return None


def _xhtml_to_html(elem: ET.Element) -> str:
    """Render an XHTML THE-VALUE subtree to a compact HTML string.

    Keeps a safe subset of structural tags (stripping namespaces and attributes)
    so the requirement body survives round-tripping without importing markup we
    do not control.
    """
    parts: List[str] = []

    def render(node: ET.Element) -> None:
        tag = _local(node.tag)
        keep = tag in _XHTML_KEEP_TAGS
        if keep:
            parts.append(f"<{tag}>")
        if node.text:
            parts.append(_escape(node.text))
        for child in node:
            render(child)
            if child.tail:
                parts.append(_escape(child.tail))
        if keep:
            parts.append(f"</{tag}>")

    for child in elem:
        render(child)
        if child.tail:
            parts.append(_escape(child.tail))
    # some tools put text directly on THE-VALUE with no child elements
    if not list(elem) and elem.text:
        parts.append(_escape(elem.text))
    return "".join(parts).strip()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _plain_text(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def _extract_bytes(data: bytes) -> bytes:
    """Return raw ReqIF XML, unwrapping a ``.reqifz`` (zip) container if needed."""
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".reqif")]
                if not names:
                    names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
                if not names:
                    raise ReqIFParseError("Archive contains no .reqif file.")
                return zf.read(names[0])
        except zipfile.BadZipFile as exc:  # pragma: no cover - defensive
            raise ReqIFParseError("Corrupt .reqifz archive.") from exc
    return data


def parse_reqif(data: bytes) -> ReqIFBundle:
    """Parse ReqIF ``.reqif`` (XML) or ``.reqifz`` (zip) bytes into a bundle."""
    if not data:
        raise ReqIFParseError("Empty file.")

    xml_bytes = _extract_bytes(data)
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ReqIFParseError(f"Not valid XML: {exc}") from exc

    if _local(root.tag) != "req-if":
        # some exporters wrap or omit the outer element; tolerate as long as
        # ReqIF content is present somewhere in the tree
        if not _find_all(root, "SPEC-OBJECT"):
            raise ReqIFParseError("No ReqIF content (SPEC-OBJECT) found.")

    # 1. enum option identifier -> long-name (to resolve enumeration values)
    enum_option_name: Dict[str, str] = {}
    for opt in _find_all(root, "ENUM-VALUE"):
        ident = opt.get("IDENTIFIER")
        name = opt.get("LONG-NAME")
        if ident:
            enum_option_name[ident] = name or ident

    # 2. attribute-definition identifier -> long-name
    attr_def_name: Dict[str, str] = {}
    for adef in root.iter():
        if _local(adef.tag).startswith("attribute-definition-"):
            ident = adef.get("IDENTIFIER")
            if ident:
                attr_def_name[ident] = adef.get("LONG-NAME") or ident

    # 3. spec-relation-type identifier -> long-name (for link typing)
    rel_type_name: Dict[str, str] = {}
    for rtype in _find_all(root, "SPEC-RELATION-TYPE"):
        ident = rtype.get("IDENTIFIER")
        if ident:
            rel_type_name[ident] = rtype.get("LONG-NAME") or ident

    bundle = ReqIFBundle()

    # 4. spec objects + their attribute values
    for so in _find_all(root, "SPEC-OBJECT"):
        ident = so.get("IDENTIFIER")
        if not ident:
            continue
        obj = ReqIFObject(identifier=ident, long_name=so.get("LONG-NAME"))
        values = _first_child(so, "VALUES")
        for av in list(values) if values is not None else []:
            _consume_attribute_value(av, obj, attr_def_name, enum_option_name)
        bundle.objects[ident] = obj

    # 5. specifications + hierarchy (parent/child ordering)
    for spec in _find_all(root, "SPECIFICATION"):
        ident = spec.get("IDENTIFIER")
        if not ident:
            continue
        specification = ReqIFSpecification(identifier=ident, long_name=spec.get("LONG-NAME"))
        children = _first_child(spec, "CHILDREN")
        if children is not None:
            for hier in children:
                if _local(hier.tag) == "spec-hierarchy":
                    node = _build_hierarchy(hier)
                    if node is not None:
                        specification.roots.append(node)
        bundle.specifications.append(specification)

    # 6. spec relations (traceability links)
    for rel in _find_all(root, "SPEC-RELATION"):
        ident = rel.get("IDENTIFIER")
        source = _ref_text(rel, "SOURCE")
        target = _ref_text(rel, "TARGET")
        if not (ident and source and target):
            continue
        type_ident = _ref_text(rel, "TYPE")
        bundle.relations.append(
            ReqIFRelation(
                identifier=ident,
                source_ref=source,
                target_ref=target,
                type_name=rel_type_name.get(type_ident) if type_ident else None,
            )
        )

    return bundle


def _consume_attribute_value(
    av: ET.Element,
    obj: ReqIFObject,
    attr_def_name: Dict[str, str],
    enum_option_name: Dict[str, str],
) -> None:
    kind = _local(av.tag)
    if not kind.startswith("attribute-value-"):
        return

    # resolve which attribute definition this value belongs to
    definition = _first_child(av, "DEFINITION")
    def_name: Optional[str] = None
    if definition is not None:
        for ref in definition:
            def_name = attr_def_name.get((ref.text or "").strip())
            if def_name:
                break
    if not def_name:
        return
    key = def_name.lower()

    if kind == "attribute-value-xhtml":
        the_value = _first_child(av, "THE-VALUE")
        if the_value is not None:
            obj.html_attributes[key] = _xhtml_to_html(the_value)
            obj.attributes[key] = _plain_text(the_value)
    elif kind == "attribute-value-enumeration":
        refs = _find_all(av, "ENUM-VALUE-REF")
        names = [enum_option_name.get((r.text or "").strip()) for r in refs]
        obj.attributes[key] = ", ".join(n for n in names if n)
    else:
        # string / integer / real / date / boolean carry THE-VALUE as an attribute
        value = av.get("THE-VALUE")
        if value is None:
            the_value = _first_child(av, "THE-VALUE")
            value = _plain_text(the_value) if the_value is not None else None
        if value is not None:
            obj.attributes[key] = value


def _build_hierarchy(hier: ET.Element) -> Optional[ReqIFHierarchyNode]:
    object_ref = _ref_text(hier, "OBJECT")
    node = ReqIFHierarchyNode(object_ref=object_ref or "")
    children = _first_child(hier, "CHILDREN")
    if children is not None:
        for child in children:
            if _local(child.tag) == "spec-hierarchy":
                built = _build_hierarchy(child)
                if built is not None:
                    node.children.append(built)
    if not node.object_ref and not node.children:
        return None
    return node


def _ref_text(parent: ET.Element, wrapper_local: str) -> Optional[str]:
    """Return the *-REF text inside a wrapper such as SOURCE/TARGET/TYPE/OBJECT."""
    wrapper = _first_child(parent, wrapper_local)
    if wrapper is None:
        return None
    for ref in wrapper:
        if _local(ref.tag).endswith("-ref") and ref.text:
            return ref.text.strip()
    # some tools place the ref text directly on the wrapper
    return wrapper.text.strip() if wrapper.text and wrapper.text.strip() else None
