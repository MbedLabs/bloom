"""Typed document relationship rules for generic artefact links."""

from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS, normalize_document_kind

LINKABLE_ARTEFACT_KINDS = ("REQ", "TC", "DES", "RSK", "CHG", "CPT", "DEF", "CMP", "TS")
LINKABLE_DOC_KINDS = LINKABLE_ARTEFACT_KINDS + tuple(CANONICAL_DOCUMENT_KINDS)

LEGACY_LINK_KIND_ALIASES = {
    "TCO": "CPT",
    "PROT": "PRT",
}
LINK_RULE_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("REQ", "REQ", ("derives_from", "refines", "depends_on", "duplicates", "relates_to")),
    ("REQ", "SPEC", ("derives_from", "refines", "references")),
    ("REQ", "STD", ("references",)),
    ("REQ", "TS", ("references",)),
    ("REQ", "CMP", ("references",)),
    ("SPEC", "SPEC", ("derives_from", "refines", "depends_on", "duplicates", "relates_to")),
    ("SPEC", "STD", ("references",)),
    ("STD", "STD", ("duplicates", "relates_to", "references")),
    ("CPT", "SPEC", ("covers", "verifies", "references")),
    ("CPT", "REQ", ("covers", "verifies", "references")),
    ("CPT", "TC", ("implements",)),
    ("CPT", "CPT", ("derives_from", "refines", "relates_to")),
    ("CPT", "STD", ("references",)),
    ("CPT", "TS", ("references",)),
    ("TC", "REQ", ("verifies",)),
    ("TC", "SPEC", ("verifies",)),
    ("TC", "PRT", ("implements", "references")),
    ("TC", "TC", ("depends_on", "duplicates", "relates_to")),
    ("TC", "STD", ("references",)),
    ("TC", "DEF", ("references",)),
    ("TS", "TC", ("contains", "references")),
    ("TS", "CPT", ("contains", "references")),
    ("TS", "SPEC", ("covers", "references")),
    ("TS", "REQ", ("covers", "references")),
    ("TS", "TS", ("relates_to",)),
    ("TS", "CMP", ("relates_to",)),
    ("CMP", "SPEC", ("verifies", "references")),
    ("CMP", "REQ", ("covers", "references")),
    ("CMP", "TC", ("contains", "references")),
    ("CMP", "CPT", ("contains", "references")),
    ("CMP", "TS", ("relates_to",)),
    ("CMP", "DEF", ("references",)),
    ("CMP", "CMP", ("relates_to",)),
    ("PRT", "REQ", ("verifies", "references")),
    ("PRT", "SPEC", ("verifies", "references")),
    ("PRT", "CPT", ("implements",)),
    ("PRT", "PRT", ("derives_from", "depends_on", "duplicates", "relates_to")),
    ("PRT", "STD", ("references",)),
    ("RPT", "REQ", ("references",)),
    ("RPT", "SPEC", ("references",)),
    ("RPT", "CPT", ("references",)),
    ("RPT", "TC", ("references",)),
    ("RPT", "TS", ("references",)),
    ("RPT", "CMP", ("references",)),
    ("RPT", "PRT", ("references",)),
    ("RPT", "DES", ("references",)),
    ("RPT", "RSK", ("references",)),
    ("RPT", "CHG", ("references",)),
    ("RPT", "STD", ("references",)),
    ("RPT", "DEF", ("references",)),
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
    ("RSK", "CPT", ("impacts", "references")),
    ("RSK", "PRT", ("impacts", "references")),
    ("RSK", "CHG", ("impacts", "references")),
    ("RSK", "RSK", ("depends_on", "duplicates", "relates_to")),
    ("RSK", "STD", ("references",)),
    ("RSK", "DEF", ("impacts", "references")),
    ("CHG", "REQ", ("impacts", "implements", "blocks", "references")),
    ("CHG", "SPEC", ("impacts", "implements", "blocks", "references")),
    ("CHG", "DES", ("impacts", "implements", "blocks", "references")),
    ("CHG", "TC", ("impacts", "blocks", "references")),
    ("CHG", "CPT", ("impacts", "blocks", "references")),
    ("CHG", "PRT", ("impacts", "blocks", "references")),
    ("CHG", "RSK", ("mitigates", "impacts", "references")),
    ("CHG", "CHG", ("depends_on", "duplicates", "blocks", "relates_to")),
    ("CHG", "STD", ("references",)),
    ("CHG", "DEF", ("implements", "references")),
    ("DEF", "REQ", ("impacts", "references")),
    ("DEF", "SPEC", ("impacts", "references")),
    ("DEF", "TC", ("references",)),
    ("DEF", "CPT", ("references",)),
    ("DEF", "PRT", ("references",)),
    ("DEF", "CHG", ("references",)),
    ("DEF", "RPT", ("references",)),
    ("DEF", "DES", ("impacts", "references")),
    ("DEF", "RSK", ("references",)),
    ("DEF", "DEF", ("duplicates", "relates_to", "depends_on")),
    ("DEF", "STD", ("references",)),
    ("DEF", "CMP", ("references",)),
    ("CMP", "DEF", ("references",)),
)


def normalize_linkable_type(value: str | None) -> str:
    if value is None:
        return ""
    upper_value = value.upper()
    legacy_kind = LEGACY_LINK_KIND_ALIASES.get(upper_value)
    if legacy_kind:
        return legacy_kind
    normalized_document_kind = normalize_document_kind(upper_value)
    if normalized_document_kind in CANONICAL_DOCUMENT_KINDS:
        return normalized_document_kind
    return upper_value


def get_linkable_type_storage_values(value: str | None) -> tuple[str, ...]:
    """Return canonical and legacy DB values for a linkable document kind."""

    canonical_value = normalize_linkable_type(value)
    legacy_values = tuple(
        legacy_value
        for legacy_value, mapped_value in LEGACY_LINK_KIND_ALIASES.items()
        if mapped_value == canonical_value
    )
    return (canonical_value, *legacy_values)


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
