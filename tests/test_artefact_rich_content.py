"""Every artefact the editor can open must accept and return its rich content.

The models carry ``content_json``/``content_html`` and the document editor sends
them, but the Create/Update schemas are ``StrictModel`` (``extra="forbid"``). For
every type except Document those fields were missing from the schema, so each
save was rejected with a 422 and the editor could never persist a body.
"""

import pytest

from app.schemas import schemas

# Artefact types whose model has content_json/content_html columns and whose
# detail page opens the rich-text editor.
RICH_CONTENT_TYPES = [
    "Requirement",
    "TestCase",
    "Document",
    "DesignItem",
    "RiskItem",
    "ChangeRequest",
    "TestConcept",
]


@pytest.mark.parametrize("artefact", RICH_CONTENT_TYPES)
@pytest.mark.parametrize("suffix", ["Create", "Update", "Response"])
def test_schema_carries_rich_content_fields(artefact, suffix):
    model = getattr(schemas, f"{artefact}{suffix}")
    fields = model.model_fields

    assert "content_json" in fields, f"{artefact}{suffix} drops content_json"
    assert "content_html" in fields, f"{artefact}{suffix} drops content_html"


@pytest.mark.parametrize("artefact", RICH_CONTENT_TYPES)
def test_create_schema_accepts_an_editor_payload(artefact):
    """A strict schema rejecting the editor's body is exactly the 422 users hit."""
    model = getattr(schemas, f"{artefact}Create")
    payload = {
        "project_id": 1,
        "content_json": {"type": "doc", "content": []},
        "content_html": "<p>body</p>",
    }
    # Required scalar fields differ per artefact; supply the common ones.
    for name, field in model.model_fields.items():
        if field.is_required() and name not in payload:
            payload[name] = "Title" if name in {"title", "name"} else "x"

    instance = model(**payload)

    assert instance.content_json == {"type": "doc", "content": []}
    assert instance.content_html == "<p>body</p>"
