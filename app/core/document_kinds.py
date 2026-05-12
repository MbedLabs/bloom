"""Canonical document kind helpers for shared Document rows."""

from fastapi import HTTPException

CANONICAL_DOCUMENT_KINDS = ("SPEC", "PRT", "RPT", "STD")

DOCUMENT_KIND_SLUGS = {
    "SPEC": "specifications",
    "PRT": "protocols",
    "RPT": "reports",
    "STD": "standards",
}

SLUG_TO_DOCUMENT_KIND = {slug: kind for kind, slug in DOCUMENT_KIND_SLUGS.items()}

LEGACY_DOCUMENT_KIND_MAP = {
    "DOC": "SPEC",
    "Specification": "SPEC",
    "Protocol": "PRT",
    "PROT": "PRT",
    "Report": "RPT",
    "External Standard": "STD",
    "SPEC": "SPEC",
    "PRT": "PRT",
    "RPT": "RPT",
    "STD": "STD",
}


def normalize_document_kind(value: str | None) -> str:
    """Normalize legacy/stored document kind values to canonical machine codes."""
    if value is None:
        return "SPEC"
    return LEGACY_DOCUMENT_KIND_MAP.get(value, value.upper())


def require_document_kind(value: str | None) -> str:
    """Validate a public shared-document kind without accepting legacy wire values."""
    if value not in CANONICAL_DOCUMENT_KINDS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid document kind '{value}'. "
                "Supported shared-document kinds: SPEC, PRT, RPT, STD. "
                "Legacy values like DOC or human-readable labels are not accepted on the public API."
            ),
        )
    return value


def document_kind_from_slug(slug: str) -> str:
    """Resolve canonical document kind from a route slug."""
    kind = SLUG_TO_DOCUMENT_KIND.get(slug)
    if not kind:
        raise HTTPException(status_code=404, detail=f"Unknown document kind slug '{slug}'")
    return kind
