"""Typed document relationship rules for generic artefact links."""

from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS, normalize_document_kind

LINKABLE_ARTEFACT_KINDS = ("REQ", "TC", "DES", "RSK", "CHG", "TCO", "DEF", "CMP")
LINKABLE_DOC_KINDS = LINKABLE_ARTEFACT_KINDS + tuple(CANONICAL_DOCUMENT_KINDS)

LINK_RULE_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("REQ", "REQ", ("derives_from", "refines", "depends_on", "duplicates", "relates_to")),
    ("REQ", "STD", ("references",)),
    ("SPEC", "REQ", ("derives_from", "refines", "references")),
    ("SPEC", "SPEC", ("derives_from", "refines", "depends_on", "duplicates", "relates_to")),
    ("SPEC", "STD", ("references",)),
    ("STD", "STD", ("duplicates", "relates_to", "references")),
    ("TCO", "SPEC", ("verifies", "references")),
    ("TCO", "REQ", ("verifies", "references")),
    ("TCO", "TC", ("implements",)),
    ("TCO", "TCO", ("derives_from", "refines", "relates_to")),
    ("TCO", "STD", ("references",)),
    ("TC", "REQ", ("verifies",)),
    ("TC", "SPEC", ("verifies",)),
    ("TC", "PROT", ("implements", "references")),
    ("TC", "TC", ("depends_on", "duplicates", "relates_to")),
    ("TC", "STD", ("references",)),
    ("PROT", "REQ", ("verifies", "references")),
    ("PROT", "SPEC", ("verifies", "references")),
    ("PROT", "TCO", ("implements",)),
    ("PROT", "PROT", ("derives_from", "depends_on", "duplicates", "relates_to")),
    ("PROT", "STD", ("references",)),
    ("RPT", "REQ", ("references",)),
    ("RPT", "SPEC", ("references",)),
    ("RPT", "TCO", ("references",)),
    ("RPT", "TC", ("references",)),
    ("RPT", "PROT", ("references",)),
    ("RPT", "DES", ("references",)),
    ("RPT", "RSK", ("references",)),
    ("RPT", "CHG", ("references",)),
    ("RPT", "STD", ("references",)),
    ("RPT", "RPT", ("duplicates", "relates_to", "references")),
    ("DES", "REQ", ("satisfies", "implements", "references")),
    ("DES", "SPEC", ("implements", "references")),
    ("DES", "RSK", ("mitigates",)),
    ("DES", "DES", ("depends_on", "derives_from", "duplicates", "relates_to")),
    ("DES", "STD", ("references",)),
    ("RSK", "REQ", ("impacts", "mitigates", "references")),
    ("RSK", "SPEC", ("impacts", "references")),
    ("RSK", "DES", ("impacts", "references")),
    ("RSK", "TC", ("impacts", "references")),
    ("RSK", "TCO", ("impacts", "references")),
    ("RSK", "PROT", ("impacts", "references")),
    ("RSK", "CHG", ("impacts", "references")),
    ("RSK", "RSK", ("depends_on", "duplicates", "relates_to")),
    ("RSK", "STD", ("references",)),
    ("CHG", "REQ", ("impacts", "implements", "blocks", "references")),
    ("CHG", "SPEC", ("impacts", "implements", "blocks", "references")),
    ("CHG", "DES", ("impacts", "implements", "blocks", "references")),
    ("CHG", "TC", ("impacts", "blocks", "references")),
    ("CHG", "TCO", ("impacts", "blocks", "references")),
    ("CHG", "PROT", ("impacts", "blocks", "references")),
    ("CHG", "RSK", ("mitigates", "impacts", "references")),
    ("CHG", "CHG", ("depends_on", "duplicates", "blocks", "relates_to")),
    ("CHG", "STD", ("references",)),
    ("CHG", "DEF", ("implements", "references")),
    # DEF (defect) rules
    ("DEF", "REQ", ("impacts", "references")),
    ("DEF", "SPEC", ("impacts", "references")),
    ("DEF", "TC", ("references",)),
    ("DEF", "TCO", ("references",)),
    ("DEF", "PROT", ("references",)),
    ("DEF", "CHG", ("references",)),
    ("DEF", "RPT", ("references",)),
    ("DEF", "DES", ("impacts", "references")),
    ("DEF", "RSK", ("references",)),
    ("DEF", "DEF", ("duplicates", "relates_to", "depends_on")),
    ("DEF", "STD", ("references",)),
    ("DEF", "CMP", ("references",)),
    # CMP (campaign) rules
    ("CMP", "DEF", ("references",)),
    ("CMP", "REQ", ("verifies", "references")),
    ("CMP", "SPEC", ("verifies", "references")),
    ("CMP", "TC", ("references",)),
    ("CMP", "CMP", ("relates_to",)),
    # Reverse edges allowing TC/RPT/RSK to reference DEF
    ("TC", "DEF", ("references",)),
    ("RPT", "DEF", ("references",)),
    ("RSK", "DEF", ("impacts", "references")),
)


def normalize_linkable_type(value: str | None) -> str:
    if value is None:
        return ""
    upper_value = value.upper()
    normalized_document_kind = normalize_document_kind(upper_value)
    if normalized_document_kind in CANONICAL_DOCUMENT_KINDS:
        return normalized_document_kind
    return upper_value


def is_known_linkable_type(value: str | None) -> bool:
    return normalize_linkable_type(value) in LINKABLE_DOC_KINDS


def get_allowed_link_roles(source_type: str, target_type: str) -> tuple[str, ...]:
    normalized_source_type = normalize_linkable_type(source_type)
    normalized_target_type = normalize_linkable_type(target_type)

    if (
        normalized_source_type not in LINKABLE_DOC_KINDS
        or normalized_target_type not in LINKABLE_DOC_KINDS
    ):
        return ()

    for row_source, row_target, roles in LINK_RULE_ROWS:
        if row_source == normalized_source_type and row_target == normalized_target_type:
            return roles

    return ()


def is_allowed_link_role(source_type: str, target_type: str, role: str) -> bool:
    return role in get_allowed_link_roles(source_type, target_type)
