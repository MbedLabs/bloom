"""Unit tests for the ReqIF import parser (app/core/reqif.py)."""

import io
import zipfile

import pytest

from app.core.reqif import (
    FOREIGN_ID_HINTS,
    TEXT_ATTRIBUTE_HINTS,
    TITLE_ATTRIBUTE_HINTS,
    ReqIFParseError,
    parse_reqif,
)

SAMPLE_REQIF = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF xmlns="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <CORE-CONTENT>
    <REQ-IF-CONTENT>
      <DATATYPES>
        <DATATYPE-DEFINITION-ENUMERATION IDENTIFIER="DT-PRIO" LONG-NAME="Priority">
          <SPECIFIED-VALUES>
            <ENUM-VALUE IDENTIFIER="PRIO-HIGH" LONG-NAME="High"/>
            <ENUM-VALUE IDENTIFIER="PRIO-MED" LONG-NAME="Medium"/>
            <ENUM-VALUE IDENTIFIER="PRIO-LOW" LONG-NAME="Low"/>
          </SPECIFIED-VALUES>
        </DATATYPE-DEFINITION-ENUMERATION>
      </DATATYPES>
      <SPEC-TYPES>
        <SPEC-OBJECT-TYPE IDENTIFIER="OT-REQ" LONG-NAME="Requirement Type">
          <SPEC-ATTRIBUTES>
            <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="AD-HEADING" LONG-NAME="ReqIF.ChapterName"/>
            <ATTRIBUTE-DEFINITION-XHTML IDENTIFIER="AD-TEXT" LONG-NAME="ReqIF.Text"/>
            <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="AD-FID" LONG-NAME="ReqIF.ForeignID"/>
            <ATTRIBUTE-DEFINITION-ENUMERATION IDENTIFIER="AD-PRIO" LONG-NAME="Priority">
              <TYPE>
                <DATATYPE-DEFINITION-ENUMERATION-REF>DT-PRIO</DATATYPE-DEFINITION-ENUMERATION-REF>
              </TYPE>
            </ATTRIBUTE-DEFINITION-ENUMERATION>
          </SPEC-ATTRIBUTES>
        </SPEC-OBJECT-TYPE>
        <SPEC-RELATION-TYPE IDENTIFIER="RT-REFINES" LONG-NAME="Refines"/>
      </SPEC-TYPES>
      <SPEC-OBJECTS>
        <SPEC-OBJECT IDENTIFIER="OBJ-1">
          <VALUES>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="System Requirements">
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-STRING-REF>AD-HEADING</ATTRIBUTE-DEFINITION-STRING-REF>
              </DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
          </VALUES>
        </SPEC-OBJECT>
        <SPEC-OBJECT IDENTIFIER="OBJ-2">
          <VALUES>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="Login">
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-STRING-REF>AD-HEADING</ATTRIBUTE-DEFINITION-STRING-REF>
              </DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-XHTML>
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-XHTML-REF>AD-TEXT</ATTRIBUTE-DEFINITION-XHTML-REF>
              </DEFINITION>
              <THE-VALUE><xhtml:div>The system <xhtml:b>shall</xhtml:b> allow login.</xhtml:div></THE-VALUE>
            </ATTRIBUTE-VALUE-XHTML>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="SYS-042">
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-STRING-REF>AD-FID</ATTRIBUTE-DEFINITION-STRING-REF>
              </DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-ENUMERATION>
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-ENUMERATION-REF>AD-PRIO</ATTRIBUTE-DEFINITION-ENUMERATION-REF>
              </DEFINITION>
              <VALUES>
                <ENUM-VALUE-REF>PRIO-HIGH</ENUM-VALUE-REF>
              </VALUES>
            </ATTRIBUTE-VALUE-ENUMERATION>
          </VALUES>
        </SPEC-OBJECT>
      </SPEC-OBJECTS>
      <SPEC-RELATIONS>
        <SPEC-RELATION IDENTIFIER="REL-1">
          <TYPE><SPEC-RELATION-TYPE-REF>RT-REFINES</SPEC-RELATION-TYPE-REF></TYPE>
          <SOURCE><SPEC-OBJECT-REF>OBJ-2</SPEC-OBJECT-REF></SOURCE>
          <TARGET><SPEC-OBJECT-REF>OBJ-1</SPEC-OBJECT-REF></TARGET>
        </SPEC-RELATION>
      </SPEC-RELATIONS>
      <SPECIFICATIONS>
        <SPECIFICATION IDENTIFIER="SPEC-1" LONG-NAME="System Specification">
          <CHILDREN>
            <SPEC-HIERARCHY IDENTIFIER="H-1">
              <OBJECT><SPEC-OBJECT-REF>OBJ-1</SPEC-OBJECT-REF></OBJECT>
              <CHILDREN>
                <SPEC-HIERARCHY IDENTIFIER="H-2">
                  <OBJECT><SPEC-OBJECT-REF>OBJ-2</SPEC-OBJECT-REF></OBJECT>
                </SPEC-HIERARCHY>
              </CHILDREN>
            </SPEC-HIERARCHY>
          </CHILDREN>
        </SPECIFICATION>
      </SPECIFICATIONS>
    </REQ-IF-CONTENT>
  </CORE-CONTENT>
