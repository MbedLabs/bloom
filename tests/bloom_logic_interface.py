"""
* @file     ${tests/bloom_logic_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's logic tests: services and helpers called directly, without the app.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Only the lifespan check loads the application object, inside that one call.
"""

import ast
import asyncio
import base64
import contextlib
import copy
import csv
import hashlib
import hmac
import importlib
import inspect
import io
import json
import os
import pkgutil
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import typing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from xml.etree import ElementTree

import httpx
import yaml
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select, text
from starlette.datastructures import Headers

from app import audit
from app import main as main_module
from app.api import (
    artefact_utils,
    campaigns,
    company_logo,
    docs_facade,
    export,
    import_service,
    integrations,
)
from app.api import project_variables as project_variables_api
from app.api.export import (
    _test_cases_markdown,
    _test_cases_xml,
    export_requirements,
    export_test_cases,
    export_traceability,
)
from app.api.import_service import (
    ImportResult,
    _import_docs,
    _import_rows_from_xml,
    _next_number,
    import_test_cases_file,
)
from app.api.policies import _apply_rules, _validate_rules, policy_rules
from app.core import (
    document_kinds,
    id_generator,
    link_rules,
    passwords,
    permissions,
    security,
)
from app.core.config import Settings, settings
from app.core.identity import POWERED_BY, PRODUCT_IDENTITY, PRODUCT_NAME
from app.core.md_import import (
    Parameter,
    parameter_name_collisions,
    parse_markdown_document,
)
from app.core.permissions import (
    DOC_TYPE_RESOURCES,
    EXTERNAL_DENIED_ACTIONS,
    RESOURCE_ACTIONS,
    RESOURCES,
    actions_for_rule,
    actions_on,
    rule_of,
)
from app.core.policy_seed import DEFAULT_GROUPS, DEFAULT_POLICIES
from app.core.security import (
    _policy_terms,
    access_terms,
    create_access_token,
    effective_permissions,
    get_current_user,
    get_external_doc_types,
    require_role,
)
from app.core.service_auth import (
    create_service_credential,
    require_bud_sync_token,
    revoke_service_credential,
)
from app.core.tc_steps import make_row, rows_to_text, text_to_rows
from app.models import (
    ArtefactLink,
    AuditEvent,
    Defect,
    Document,
    ImportAttempt,
    IntegrationSetting,
    Project,
    Requirement,
    RequirementLink,
    SystemMarker,
    TestCase,
    user_token,
)
from app.models.groups import Group, GroupMembership, Policy
from app.models.models import ServiceCredential
from app.models.project_membership import ProjectAccess
from app.models.user import User, UserRole
from app.schemas import ProjectCreate, ProjectVariableUpdate
from app.schemas import auth as auth_schemas
from app.schemas import schemas
from app.schemas.groups import PolicyRule
from app.services import (
    attachment_storage,
    import_attempts,
    integration_sync,
    jira_outbound,
    mail_service,
    rich_text,
    tag_links,
    token_service,
)
from app.services.attachment_cleanup import reconcile_attachments
from app.services.jira_inbound import (
    adf_to_text,
    bloom_level,
    build_jql,
    is_resolved,
    issue_matches,
    issue_types,
    issue_url,
    referenced_tc_ids,
    search_fields,
)
from tests.bloom_interface import BloomInterface

ROOT = Path(__file__).resolve().parents[1]


