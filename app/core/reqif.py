"""ReqIF import parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as SafeET

from app.core.config import settings
from app.core.reqif_policy import ReqIFParseError, extract_reqif_xml

TITLE_ATTRIBUTE_HINTS = (
    "reqif.chaptername",
    "reqif.name",
    "object heading",
    "objectheading",
    "heading",
    "title",
    "name",
)

TEXT_ATTRIBUTE_HINTS = (
    "reqif.text",
    "object text",
    "objecttext",
    "text",
    "statement",
    "description",
)

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


@dataclass
class ReqIFObject:
    """A single SPEC-OBJECT (a requirement candidate).

    attributes maps lower-cased attribute long-names to plain text; html_attributes holds the HTML
    of XHTML values.
    """

    identifier: str
    long_name: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    html_attributes: Dict[str, str] = field(default_factory=dict)

    def first_attr(self, hints: tuple) -> Optional[str]:
        """Return the first non-empty attribute value whose name matches a hint.

        Exact names are tried first, then a substring match.
        """
        for hint in hints:
            for name, value in self.attributes.items():
                if name == hint and value and value.strip():
                    return value.strip()
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

    def ordered_object_refs(self) -> List[str]:
        """Every object reference once, in specification document order, then the objects
        no specification lists.
        """
        ordered: List[str] = []
        seen: set = set()

        def walk(node: ReqIFHierarchyNode) -> None:
            if node.object_ref in self.objects and node.object_ref not in seen:
                ordered.append(node.object_ref)
                seen.add(node.object_ref)
            for child in node.children:
                walk(child)

        for spec in self.specifications:
            for root in spec.roots:
                walk(root)

        for identifier in self.objects:
            if identifier not in seen:
                ordered.append(identifier)
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


def _render_xhtml(node: ET.Element, parts: List[str]) -> None:
    """Append one XHTML node to parts: kept tags around its text, children and their tails."""
    tag = _local(node.tag)
    keep = tag in _XHTML_KEEP_TAGS
    if keep:
        parts.append(f"<{tag}>")
    if node.text:
        parts.append(_escape(node.text))
    for child in node:
        _render_xhtml(child, parts)
        if child.tail:
            parts.append(_escape(child.tail))
    if keep:
        parts.append(f"</{tag}>")


def _xhtml_to_html(elem: ET.Element) -> str:
    """Render an XHTML THE-VALUE subtree to a compact HTML string.

    Text placed directly on THE-VALUE is kept.
    """
    parts: List[str] = []
    for child in elem:
        _render_xhtml(child, parts)
        if child.tail:
            parts.append(_escape(child.tail))
    if not list(elem) and elem.text:
        parts.append(_escape(elem.text))
    return "".join(parts).strip()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _plain_text(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def _extract_bytes(data: bytes) -> bytes:
    """Return raw ReqIF XML, unwrapping a ``.reqifz`` (zip) container if needed."""
    return extract_reqif_xml(data)


def parse_reqif(data: bytes) -> ReqIFBundle:
    """Parse ReqIF ``.reqif`` (XML) or ``.reqifz`` (zip) bytes into a bundle.

    A document whose outer element is wrapped or missing is accepted when it holds SPEC-OBJECT
    content.
    """
    if not data:
        raise ReqIFParseError("Empty file.")

    xml_bytes = _extract_bytes(data)
    try:
        root = SafeET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ReqIFParseError(f"Not valid XML: {exc}") from exc

    if _local(root.tag) != "req-if" and not _find_all(root, "SPEC-OBJECT"):
        raise ReqIFParseError("No ReqIF content (SPEC-OBJECT) found.")

    enum_option_name = _enum_option_names(root)
    attr_def_name = _attribute_definition_names(root)
    rel_type_name = _relation_type_names(root)

    bundle = ReqIFBundle()
    _read_objects(root, bundle, attr_def_name, enum_option_name)
    _read_specifications(root, bundle)
    _read_relations(root, bundle, rel_type_name)
    return bundle


def _enum_option_names(root: ET.Element) -> Dict[str, str]:
    """Each enumeration option's name by its identifier, the identifier when it has no name."""
    enum_option_name: Dict[str, str] = {}
    for opt in _find_all(root, "ENUM-VALUE"):
        ident = opt.get("IDENTIFIER")
        name = opt.get("LONG-NAME")
        if ident:
            enum_option_name[ident] = name or ident
    return enum_option_name


def _attribute_definition_names(root: ET.Element) -> Dict[str, str]:
    """Each attribute definition's name by its identifier, the identifier when it has no name."""
    attr_def_name: Dict[str, str] = {}
    for adef in root.iter():
        if _local(adef.tag).startswith("attribute-definition-"):
            ident = adef.get("IDENTIFIER")
            if ident:
                attr_def_name[ident] = adef.get("LONG-NAME") or ident
    return attr_def_name


def _relation_type_names(root: ET.Element) -> Dict[str, str]:
    """Each relation type's name by its identifier, the identifier when it has no name."""
    rel_type_name: Dict[str, str] = {}
    for rtype in _find_all(root, "SPEC-RELATION-TYPE"):
        ident = rtype.get("IDENTIFIER")
        if ident:
            rel_type_name[ident] = rtype.get("LONG-NAME") or ident
    return rel_type_name