</REQ-IF>
""".encode(
    "utf-8"
)


def test_parses_all_spec_objects():
    bundle = parse_reqif(SAMPLE_REQIF)
    assert set(bundle.objects) == {"OBJ-1", "OBJ-2"}


def test_title_resolves_from_chaptername_attribute():
    bundle = parse_reqif(SAMPLE_REQIF)
    assert bundle.objects["OBJ-1"].first_attr(TITLE_ATTRIBUTE_HINTS) == "System Requirements"
    assert bundle.objects["OBJ-2"].first_attr(TITLE_ATTRIBUTE_HINTS) == "Login"


def test_xhtml_body_preserved_as_html_and_plain_text():
    obj = parse_reqif(SAMPLE_REQIF).objects["OBJ-2"]
    html = obj.first_html(TEXT_ATTRIBUTE_HINTS)
    assert html is not None
    assert "<b>shall</b>" in html
    assert "allow login" in html
    assert obj.first_attr(TEXT_ATTRIBUTE_HINTS) == "The system shall allow login."


def test_enumeration_value_resolves_to_long_name():
    obj = parse_reqif(SAMPLE_REQIF).objects["OBJ-2"]
    assert obj.attributes.get("priority") == "High"


def test_foreign_id_attribute_captured():
    obj = parse_reqif(SAMPLE_REQIF).objects["OBJ-2"]
    assert obj.first_attr(FOREIGN_ID_HINTS) == "SYS-042"


def test_hierarchy_orders_parent_before_child():
    bundle = parse_reqif(SAMPLE_REQIF)
    ordered = bundle.ordered_object_refs()
    assert ordered == [("OBJ-1", None), ("OBJ-2", "OBJ-1")]


def test_relations_parsed_with_type_name():
    bundle = parse_reqif(SAMPLE_REQIF)
    assert len(bundle.relations) == 1
    rel = bundle.relations[0]
    assert (rel.source_ref, rel.target_ref) == ("OBJ-2", "OBJ-1")
    assert rel.type_name == "Refines"


def test_reqifz_zip_container_is_unwrapped():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("export.reqif", SAMPLE_REQIF)
    bundle = parse_reqif(buf.getvalue())
    assert set(bundle.objects) == {"OBJ-1", "OBJ-2"}


def test_objects_not_in_hierarchy_are_not_dropped():
    xml = SAMPLE_REQIF.replace(
        b"</SPEC-OBJECTS>",
        b'<SPEC-OBJECT IDENTIFIER="OBJ-3"><VALUES/></SPEC-OBJECT></SPEC-OBJECTS>',
    )
    bundle = parse_reqif(xml)
    ordered = bundle.ordered_object_refs()
    assert ("OBJ-3", None) in ordered
    assert len(ordered) == 3


def test_empty_input_rejected():
    with pytest.raises(ReqIFParseError):
        parse_reqif(b"")


def test_non_xml_rejected():
    with pytest.raises(ReqIFParseError):
        parse_reqif(b"this is not xml at all")


def test_xml_without_reqif_content_rejected():
    with pytest.raises(ReqIFParseError):
        parse_reqif(b"<html><body>nope</body></html>")


import pytest_asyncio  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.api.import_service import import_reqif  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models import ArtefactLink, Project, Requirement, RequirementLink  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


class _FakeUpload:
    def __init__(self, data: bytes):
        self._data = data
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        end = len(self._data) if size < 0 else self._offset + size
        chunk = self._data[self._offset : end]
        self._offset += len(chunk)
        return chunk


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(Project(name="System Project", prefix="SYS"))
        db.add(
            User(
                email="admin@test.local",
                full_name="Ada Admin",
                hashed_password="x",
                role=UserRole.admin,
                is_active=True,
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


async def test_import_creates_requirements_with_hierarchy_and_links(session):
    admin = await _admin(session)
    result = await import_reqif(
        project_id=1, file=_FakeUpload(SAMPLE_REQIF), db=session, current_user=admin
    )
    assert result.imported == 2
    assert result.links_created == 1
    assert result.specifications == 1
    assert result.new_ids == ["SYS-REQ-001", "SYS-REQ-002"]

    reqs = {r.req_id: r for r in (await session.execute(select(Requirement))).scalars().all()}
    parent = reqs["SYS-REQ-001"]
    child = reqs["SYS-REQ-002"]
    assert parent.title == "System Requirements"
    assert child.title == "Login"
    assert child.parent_id == parent.id
    assert child.priority == "High"
    assert child.content_html
    assert "<b>shall</b>" in child.content_html
    assert child.req_origin == "External"
    assert parent.source_ref == "OBJ-1"

    link = (await session.execute(select(ArtefactLink))).scalars().one()
    assert (link.source_id, link.target_id) == (child.id, parent.id)
    assert (link.source_type, link.target_type, link.role) == ("REQ", "REQ", "refines")
    assert (await session.execute(select(RequirementLink))).scalars().all() == []


async def test_reimport_is_idempotent(session):
    admin = await _admin(session)
    first = await import_reqif(
        project_id=1, file=_FakeUpload(SAMPLE_REQIF), db=session, current_user=admin
    )
    assert first.imported == 2
    assert first.links_created == 1

    second = await import_reqif(
        project_id=1, file=_FakeUpload(SAMPLE_REQIF), db=session, current_user=admin
    )
    assert second.imported == 0
    assert second.skipped == 2
    assert second.links_created == 0

    total = len((await session.execute(select(Requirement))).scalars().all())
    assert total == 2


async def test_missing_project_returns_404(session):
    from fastapi import HTTPException

    admin = await _admin(session)
    upload = _FakeUpload(SAMPLE_REQIF)
    with pytest.raises(HTTPException) as exc:
        await import_reqif(project_id=999, file=upload, db=session, current_user=admin)
    assert exc.value.status_code == 404


async def test_unparseable_upload_returns_422(session):
    from fastapi import HTTPException

    admin = await _admin(session)
    upload = _FakeUpload(b"not reqif")
    with pytest.raises(HTTPException) as exc:
        await import_reqif(project_id=1, file=upload, db=session, current_user=admin)
    assert exc.value.status_code == 422


@pytest.mark.parametrize(
    ("type_name", "role"),
    [
        ("Refines", "refines"),
        ("Derives", "derives_from"),
        ("Depends", "depends_on"),
        ("Satisfies", "relates_to"),
        ("Copies", "duplicates"),
    ],
)
async def test_reqif_relations_are_visible_as_normalized_links(session, type_name, role):
    from app.api.link_read_utils import iter_req_req_outgoing_neighbors

    result = await import_reqif(
        project_id=1,
        file=_FakeUpload(
            SAMPLE_REQIF.replace(b'LONG-NAME="Refines"', f'LONG-NAME="{type_name}"'.encode())
        ),
        db=session,
        current_user=await _admin(session),
    )
    assert result.links_created == 1
    link = (await session.execute(select(ArtefactLink))).scalar_one()
    assert link.role == role
    assert [edge async for edge in iter_req_req_outgoing_neighbors(link.source_id, 1, session)] == [
        (link.target_id, role)
    ]


async def test_reqif_unknown_relation_fails_with_identifier_and_type(session):
    from fastapi import HTTPException

    upload = _FakeUpload(
        SAMPLE_REQIF.replace(b'LONG-NAME="Refines"', b'LONG-NAME="Unknown Relation"')
    )
    admin = await _admin(session)
    with pytest.raises(HTTPException) as failed:
        await import_reqif(project_id=1, file=upload, db=session, current_user=admin)
    assert failed.value.status_code == 422
    assert "REL-1" in failed.value.detail
    assert "Unknown Relation" in failed.value.detail
    assert (await session.execute(select(Requirement))).scalars().all() == []
    assert (await session.execute(select(ArtefactLink))).scalars().all() == []


async def test_reqif_disallowed_mapped_role_fails_with_relation(session, monkeypatch):
    from fastapi import HTTPException

    from app.core import link_rules

    monkeypatch.setattr(link_rules, "LINK_RULE_ROWS", ())
    upload = _FakeUpload(SAMPLE_REQIF)
    admin = await _admin(session)
    with pytest.raises(HTTPException) as failed:
        await import_reqif(project_id=1, file=upload, db=session, current_user=admin)
    assert failed.value.status_code == 422
    assert "REL-1" in failed.value.detail
    assert "Refines" in failed.value.detail
    assert (await session.execute(select(ArtefactLink))).scalars().all() == []


async def test_reqif_preserves_and_deduplicates_legacy_equivalents(session):
    session.add_all(
        [
            Requirement(project_id=1, req_id="SYS-REQ-001", title="Parent", source_ref="OBJ-1"),
            Requirement(project_id=1, req_id="SYS-REQ-002", title="Child", source_ref="OBJ-2"),
        ]
    )
    await session.flush()
    legacy = RequirementLink(source_id=2, target_id=1, link_type="derived_from")
    session.add(legacy)
    await session.flush()
    result = await import_reqif(
        project_id=1,
        file=_FakeUpload(SAMPLE_REQIF.replace(b'LONG-NAME="Refines"', b'LONG-NAME="Derives"')),
        db=session,
        current_user=await _admin(session),
    )
    assert result.links_created == 0
    assert (await session.execute(select(RequirementLink))).scalar_one().id == legacy.id
    assert (await session.execute(select(ArtefactLink))).scalars().all() == []