class BloomLogicInterface(BloomInterface):

    def bloom_get_setting(self, setting_id):
        return self._run(self._get(IntegrationSetting, setting_id))

    def bloom_mark_sends_since(self, moment):
        self._run(self._mark_sends_since(moment))

    def bloom_add_unlinked_defect(self, project_id, title):
        return self._run(self._link_defect(project_id, None, None, None, {"title": title}))

    def bloom_serve_jira_creation(self, first_number, refuse_after=None):
        created = []

        def answer(request):
            if request.url.path.endswith(self.parameters.JIRA_MYSELF):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                )
            if request.method == "POST" and request.url.path.endswith(
                self.parameters.OUTBOUND_ISSUE_PATH
            ):
                created.append(json.loads(request.content)["fields"])
                if refuse_after is not None and len(created) > refuse_after:
                    return httpx.Response(
                        self.parameters.STATUS_BAD_REQUEST, json={"errorMessages": ["refused"]}
                    )
                key = self.bloom_jira_key(first_number + len(created) - 1)
                return httpx.Response(self.parameters.STATUS_CREATED, json={"key": key})
            if request.method == "GET":
                return httpx.Response(self.parameters.STATUS_OK, json={"fields": {}})
            return httpx.Response(self.parameters.STATUS_OK, json={"issues": [], "isLast": True})

        self.bloom_serve(answer)
        return created

    def bloom_send_now(self, setting_id):
        return self._run(self._send_now(setting_id))

    async def _send_now(self, setting_id):
        async with self.maker() as db:
            setting = await db.get(IntegrationSetting, setting_id)
            run = await integration_sync.sync_now(db, setting, maker=self.maker)
            await db.commit()
            return run

    async def _mark_sends_since(self, moment):
        async with self.maker() as db:
            db.add(SystemMarker(name=jira_outbound.SENDS_SINCE, marked_at=moment))
            await db.commit()

    def bloom_get_setting_response(self, setting_id):
        setting = self.bloom_get_setting(setting_id)
        return json.loads(integrations._setting_response(setting).model_dump_json())

    def bloom_build_jira_issue(self, key, kind=None, category=None, status=None, **fields):
        return {
            "key": key,
            "fields": {
                "issuetype": {"name": kind or self.parameters.BUG},
                "status": {
                    "name": status or self.parameters.JIRA_TO_DO,
                    "statusCategory": {"key": category or self.parameters.JIRA_NEW},
                },
                "summary": fields.pop("summary", key),
                **fields,
            },
        }

    def bloom_jira_time(self, moment, offset_hours):
        local = moment + timedelta(hours=offset_hours)
        sign = "+" if offset_hours >= 0 else "-"
        return f"{local:%Y-%m-%dT%H:%M:%S}.000{sign}{abs(offset_hours):02d}00"

    def bloom_git_time(self, moment):
        return f"{moment:%Y-%m-%dT%H:%M:%S}Z"

    def bloom_serve_jira(self, creation=(), changed=(), issue_status=None):
        statuses = issue_status or {}

        def answer(request):
            path = request.url.path
            if path.endswith(self.parameters.JIRA_MYSELF):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                )
            if request.method == "POST" and path.endswith(self.parameters.JIRA_SEARCH):
                query = json.loads(request.content)["jql"]
                self.site.jql.append(query)
                issues = creation if self.parameters.CREATION_MARK in query else changed
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": list(issues), "isLast": True}
                )
            if request.method == "GET" and self.parameters.JIRA_ISSUE in path:
                key = path.rsplit("/", 1)[1]
                self.site.reads.append(key)
                return httpx.Response(
                    statuses.get(key, self.parameters.STATUS_OK), json={"fields": {}}
                )
            return httpx.Response(self.parameters.STATUS_SERVER_ERROR)

        self.bloom_serve(answer)

    def bloom_serve_issue_list(self, issues, unreadable_repo=None, unreadable_status=None):
        def answer(request):
            if unreadable_repo and request.url.path.startswith(f"/repos/{unreadable_repo}"):
                return httpx.Response(unreadable_status, json=[])
            return httpx.Response(self.parameters.STATUS_OK, json=list(issues))

        self.bloom_serve(answer)

    def bloom_serve_redirect(self, repo, status, location, issues):
        def answer(request):
            if request.url.path.startswith(f"/repos/{repo}"):
                return httpx.Response(status, headers={"location": location})
            return httpx.Response(self.parameters.STATUS_OK, json=list(issues))

        self.bloom_serve(answer)

    def bloom_serve_by_repo(self, answers):
        def answer(request):
            for repo, (status, headers, body) in answers.items():
                if request.url.path.startswith(f"/repos/{repo}/"):
                    return httpx.Response(status, headers=headers, json=body)
            return httpx.Response(self.parameters.STATUS_NOT_FOUND, json={})

        self.bloom_serve(answer)

    def bloom_cap_searches(self, cap):
        self.patches.enter_context(patch.object(integrations, "MAX_PULLED_ISSUES", cap))
        self.patches.enter_context(patch.object(integration_sync, "MAX_PULLED_ISSUES", cap))

    def bloom_check_removals(self, count):
        self.patches.enter_context(patch.object(integration_sync, "REMOVAL_CHECKS", count))

    def bloom_save_during_search(self, setting_id, label, when):
        async def save(setting):
            async with self.maker() as db:
                row = await db.get(IntegrationSetting, setting_id)
                row.jira_label = label
                row.updated_at = when
                await db.commit()

        self._after_each_search(save)

    def bloom_link_defect_during_search(self, project_id, number):
        async def link(setting):
            await self._link_defect(project_id, "jira", self.parameters.JIRA_PROJECT, number, {})

        self._after_each_search(link)

    def bloom_fail_search_of(self, project_key, text):
        original = integration_sync._fetch_jira

        async def fetch(setting, **kw):
            if setting.jira_project_key == project_key:
                raise RuntimeError(text)
            return await original(setting, **kw)

        self.patches.enter_context(patch.object(integration_sync, "_fetch_jira", fetch))

    def bloom_run_sync(self, now):
        return self._run(integration_sync.run_due(maker=self.maker, now=now))

    def bloom_claim(self, setting_id, minutes, now):
        return self._run(integration_sync.claim(self.maker, setting_id, minutes, now))

    def bloom_save_setting(self, setting_id, admin_email, **changes):
        async def save(db, admin):
            update = integrations.IntegrationSettingUpdate(**changes)
            return await integrations.update_integration_setting(
                setting_id, update, db=db, current_user=admin
            )

        self._run(self._as_admin(admin_email, save))

    def bloom_compute_next_id(self, existing_ids, prefix, type_code):
        try:
            return id_generator.compute_next_id(existing_ids, prefix, type_code), None
        except ValueError as exc:
            return None, type(exc).__name__

    def bloom_default_catalogue(self):
        return copy.deepcopy(DEFAULT_POLICIES), copy.deepcopy(DEFAULT_GROUPS)

    def bloom_resource_actions(self):
        return {resource: set(actions) for resource, actions in RESOURCE_ACTIONS.items()}

    def bloom_resources(self):
        return list(RESOURCES)

    def bloom_load_migration(self, name):
        path = ROOT / "alembic" / "versions" / name
        spec = importlib.util.spec_from_file_location(path.stem, path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        return migration

    def bloom_widened_ids(self, existing_ids, prefix, type_code, width):
        return id_generator.widened_ids(existing_ids, prefix, type_code, width)

    def bloom_id_pattern_matches(self, value):
        return id_generator.DOC_ID_PATTERN.fullmatch(value) is not None

    def bloom_id_refusal(self, existing_ids, prefix, type_code):
        try:
            id_generator.compute_next_id(existing_ids, prefix, type_code)
        except ValueError as refused:
            return str(refused)
        return None

    def bloom_normalize_doc_id(self, value, **expected):
        try:
            return id_generator.normalize_doc_id(value, **expected), None
        except ValueError as refused:
            return None, str(refused)

    def bloom_list_docs_routes(self):
        return [route.path for route in docs_facade.router.routes]

    def bloom_external_doc_types_as_admin(self, project_id):
        db = AsyncMock()
        admin = SimpleNamespace(id=self.parameters.EXTERNAL_USER_ID, role=UserRole.admin)
        allowed = self._run(get_external_doc_types(db, admin, project_id))
        return SimpleNamespace(allowed=allowed, queries=db.execute.await_count)

    def bloom_identity(self):
        return PRODUCT_NAME, PRODUCT_IDENTITY, POWERED_BY

    def bloom_capture_mail(self, sender, **fields):
        sent = []

        def send_email(*, to_email, subject, text_body, html_body=None):
            sent.append({"to": to_email, "subject": subject, "text": text_body, "html": html_body})

        with patch.object(mail_service, "send_email", send_email):
            getattr(mail_service, sender)(**fields)
        return sent

    def bloom_api_identity(self):
        return main_module.app.title, main_module.app.description

    def bloom_app_name_setting(self, name):
        with self._temp_dir() as folder, contextlib.ExitStack() as stack:
            env_file = Path(folder) / ".env"
            env_file.write_text(f"BLOOM_APP_NAME={name} from dotenv\n", encoding="utf-8")
            stack.enter_context(patch.dict(os.environ, {"BLOOM_APP_NAME": name}))
            os.environ.pop("BLOOM_DOTENV_DISABLED", None)
            stack.callback(os.environ.__setitem__, "BLOOM_DOTENV_DISABLED", "1")
            loaded = Settings(_env_file=env_file)
        return "BLOOM_APP_NAME" in Settings.model_fields, hasattr(loaded, "BLOOM_APP_NAME")

    def bloom_title_with_app_name(self, name):
        env = {**os.environ, "BLOOM_APP_NAME": name, "BLOOM_DOTENV_DISABLED": "1"}
        done = subprocess.run(
            [sys.executable, "-c", "from app.main import app; print(app.title)"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        return done.stdout.strip().splitlines()[-1]

    def bloom_app_scope_case(self, scope="app", admission=None, role=None):
        return self._run(self._app_scope_case(scope, admission, role or UserRole.maintainer))

    def bloom_admin_permissions(self):
        return self._run(self._admin_permissions())

    def bloom_release_module(self):
        path = ROOT / "scripts" / "image_release.py"
        spec = importlib.util.spec_from_file_location("image_release", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def bloom_eligible_aliases(self, *arguments):
        return self.bloom_release_module().eligible_aliases(*arguments)

    def bloom_promote(self, image, aliases, digest_of=None):
        release, executed = self.bloom_release_module(), []
        try:
            if digest_of is None:
                release.promote(image, aliases, execute=lambda *call: executed.append(call))
            else:
                release.promote(image, aliases, digest_of, lambda *call: executed.append(call))
        except RuntimeError as refused:
            return str(refused), executed
        return None, executed

    def bloom_digest(self, reference, returncode=0, stdout="", stderr=""):
        release, calls = self.bloom_release_module(), []

        def run(args, **_kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

        with patch.object(release.subprocess, "run", run):
            try:
                return release.digest(reference), calls
            except ValueError as refused:
                return str(refused), calls

    def bloom_promote_workflow(self, digest_value, source, aliases):
        release, inspected, executed = self.bloom_release_module(), [], []

        def run(args, **_kwargs):
            inspected.append(args[4])
            return SimpleNamespace(returncode=0, stdout=digest_value, stderr="")

        with patch.object(release.subprocess, "run", run):
            found = release.digest(source)
            image = source.split(":sha-")[0] + "@" + digest_value
            release.promote(image, aliases, execute=lambda *call: executed.append(call))
        return found, len(executed), set(inspected)

    async def _app_scope_case(self, scope, admission, role):
        async with self.maker() as db:
            user = User(
                email="scope@example.com", full_name="Scope", hashed_password="x", role=role
            )
            project = Project(name="Demo", prefix="PRJ")
            policy = Policy(
                name="Application rules",
                scope=scope,
                permissions={
                    "users": ["view", "create", "edit"],
                    "access": ["delete"],
                    "REQ": ["view", "edit"],
                    "project": ["view"],
                },
                type_tags={"REQ": {"all": True}},
            )
            group = Group(name="Scope group", policies=[policy])
            db.add_all([user, project, group])
            await db.flush()
            db.add(GroupMembership(user_id=user.id, group_id=group.id))
            await db.flush()
            if admission:
                db.add(
                    ProjectAccess(project_id=project.id, group_id=group.id, inherit_policies=True)
                )
            if admission == "replacement":
                replacement = Policy(
                    name="Project read",
                    scope="document",
                    permissions={"REQ": ["view"]},
                    type_tags={"REQ": {"all": True}},
                )
                db.add(
                    ProjectAccess(project_id=project.id, user_id=user.id, policies=[replacement])
                )
            if admission == "bundles":
                first = Policy(
                    name="Direct requirements",
                    permissions={"REQ": ["view"]},
                    type_tags={"REQ": {"all": True}},
                )
                second = Policy(
                    name="Direct tests",
                    permissions={"TC": ["edit"]},
                    type_tags={"TC": {"all": True}},
                )
                bundles = [
                    Group(name="Readers", policies=[first]),
                    Group(name="Testers", policies=[second]),
                ]
                db.add_all(bundles)
                await db.flush()
                db.add_all(
                    [
                        ProjectAccess(project_id=project.id, user_id=user.id, policy_group=bundle)
                        for bundle in bundles
                    ]
                )
            await db.flush()
            try:
                await require_role(UserRole.admin)(user)
                admin_only = None
            except HTTPException as refused:
                admin_only = refused.status_code
            return SimpleNamespace(
                app_terms=sorted(
                    {r for term in await access_terms(db, user, None) for r in term.permissions}
                ),
                project_terms=await access_terms(db, user, project.id),
                app=await effective_permissions(db, user, None),
                project=await effective_permissions(db, user, project.id),
                admin_only=admin_only,
            )

    async def _admin_permissions(self):
        async with self.maker() as db:
            user = User(
                email="admin-scope@example.com",
                full_name="Admin",
                hashed_password="x",
                role=UserRole.admin,
            )
            db.add(user)
            await db.flush()
            return await effective_permissions(db, user, None)

    def bloom_seed_export_requirements(self):
        return self._run(self._seed_export_requirements())

    def bloom_export(self, kind, project_id, export_format):
        exports = {"requirements": export_requirements, "traceability": export_traceability}
        return self._run(self._export(exports[kind], project_id, export_format))

    async def _export(self, export, project_id, export_format):
        async with self.maker() as db:
            admin = (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()
            try:
                answer = await export(
                    project_id=project_id, format=export_format, db=db, current_user=admin
                )
            except HTTPException as exc:
                return SimpleNamespace(status=exc.status_code)
        csv_rows = None
        if export_format == "csv":
            csv_rows = list(csv.reader(io.StringIO(answer.body.decode("utf-8"))))
        return SimpleNamespace(
            status=200,
            media_type=answer.media_type,
            disposition=answer.headers.get("content-disposition", ""),
            body=answer.body,
            rows=csv_rows,
        )

    async def _seed_export_requirements(self):
        async with self.maker() as db:
            project = Project(name="Demo", prefix="PRJ")
            admin = User(
                email="admin@test.local",
                full_name="Ada Admin",
                hashed_password="x",
                role=UserRole.admin,
            )
            db.add_all([project, admin])
            await db.flush()
            login = Requirement(
                project_id=project.id,
                req_id="PRJ-REQ-001",
                title="Login shall be possible",
                description="Users must be able to log in.",
                status="Approved",
            )
            other = Requirement(
                project_id=project.id, req_id="PRJ-REQ-002", title="Uncovered requirement"
            )
            case = TestCase(
                project_id=project.id,
                tc_id="PRJ-TC-001",
                title="Verify login",
                last_execution_status="passed",
            )
            db.add_all([login, other, case])
            await db.flush()
            db.add(
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=case.id,
                    target_type="REQ",
                    target_id=login.id,
                    role="verifies",
                )
            )
            await db.commit()
            return project.id

    def bloom_seed_export_cases(self):
        return self._run(self._seed_export_cases())

    def bloom_export_test_cases(self, project_id, export_format):
        return self._run(self._export_test_cases(project_id, export_format))

    def bloom_jira_setting(self, **overrides):
        values = {
            "jira_issue_types": None,
            "jira_label": None,
            "jira_jql": None,
            "jira_reference_field": None,
            "jira_priority_map": None,
            "jira_project_key": "PROJ",
            "base_url": "https://acme.atlassian.net/",
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def bloom_adf_to_text(self, value):
        return adf_to_text(value)

    def bloom_jira_filter(self, setting, fields):
        return issue_matches(setting, fields)

    def bloom_jira_issue_types(self, setting):
        return issue_types(setting)

    def bloom_jira_level(self, setting, fields):
        return bloom_level(setting, fields)

    def bloom_jira_resolved(self, fields):
        return is_resolved(fields)

    def bloom_jira_references(self, prefix, setting, fields):
        return referenced_tc_ids(prefix, setting, fields)

    def bloom_jira_jql(self, setting):
        return build_jql(setting)

    def bloom_jira_search_fields(self, setting):
        return search_fields(setting)

    def bloom_jira_issue_url(self, setting, key):
        return issue_url(setting, key)

    async def _seed_export_cases(self):
        async with self.maker() as db:
            project = Project(name="Demo", prefix=self.parameters.ETC_PREFIX)
            admin = User(
                email="admin@test.local",
                full_name="Ada Admin",
                hashed_password="x",
                role=UserRole.admin,
            )
            db.add_all([project, admin])
            await db.flush()
            db.add_all(
                [
                    TestCase(
                        project_id=project.id,
                        tc_id=self.parameters.ETC_FIRST,
                        title="Verify login",
                        status="Approved",
                        preconditions="User exists",
                        steps=[
                            {"action": "Open login", "expected": "Form shown"},
                            {"action": "Submit", "expected": "Dashboard"},
                        ],
                        description="Covers the happy path.",
                        last_execution_status="passed",
                    ),
                    TestCase(
                        project_id=project.id,
                        tc_id=self.parameters.ETC_SECOND,
                        title="Verify logout",
                        status="Draft",
                    ),
                ]
            )
            await db.commit()
            return project.id, admin.id

    async def _export_test_cases(self, project_id, export_format):
        async with self.maker() as db:
            admin = (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()
            try:
                answer = await export_test_cases(
                    project_id=project_id, format=export_format, db=db, current_user=admin
                )
            except HTTPException as exc:
                return SimpleNamespace(status=exc.status_code)
        body = answer.body.decode("utf-8")
        return SimpleNamespace(
            status=200,
            media_type=answer.media_type,
            disposition=answer.headers["content-disposition"],
            body=body,
            rows=list(csv.reader(io.StringIO(body))) if export_format == "csv" else None,
            xml=ElementTree.fromstring(answer.body) if export_format == "xml" else None,
        )

    def bloom_seed_copy_projects(self):
        return self._run(self._seed_copy_projects())

    def bloom_copy_docs(self, doc_type, source_id, target_id, extra_ids=()):
        return self._run(self._copy_docs(doc_type, source_id, target_id, list(extra_ids)))

    def bloom_requirement_by_ref(self, req_id):
        return self._run(self._one(select(Requirement).where(Requirement.req_id == req_id)))

    def bloom_test_case_by_ref(self, tc_id):
        return self._run(self._one(select(TestCase).where(TestCase.tc_id == tc_id)))

    def bloom_test_case_titled(self, title):
        return self._run(self._one(select(TestCase).where(TestCase.title == title)))

    def bloom_list_test_cases(self):
        return self._run(self._all(select(TestCase).order_by(TestCase.id)))

    def bloom_next_number(self, project_id, prefix, kind):
        return self._run(self._next_number(project_id, prefix, kind))

    def bloom_seed_import_case(self):
        return self._run(self._seed_import_case())

    def bloom_import_test_cases(self, project_id, file_format, content):
        return self._run(self._import_test_cases(project_id, file_format, content))

    async def _one(self, query):
        async with self.maker() as db:
            return (await db.execute(query)).scalar_one()

    async def _next_number(self, project_id, prefix, kind):
        async with self.maker() as db:
            return await _next_number(db, project_id, prefix, kind)

    async def _seed_copy_projects(self):
        async with self.maker() as db:
            source = Project(
                name=self.parameters.CPY_SOURCE[0], prefix=self.parameters.CPY_SOURCE[1]
            )
            target = Project(
                name=self.parameters.CPY_TARGET[0], prefix=self.parameters.CPY_TARGET[1]
            )
            db.add_all([source, target])
            await db.flush()
            db.add_all(
                [
                    Requirement(
                        project_id=source.id,
                        req_id="PRJ-REQ-001",
                        title="Boot",
                        description="Boots fast",
                        content_json={"k": 1},
                        content_html="<p>1</p>",
                        status="Approved",
                        priority="High",
                        req_type="functional",
                        req_origin="customer",
                    ),
                    TestCase(
                        project_id=source.id,
                        tc_id="PRJ-TC-001",
                        title="Boot test",
                        status="Approved",
                        preconditions="Powered",
                        steps=[{"action": "Power on"}],
                    ),
                    Requirement(project_id=target.id, req_id="ABC-REQ-007", title="Existing"),
                ]
            )
            await db.commit()
            return source.id, target.id

    async def _copy_docs(self, doc_type, source_id, target_id, extra_ids):
        model = Requirement if doc_type == "REQ" else TestCase
        async with self.maker() as db:
            source, target = await db.get(Project, source_id), await db.get(Project, target_id)
            ids = list(
                (await db.scalars(select(model.id).where(model.project_id == source_id))).all()
            )
            result = ImportResult(imported=0, skipped=0, new_ids=[], errors=[])
            admin = User(email="admin@test.local", full_name="Ada Admin", role=UserRole.admin)
            await _import_docs(db, admin, doc_type, ids + extra_ids, source, target, result)
            await db.commit()
            return result

    async def _seed_import_case(self):
        async with self.maker() as db:
            project = Project(name="Demo", prefix="PRJ")
            admin = User(
                email="admin@test.local",
                full_name="Ada Admin",
                hashed_password="x",
                role=UserRole.admin,
            )
            db.add_all([project, admin])
            await db.flush()
            db.add(
                TestCase(
                    project_id=project.id, tc_id="PRJ-TC-001", title="Verify login", status="Draft"
                )
            )
            await db.commit()
            return project.id

    async def _import_test_cases(self, project_id, file_format, content):
        async with self.maker() as db:
            admin = (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()
            upload = UploadFile(file=io.BytesIO(content.encode()))
            result = await import_test_cases_file(
                project_id=project_id, format=file_format, file=upload, db=db, current_user=admin
            )
            await db.commit()
            return result

    def bloom_actions_for_rule(self, resource, *flags, **named):
        return set(actions_for_rule(resource, *flags, **named))

    def bloom_actions_on(self, matrix, resource):
        return actions_on(matrix, resource)

    def bloom_rule_of(self, actions):
        return rule_of(actions)

    def bloom_review_rule_roundtrip(self):
        policy = Policy(name="Review only", scope="document", permissions={}, type_tags={})
        _apply_rules(policy, {"REQ": PolicyRule(review=True, visibility=["customer"])})
        stored = (dict(policy.permissions), dict(policy.type_tags))
        shown = policy_rules(policy)["REQ"]
        _apply_rules(policy, {"REQ": shown})
        flags = (shown.review, shown.read, shown.write, shown.approve, shown.delete)
        return stored, flags, dict(policy.permissions)

    def bloom_validate_rule(self, resource, scope=None, **rule):
        try:
            if scope is None:
                self._run(_validate_rules(None, {resource: PolicyRule(**rule)}))
            else:
                self._run(_validate_rules(None, {resource: PolicyRule(**rule)}, scope))
        except HTTPException as refused:
            return refused.detail
        return None

    def bloom_permission_resources_of_documents(self):
        return list(DOC_TYPE_RESOURCES)

    def bloom_external_denied_actions(self):
        return set(EXTERNAL_DENIED_ACTIONS)

    def bloom_external_review_terms(self, permissions, type_tags):
        policy = Policy(
            name="Customer reviewer", scope="project", permissions=permissions, type_tags=type_tags
        )
        return [
            (term.permissions, term.customer_only, term.doc_types)
            for term in _policy_terms(policy, external=True)
        ]

    def bloom_editor_rows(self, specs):
        return [
            make_row(kind, description, expected, indent=indent)
            for kind, description, expected, indent in specs
        ]

    def bloom_rows_to_text(self, rows):
        return rows_to_text(rows)

    def bloom_text_to_rows(self, text):
        return text_to_rows(text)

    def bloom_row_fields(self, rows):
        return [
            (r["row_type"], r["label"], r["indent_level"], r["description"], r["expected_result"])
            for r in rows
        ]

    def bloom_step_case(self, **overrides):
        values = {
            "tc_id": "PRJ-TC-001",
            "title": "Boot within budget",
            "status": "Approved",
            "visibility": "internal",
            "preconditions": None,
            "steps": [],
            "description": "Measures the cold boot time.",
            "last_execution_status": None,
            "created_at": None,
            "updated_at": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def bloom_xml_reimport(self, cases):
        return _import_rows_from_xml(
            _test_cases_xml(SimpleNamespace(name="Demo", prefix="PRJ"), cases)
        )

    def bloom_markdown_reimport(self, cases):
        return parse_markdown_document(
            _test_cases_markdown(SimpleNamespace(name="Demo", prefix="PRJ"), cases)
        )

    def bloom_revision_sources(self):
        versions = ROOT / "alembic" / "versions"
        return {
            path.name: path.read_text()
            for path in sorted(versions.glob("*.py"))
            if path.name != "__init__.py"
        }

    def bloom_create_all_calls(self, source):
        found = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "create_all":
                    found.append(func.attr)
                elif isinstance(func, ast.Name) and func.id == "create_all":
                    found.append(func.id)
        return found

    def bloom_reconcile_attachments(self, files, referenced, old, grace_seconds, old_age_seconds):
        with self._temp_dir() as folder, contextlib.ExitStack() as stack:
            root = Path(folder)
            stack.enter_context(patch.object(settings, "ATTACHMENT_DIR", folder))
            stack.enter_context(patch.object(attachment_storage, "_ROOT", None))
            for name in files:
                (root / name).write_bytes(name.encode())
            stamp = time.time() - old_age_seconds
            os.utime(root / old, (stamp, stamp))
            session = self._reconcile_session(referenced)
            report = self._run(reconcile_attachments(session, orphan_grace_seconds=grace_seconds))
            kept = sorted(path.name for path in root.iterdir())
        return SimpleNamespace(report=report, kept=kept, committed=session.committed)

    def bloom_lifespan_reconcile_calls(self):
        calls, session = [], object()

        class SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, *_args):
                return None

        async def fake_reconcile(received):
            calls.append(received)
            return SimpleNamespace(leader_acquired=True, orphan_files=0, missing_files=0)

        async def start():
            async with main_module.lifespan(main_module.app):
                await asyncio.sleep(0)

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch.object(main_module.settings, "RUN_STARTUP_DATA_REPAIR", False)
            )
            stack.enter_context(patch.object(main_module.settings, "AUTO_SEED_ADMIN", False))
            stack.enter_context(patch.object(main_module, "async_session_maker", SessionContext))
            stack.enter_context(patch.object(main_module, "reconcile_attachments", fake_reconcile))
            self._run(start())
        return calls == [session], len(calls)

    def bloom_parse_markdown(self, text, default_type=None):
        if default_type is None:
            return parse_markdown_document(text)
        return parse_markdown_document(text, default_type=default_type)

    def bloom_parameter_collisions(self, names_and_values, existing):
        found = [Parameter(name, value) for name, value in names_and_values]
        return parameter_name_collisions(found, existing_names=existing)

    def _reconcile_session(self, referenced):
        class Scalars:
            def all(self):
                return referenced

        class Session:
            bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
            committed = False

            async def scalars(self, _statement):
                return Scalars()

            async def commit(self):
                Session.committed = True

        return Session()

    def bloom_read_repo_text(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def bloom_read_repo_lines_with(self, name, words):
        lines = self.bloom_read_repo_text(name).splitlines()
        return "\n".join(line for line in lines if any(word in line for word in words))

    def bloom_read_compose_service(self, service):
        compose = yaml.safe_load(self.bloom_read_repo_text(self.parameters.COMPOSE_FILE))
        return SimpleNamespace(service=compose["services"][service], volumes=compose["volumes"])

    def bloom_hash_token(self, token):
        return token_service.hash_token(token)

    def bloom_token_purpose_values(self):
        return {purpose.name: purpose.value for purpose in user_token.UserTokenPurpose}

    def bloom_new_invite_token(self, hours):
        token = user_token.UserToken(
            user_id=self.parameters.EXTERNAL_USER_ID,
            purpose=user_token.UserTokenPurpose.invite,
            token_hash=self.parameters.INVITE_TOKEN_HASH,
            expires_at=datetime.utcnow() + timedelta(hours=hours),
        )
        return SimpleNamespace(used_at=token.used_at, expires_at=token.expires_at)

    def bloom_external_doc_types(self, granted):
        user = self._external_user(granted)
        db = self._external_db(granted)
        project_id = self.parameters.EXTERNAL_PROJECT_ID
        return self._run(security.get_external_doc_types(db, user, project_id))

    def bloom_require_external_doc_type(self, granted, doc_type):
        user = self._external_user(granted)
        db = self._external_db(granted)
        project_id = self.parameters.EXTERNAL_PROJECT_ID
        try:
            self._run(security.require_external_doc_type_access(db, user, project_id, doc_type))
        except HTTPException as exc:
            return SimpleNamespace(status=exc.status_code, detail=exc.detail)
        return SimpleNamespace(status=None, detail="")

    def bloom_add_document(self, project_id, doc_id, doc_type, title):
        return self._run(
            self._add(
                Document(project_id=project_id, doc_id=doc_id, doc_type=doc_type, title=title)
            )
        )

    def bloom_normalize_document_kinds(self):
        from app import main

        with patch.object(main, "async_session_maker", self.maker):
            self._run(main.normalize_document_kinds_and_ids())

    def bloom_list_document_kinds(self):
        documents = self._run(self._all(select(Document).order_by(Document.id)))
        return [(document.doc_type, document.doc_id) for document in documents]

    def bloom_minute_utc(self, value):
        return artefact_utils.minute_utc(value)

    def bloom_resolve_execution_time_in_zone(self, executed, zone):
        previous = os.environ.get("TZ")
        os.environ["TZ"] = zone
        time.tzset()
        try:
            return campaigns._resolved_execution_time(executed)
        finally:
            if previous is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = previous
            time.tzset()

    def bloom_schema_fields(self, name):
        return list(getattr(schemas, name).model_fields)

    def bloom_build_schema(self, name, payload):
        model = getattr(schemas, name)
        body = dict(payload)
        for field_name, field in model.model_fields.items():
            if field.is_required() and field_name not in body:
                body[field_name] = (
                    self.parameters.RICH_TITLE
                    if field_name in self.parameters.RICH_TITLE_FIELDS
                    else self.parameters.RICH_FILLER
                )
        try:
            instance = model(**body)
        except ValidationError as exc:
            return SimpleNamespace(content_json=None, content_html=None, error=str(exc))
        return SimpleNamespace(
            content_json=getattr(instance, "content_json", None),
            content_html=getattr(instance, "content_html", None),
            error=None,
        )

    def bloom_read_repo_json(self, name):
        return json.loads(self.bloom_read_repo_text(name))

    def bloom_project_version(self):
        project = tomllib.loads(self.bloom_read_repo_text(self.parameters.PYPROJECT))
        return project["project"]["version"]

    def bloom_add_audit_event(self, action, age_days):
        occurred = datetime.utcnow() - timedelta(days=age_days)
        return self._run(
            self._add(AuditEvent(actor_type="user", action=action, occurred_at=occurred))
        )

    def bloom_prune_audit(self, older_than_days):
        with patch.object(audit, "async_session_maker", self.maker):
            return self._run(audit.prune(older_than_days))

    def bloom_list_audit_actions(self):
        return [event.action for event in self._run(self._all(select(AuditEvent)))]

    def bloom_response_models(self):
        seen = {}
        for package_name in self.parameters.RESPONSE_PACKAGES:
            package = importlib.import_module(package_name)
            for module_info in pkgutil.iter_modules(package.__path__):
                module = importlib.import_module(f"{package_name}.{module_info.name}")
                for name, cls in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(cls, BaseModel)
                        and cls.__module__ == module.__name__
                        and name.endswith(self.parameters.RESPONSE_SUFFIXES)
                    ):
                        seen[f"{cls.__module__}.{name}"] = cls
        return seen

    def bloom_unmarked_timestamps(self, models):
        unmarked = []
        for qualified, cls in models.items():
            serialized = set()
            for decorator in cls.__pydantic_decorators__.field_serializers.values():
                serialized |= set(decorator.info.fields)
            for field, info in cls.model_fields.items():
                if self._is_datetime(info.annotation) and field not in serialized:
                    unmarked.append(f"{qualified}.{field}")
        return unmarked

    def _temp_dir(self):
        return tempfile.TemporaryDirectory()

    def bloom_stream_attachment(self, payload, max_bytes, interrupt=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / self.parameters.STREAM_FILE
            upload = (
                self._interrupted_upload(payload, interrupt)
                if interrupt
                else UploadFile(file=io.BytesIO(payload))
            )
            outcome = SimpleNamespace(stored=None, status=None, error=None)
            with (
                patch.object(attachment_storage, "get_attachment_root", return_value=root),
                patch.object(attachment_storage, "CHUNK_BYTES", self.parameters.STREAM_CHUNK),
            ):
                try:
                    outcome.stored = self._run(
                        attachment_storage.write_stream(upload, target, max_bytes=max_bytes)
                    )
                except HTTPException as exc:
                    outcome.status = exc.status_code
                except (OSError, asyncio.CancelledError) as exc:
                    outcome.error = type(exc).__name__
            outcome.content = target.read_bytes() if target.exists() else None
            outcome.parts = sorted(path.name for path in root.glob("*.part"))
            outcome.files = sorted(path.name for path in root.iterdir())
            outcome.reads = getattr(upload, "reads", None)
            return outcome

    def bloom_apply_test_result(self, test_case, result):
        case = SimpleNamespace(**test_case)
        applied = campaigns._apply_result_to_test_case(case, SimpleNamespace(**result))
        return SimpleNamespace(applied=applied, case=case)

    def bloom_build_sync_request(self, tc_id, status, count):
        item = schemas.AutomatedResult(tc_id=tc_id, status=status)
        try:
            schemas.SyncResultsRequest(results=[item] * count)
        except ValidationError as exc:
            return type(exc).__name__
        return None

    def bloom_require_project_access(self, role, actions=None, permission=None):
        project_id = self.parameters.EXTERNAL_PROJECT_ID
        user = SimpleNamespace(id=self.parameters.EXTERNAL_USER_ID, role=UserRole(role))
        if actions is not None:
            term = security.AccessTerm(actions, None, None, frozenset(), False)
            user.access_map = {project_id: (term,)}
        db = AsyncMock()
        db.get.return_value = object()
        db.execute.return_value = SimpleNamespace(
            scalar_one_or_none=lambda: None,
            scalars=lambda: SimpleNamespace(all=lambda: []),
        )
        options = {"permission": permission} if permission else {}
        try:
            membership = self._run(security.require_project_access(db, user, project_id, **options))
        except HTTPException as exc:
            return SimpleNamespace(
                membership=None,
                status=exc.status_code,
                detail=exc.detail,
                lookups=db.get.await_count,
            )
        return SimpleNamespace(
            membership=membership, status=None, detail="", lookups=db.get.await_count
        )

    def bloom_role(self, name):
        return UserRole(name)

    def bloom_limit_imports(self, starts):
        self.patches.enter_context(patch.object(settings, "REQIF_IMPORTS_PER_15_MINUTES", starts))

    def bloom_begin_import(self, user_id, project_id):
        async def begin():
            async with self.maker() as db:
                try:
                    attempt = await import_attempts.begin_import_attempt(
                        db, user_id=user_id, project_id=project_id
                    )
                except HTTPException as exc:
                    retry = (exc.headers or {}).get("Retry-After")
                    return SimpleNamespace(id=None, status=exc.status_code, retry_after=retry)
                return SimpleNamespace(id=attempt.id, status=None, retry_after=None)

        return self._run(begin())

    def bloom_finish_import(self, attempt_id, outcome):
        async def finish():
            async with self.maker() as db:
                await import_attempts.finish_import_attempt(db, attempt_id, outcome)

        self._run(finish())

    def bloom_count_imports(self, user_id):
        return self._run(
            self._scalar(
                select(func.count(ImportAttempt.id)).where(ImportAttempt.user_id == user_id)
            )
        )

    def bloom_normalize_document_kind(self, value):
        return document_kinds.normalize_document_kind(value)

    def bloom_require_document_kind(self, value):
        try:
            return SimpleNamespace(
                kind=document_kinds.require_document_kind(value), status=None, detail=""
            )
        except HTTPException as exc:
            return SimpleNamespace(kind=None, status=exc.status_code, detail=exc.detail)

    def bloom_document_kind_from_slug(self, slug):
        try:
            return document_kinds.document_kind_from_slug(slug)
        except HTTPException as exc:
            return exc.status_code

    def bloom_count_links(self, project_id, type_code, incoming, outgoing):
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    SimpleNamespace(all=lambda: incoming),
                    SimpleNamespace(all=lambda: outgoing),
                ]
            )
        )
        row_ids = sorted({row[0] for row in incoming + outgoing})
        return self._run(
            docs_facade._count_links(
                db, project_id=project_id, type_code=type_code, row_ids=row_ids
            )
        )

    def bloom_try_schema(self, name, body):
        try:
            instance = getattr(schemas, name)(**body)
        except ValidationError as exc:
            return SimpleNamespace(instance=None, error=type(exc).__name__)
        return SimpleNamespace(instance=instance, error=None)

    def bloom_read_repo_lines(self, name):
        lines = self.bloom_read_repo_text(name).splitlines()
        return [line.strip() for line in lines if line.strip()]

    def bloom_read_repo_block(self, name, start, end):
        text = self.bloom_read_repo_text(name)
        first = text.find(start)
        last = text.find(end, first + 1) if first >= 0 else -1
        return text[first:last] if first >= 0 and last >= 0 else ""

    def bloom_role_baseline(self, instance_role, member_role):
        return permissions.role_baseline(instance_role, member_role)

    def bloom_has_permission(self, granted, action, resource):
        return permissions.has_permission(granted, action, resource)

    def bloom_merge_permissions(self, granted, *matrices):
        for matrix in matrices:
            permissions.merge(granted, matrix)
        return granted

    def bloom_transition_action(self, current, following):
        return permissions.transition_action(current, following)

    def bloom_invalid_permission_entries(self, matrix):
        return permissions.invalid_entries(matrix)

    def bloom_permissions_as_lists(self, granted):
        return permissions.as_lists(granted)

    def bloom_permission_resources(self):
        return list(permissions.RESOURCES)

    def bloom_link_rule(self, rule, *kinds):
        return getattr(link_rules, rule)(*kinds)

    def bloom_password_limits(self):
        return passwords.PASSWORD_MIN_LENGTH, passwords.PASSWORD_MAX_BYTES

    def bloom_check_password(self, value):
        try:
            return SimpleNamespace(value=passwords.validate_password_strength(value), error="")
        except ValueError as exc:
            return SimpleNamespace(value=None, error=str(exc))

    def bloom_try_auth_schema(self, name, body):
        try:
            instance = getattr(auth_schemas, name)(**body)
        except ValidationError as exc:
            return SimpleNamespace(instance=None, error=type(exc).__name__)
        return SimpleNamespace(instance=instance, error=None)

    def bloom_add_artefact(self, kind, **fields):
        models = {"REQ": Requirement, "TC": TestCase, "DEF": Defect}
        return self._run(self._add(models[kind](**fields)))

    def bloom_add_link(self, project_id, source, target, role):
        (source_type, source_id), (target_type, target_id) = source, target
        link = ArtefactLink(
            project_id=project_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            role=role,
        )
        return self._run(self._add(link))

    def bloom_lookup_artefact(self, artefact_type, reference, public_field):
        async def lookup(db, admin):
            try:
                row = await artefact_utils.get_artefact_or_404(db, artefact_type, reference, admin)
            except HTTPException as exc:
                return SimpleNamespace(status=exc.status_code, id=None, public_id=None)
            return SimpleNamespace(status=None, id=row.id, public_id=getattr(row, public_field))

        return self._run(self._as_first_admin(lookup))

    def bloom_related_artefacts(self, artefact_type, reference):
        async def related(db, admin):
            try:
                answer = await artefact_utils.build_related_response(
                    db, artefact_type, reference, admin
                )
            except HTTPException as exc:
                return exc.status_code
            return answer.model_dump()

        return self._run(self._as_first_admin(related))

    def bloom_update_project_variable(self, item_fields, update, duplicate=None):
        item = SimpleNamespace(**item_fields)
        found = [item, SimpleNamespace(**duplicate) if duplicate else None]
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    SimpleNamespace(scalar_one_or_none=lambda row=row: row) for row in found
                ]
            ),
            flush=AsyncMock(),
            refresh=AsyncMock(),
            get=AsyncMock(return_value=SimpleNamespace(id=item.project_id)),
        )
        admin = SimpleNamespace(role=UserRole.admin)
        outcome = SimpleNamespace(same_item=False, status=None, detail=None)
        try:
            response = self._run(
                project_variables_api.update_project_variable(
                    item_id=item.id, data=ProjectVariableUpdate(**update), db=db, current_user=admin
                )
            )
            outcome.same_item = response is item
        except HTTPException as exc:
            outcome.status, outcome.detail = exc.status_code, exc.detail
        refreshed = [call.args[0] is item for call in db.refresh.await_args_list]
        outcome.item = vars(item)
        outcome.flushes = db.flush.await_count
        outcome.refreshed_item = refreshed
        return outcome

    def bloom_nginx_locations(self, name):
        text = self.bloom_read_repo_text(name)
        blocks = []
        for match in re.finditer(r"^\s*(location[^\n{]*)\{", text, re.MULTILINE):
            start = index = match.end()
            depth = 1
            while index < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[index], 0)
                index += 1
            blocks.append((match.group(1).strip(), text[start : index - 1]))
        return blocks

    def bloom_nginx_server_head(self, name):
        text = self.bloom_read_repo_text(name)
        first = re.search(r"^\s*location[^\n{]*\{", text, re.MULTILINE)
        return text[: first.start()] if first else text

    def bloom_mention(self, kind, identifier):
        return {
            "type": "mention",
            "attrs": {"id": f"{kind}:{identifier}", "mentionSuggestionChar": "#"},
        }

    def bloom_sync_tag_links(self, project_id, source, source_id, content, hidden=False):
        async def sync(db, admin):
            try:
                with contextlib.ExitStack() as stack:
                    if hidden:
                        stack.enter_context(patch.object(tag_links, "link_end", self._hidden_end))
                    created = await tag_links.sync_tag_links(
                        db,
                        project_id=project_id,
                        source_type=source,
                        source_id=source_id,
                        content_json=content,
                        user=admin,
                    )
                await db.commit()
            except HTTPException as exc:
                await db.rollback()
                return SimpleNamespace(created=None, status=exc.status_code, detail=str(exc.detail))
            return SimpleNamespace(created=created, status=None, detail="")

        return self._run(self._as_first_admin(sync))

    def bloom_list_links(self):
        links = self._run(self._all(select(ArtefactLink).order_by(ArtefactLink.id)))
        return [(link.source_type, link.target_type, link.role) for link in links]

    async def _hidden_end(self, *args, **kwargs):
        return None, False

    def bloom_plain_text(self, content_json, content_html):
        return rich_text.plain_text(content_json, content_html)

    def bloom_description_with_content(self, description, content_json, content_html):
        return rich_text.description_with_content(description, content_json, content_html)

    def bloom_import_reqif(self, project_id, data):
        stream = io.BytesIO(data)

        async def read(size=-1):
            return stream.read(size)

        async def run(db, admin):
            return await import_service.import_reqif(
                project_id=project_id,
                file=SimpleNamespace(read=read),
                db=db,
                current_user=admin,
            )

        return self._run(self._as_first_admin(run))

    def bloom_copy_requirements(self, source_id, target_id):
        async def copy(db, admin):
            source = await db.get(Project, source_id)
            target = await db.get(Project, target_id)
            ids = list(
                await db.scalars(select(Requirement.id).where(Requirement.project_id == source_id))
            )
            result = import_service.ImportResult(imported=0, skipped=0, new_ids=[], errors=[])
            await import_service._import_docs(db, admin, "REQ", ids, source, target, result)
            await db.commit()
            return result

        return self._run(self._as_first_admin(copy))

    def bloom_requirement_rows(self, fields, project_id=None):
        query = select(Requirement).order_by(Requirement.req_id)
        if project_id is not None:
            query = query.where(Requirement.project_id == project_id)
        rows = self._run(self._all(query))
        return [tuple(getattr(row, name) for name in fields) for row in rows]

    def bloom_list_link_ends(self):
        links = self._run(self._all(select(ArtefactLink).order_by(ArtefactLink.id)))
        return [
            (link.source_id, link.target_id, link.source_type, link.target_type, link.role)
            for link in links
        ]

    def bloom_count_requirement_links(self):
        return len(self._run(self._all(select(RequirementLink))))

    def bloom_set_logo(self, data, content_type):
        async def upload(db, admin):
            file = UploadFile(
                io.BytesIO(data),
                filename=self.parameters.LOGO_FILE,
                headers=Headers({"content-type": content_type}),
            )
            try:
                answer = await company_logo.set_company_logo(file=file, db=db, current_user=admin)
            except HTTPException as exc:
                return SimpleNamespace(status=exc.status_code, content_type=None, size=None)
            await db.commit()
            return SimpleNamespace(status=None, **answer)

        return self._run(self._as_first_admin(upload))

    def bloom_get_logo(self):
        async def read(db, admin):
            try:
                answer = await company_logo.get_company_logo(db=db, current_user=admin)
            except HTTPException as exc:
                return SimpleNamespace(status=exc.status_code, body=None, media_type=None)
            return SimpleNamespace(status=None, body=answer.body, media_type=answer.media_type)

        return self._run(self._as_first_admin(read))

    def bloom_delete_logo(self):
        async def remove(db, admin):
            await company_logo.delete_company_logo(db=db, current_user=admin)
            await db.commit()

        self._run(self._as_first_admin(remove))

    def bloom_report_logo(self):
        async def load(db, admin):
            return await export._load_report_logo(db)

        return self._run(self._as_first_admin(load))

    def bloom_requirements_pdf(self, logo):
        project = self._run(self._all(select(Project)))[0]
        requirements = self._run(self._all(select(Requirement)))
        return export._requirements_pdf(project, list(requirements), logo)

    def bloom_forge_token(self, user_id, algorithm, minutes):
        user = self._run(self._get(User, user_id))
        expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        claims = {
            "sub": str(user.id),
            "type": "user",
            "ver": user.session_version,
            "exp": int(expires.timestamp()),
        }
        signing_input = f"{self._token_part({'alg': algorithm, 'typ': 'JWT'})}."
        signing_input += self._token_part(claims)
        hashes = {"HS256": hashlib.sha256, "HS512": hashlib.sha512}
        if algorithm not in hashes:
            return f"{signing_input}."
        digest = hmac.new(
            settings.SECRET_KEY.encode(), signing_input.encode(), hashes[algorithm]
        ).digest()
        return f"{signing_input}.{base64.urlsafe_b64encode(digest).rstrip(b'=').decode()}"

    def bloom_issue_token(self, user_id):
        user = self._run(self._get(User, user_id))
        return create_access_token(
            {"sub": str(user.id), "type": "user", "ver": user.session_version}
        )

    def bloom_sign_in_with_token(self, token):
        return self._run(self._sign_in_with_token(token))

    def bloom_issue_untyped_token(self, user_id):
        return create_access_token({"sub": str(user_id)})

    def bloom_create_service_credential(self, user_id, name):
        return self._run(self._create_service_credential(user_id, name))

    def bloom_authenticate_service_token(self, raw):
        return self._run(self._authenticate_service_token(raw))

    def bloom_revoke_service_credential(self, credential_id):
        self._run(self._revoke_service_credential(credential_id))

    def bloom_expire_service_credential(self, credential_id):
        self._run(self._expire_service_credential(credential_id))

    def bloom_run_smoke_script_with_fake_docker(self, image):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "docker-argv.jsonl"
            docker = Path(folder) / "docker"
            docker.write_text(self._fake_docker(), encoding="utf-8")
            docker.chmod(0o755)
            env = {**os.environ, "DOCKER_ARGV_LOG": str(log)}
            env["PATH"] = f"{folder}{os.pathsep}{env['PATH']}"
            subprocess.run(
                ["bash", str(ROOT / self.parameters.SMOKE_SCRIPT), image],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            if not log.exists():
                return []
            return [json.loads(line) for line in log.read_text().splitlines()]

    def bloom_read_smoke_project_payload(self):
        script = (ROOT / self.parameters.SMOKE_SCRIPT).read_text(encoding="utf-8")
        match = re.search(self.parameters.SMOKE_PAYLOAD_PATTERN, script)
        return json.loads(match.group(1)) if match else None

    def bloom_validate_project_payload(self, payload):
        try:
            return ProjectCreate.model_validate(payload).prefix, None
        except ValidationError as exc:
            return None, str(exc)

    def bloom_count_lifespan_starts(self, minutes):
        from app import main

        started = []

        async def loop():
            started.append(True)
            await asyncio.Event().wait()

        async def reconcile(session):
            return SimpleNamespace(leader_acquired=False)

        async def cycle():
            async with main.lifespan(main.app):
                await asyncio.sleep(0)

        with (
            patch.object(main.settings, "INTEGRATION_SYNC_MINUTES", minutes),
            patch.object(main.settings, "RUN_STARTUP_DATA_REPAIR", False),
            patch.object(main.settings, "AUTO_SEED_ADMIN", False),
            patch.object(main.integration_sync, "sync_loop", loop),
            patch.object(main, "reconcile_attachments", reconcile),
        ):
            self._run(cycle())
        return len(started)

    def _fake_docker(self):
        return (
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['DOCKER_ARGV_LOG'], 'a', encoding='utf-8') as log:\n"
            "    log.write(json.dumps(args) + '\\n')\n"
            "if 'current' in args:\n"
            f"    print('{self.parameters.SMOKE_ALEMBIC_HEAD} (head)')\n"
            "    sys.exit(0)\n"
            "if args and args[0] == 'run' and '--name' in args:\n"
            "    name = args[args.index('--name') + 1]\n"
            f"    if name.startswith('{self.parameters.SMOKE_APP_CONTAINER}'):\n"
            f"        sys.exit({self.parameters.SMOKE_STOP_CODE})\n"
        )

    def _external_user(self, granted):
        term = security.AccessTerm(
            {"*": {"view"}},
            frozenset(granted),
            frozenset(self.parameters.EXTERNAL_VISIBILITY),
            frozenset(),
            True,
        )
        return SimpleNamespace(
            id=self.parameters.EXTERNAL_USER_ID,
            role=UserRole.external,
            access_map={self.parameters.EXTERNAL_PROJECT_ID: (term,)},
        )

    def _external_db(self, granted):
        membership = SimpleNamespace(id=self.parameters.EXTERNAL_MEMBERSHIP_ID, role="external")
        rows = SimpleNamespace(all=lambda: list(granted))
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: membership),
            SimpleNamespace(scalars=lambda: rows),
        ]
        return db

    def _is_datetime(self, annotation):
        if annotation is datetime:
            return True
        return any(self._is_datetime(arg) for arg in typing.get_args(annotation))

    async def _as_first_admin(self, call):
        async with self.maker() as db:
            admin = await db.scalar(select(User).where(User.role == UserRole.admin))
            return await call(db, admin)

    def _interrupted_upload(self, first_chunk, error):
        upload = SimpleNamespace(reads=0)

        async def read(size):
            upload.reads += 1
            if upload.reads > 1:
                raise error()
            return first_chunk

        upload.read = read
        return upload

    def _token_part(self, value):
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    async def _create_service_credential(self, user_id, name):
        async with self.maker() as db:
            credential, raw = await create_service_credential(
                db, created_by_user_id=user_id, name=name
            )
            await db.commit()
            return SimpleNamespace(
                id=credential.id,
                scope=credential.scope,
                token_hash=credential.token_hash,
                expires_at=credential.expires_at,
                deadline=datetime.utcnow() + self.parameters.SERVICE_LIFETIME,
                raw=raw,
            )

    async def _authenticate_service_token(self, raw):
        async with self.maker() as db:
            try:
                return (await require_bud_sync_token(token=raw, db=db)).id, None
            except HTTPException as exc:
                return None, exc.status_code

    async def _revoke_service_credential(self, credential_id):
        async with self.maker() as db:
            await revoke_service_credential(db, credential_id)
            await db.commit()

    async def _expire_service_credential(self, credential_id):
        async with self.maker() as db:
            credential = await db.get(ServiceCredential, credential_id)
            credential.expires_at = datetime.utcnow() - timedelta(seconds=1)
            await db.commit()

    async def _sign_in_with_token(self, token):
        async with self.maker() as db:
            try:
                return (await get_current_user(token=token, db=db)).id, None
            except HTTPException as exc:
                return None, exc.status_code

    def _after_each_search(self, action):
        original = integration_sync._fetch_jira

        async def fetch(setting, **kw):
            fetched = await original(setting, **kw)
            await action(setting)
            return fetched

        self.patches.enter_context(patch.object(integration_sync, "_fetch_jira", fetch))