def _read_objects(
    root: ET.Element,
    bundle: ReqIFBundle,
    attr_def_name: Dict[str, str],
    enum_option_name: Dict[str, str],
) -> None:
    """Add every identified spec object with its attribute values, within the object limit."""
    spec_objects = _find_all(root, "SPEC-OBJECT")
    if len(spec_objects) > settings.REQIF_MAX_OBJECTS:
        raise ReqIFParseError(
            f"ReqIF object limit exceeded (maximum {settings.REQIF_MAX_OBJECTS})."
        )
    for so in spec_objects:
        ident = so.get("IDENTIFIER")
        if not ident:
            continue
        obj = ReqIFObject(identifier=ident, long_name=so.get("LONG-NAME"))
        values = _first_child(so, "VALUES")
        for av in list(values) if values is not None else []:
            _consume_attribute_value(av, obj, attr_def_name, enum_option_name)
        bundle.objects[ident] = obj


def _read_specifications(root: ET.Element, bundle: ReqIFBundle) -> None:
    """Add every identified specification with its hierarchy roots."""
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


def _read_relations(root: ET.Element, bundle: ReqIFBundle, rel_type_name: Dict[str, str]) -> None:
    """Add every relation with an identifier, source and target, within the relation limit."""
    spec_relations = _find_all(root, "SPEC-RELATION")
    if len(spec_relations) > settings.REQIF_MAX_RELATIONS:
        raise ReqIFParseError(
            f"ReqIF relation limit exceeded (maximum {settings.REQIF_MAX_RELATIONS})."
        )
    for rel in spec_relations:
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


def _consume_attribute_value(
    av: ET.Element,
    obj: ReqIFObject,
    attr_def_name: Dict[str, str],
    enum_option_name: Dict[str, str],
) -> None:
    """Record one attribute value on a spec object under its definition's lower-cased long-name: XHTML
    as HTML and plain text, enumerations as option names, other kinds from THE-VALUE.
    """
    kind = _local(av.tag)
    if not kind.startswith("attribute-value-"):
        return

    def_name = _definition_name(av, attr_def_name)
    if not def_name:
        return
    key = def_name.lower()

    if kind == "attribute-value-xhtml":
        _record_xhtml(av, obj, key)
    elif kind == "attribute-value-enumeration":
        refs = _find_all(av, "ENUM-VALUE-REF")
        names = [enum_option_name.get((r.text or "").strip()) for r in refs]
        obj.attributes[key] = ", ".join(n for n in names if n)
    else:
        value = _plain_value(av)
        if value is not None:
            obj.attributes[key] = value


def _definition_name(av: ET.Element, attr_def_name: Dict[str, str]) -> Optional[str]:
    """The long-name of the first known definition an attribute value refers to."""
    definition = _first_child(av, "DEFINITION")
    def_name: Optional[str] = None
    if definition is not None:
        for ref in definition:
            def_name = attr_def_name.get((ref.text or "").strip())
            if def_name:
                break
    return def_name


def _record_xhtml(av: ET.Element, obj: ReqIFObject, key: str) -> None:
    """Record an XHTML value both as HTML and as plain text."""
    the_value = _first_child(av, "THE-VALUE")
    if the_value is not None:
        obj.html_attributes[key] = _xhtml_to_html(the_value)
        obj.attributes[key] = _plain_text(the_value)


def _plain_value(av: ET.Element) -> Optional[str]:
    """A plain value from the THE-VALUE attribute, else from a THE-VALUE element's text."""
    value = av.get("THE-VALUE")
    if value is None:
        the_value = _first_child(av, "THE-VALUE")
        value = _plain_text(the_value) if the_value is not None else None
    return value


def _build_hierarchy(
    hier: ET.Element,
    *,
    depth: int = 1,
    ancestor_refs: frozenset[str] = frozenset(),
) -> Optional[ReqIFHierarchyNode]:
    if depth > settings.REQIF_MAX_HIERARCHY_DEPTH:
        raise ReqIFParseError(
            "ReqIF hierarchy depth limit exceeded "
            f"(maximum {settings.REQIF_MAX_HIERARCHY_DEPTH})."
        )
    object_ref = _ref_text(hier, "OBJECT")
    if object_ref and object_ref in ancestor_refs:
        raise ReqIFParseError("ReqIF hierarchy cycle detected.")
    node = ReqIFHierarchyNode(object_ref=object_ref or "")
    next_ancestors = ancestor_refs | ({object_ref} if object_ref else set())
    node.children.extend(_child_nodes(hier, depth, next_ancestors))
    if not node.object_ref and not node.children:
        return None
    return node


def _child_nodes(
    hier: ET.Element, depth: int, ancestors: frozenset[str]
) -> List[ReqIFHierarchyNode]:
    """The non-empty hierarchy nodes built from a hierarchy's spec-hierarchy children."""
    nodes: List[ReqIFHierarchyNode] = []
    children = _first_child(hier, "CHILDREN")
    if children is not None:
        for child in children:
            if _local(child.tag) == "spec-hierarchy":
                built = _build_hierarchy(
                    child,
                    depth=depth + 1,
                    ancestor_refs=frozenset(ancestors),
                )
                if built is not None:
                    nodes.append(built)
    return nodes


def _ref_text(parent: ET.Element, wrapper_local: str) -> Optional[str]:
    """Return the *-REF text inside a wrapper such as SOURCE/TARGET/TYPE/OBJECT.

    Text placed directly on the wrapper counts too.
    """
    wrapper = _first_child(parent, wrapper_local)
    if wrapper is None:
        return None
    for ref in wrapper:
        if _local(ref.tag).endswith("-ref") and ref.text:
            return ref.text.strip()
    return wrapper.text.strip() if wrapper.text and wrapper.text.strip() else None
