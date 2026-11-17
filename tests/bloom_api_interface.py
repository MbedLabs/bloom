"""
* @file     ${tests/bloom_api_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's API tests: the routes served in-process over in-memory SQLite.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Requests go through an ASGI transport; no server is started.
"""

import base64
import contextlib
import csv
import gzip
import hashlib
import hmac
import io
import json
import logging
import re
from datetime import datetime, timedelta
from logging.handlers import BufferingHandler
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from pydantic import ValidationError
from slowapi.util import get_remote_address
from sqlalchemy import event, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import tests.parameters as params
from app import main
from app.api import access_requests as access_requests_api
from app.api import defects as defects_api
from app.api import integrations
from app.api import setup as setup_api
from app.core import id_generator
from app.core.cache import dashboard_stats_cache
from app.core.config import Settings, settings
from app.core.database import get_db
from app.core.deps import limiter, rate_limit_key
from app.core.observability import CREATED_BODY_LIMIT, CreatedBody, client_address
from app.core.permissions import DOC_TYPE_RESOURCES
from app.core.security import create_access_token
from app.core.service_auth import require_bud_sync_token
from app.models import (
    ArtefactActivity,
    ArtefactComment,
    ArtefactLink,
    AuditEvent,
    Baseline,
    CampaignSuite,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    IntegrationSetting,
    Notification,
    Project,
    ProjectVariable,
    Requirement,
    RiskItem,
    TestCampaign,
    TestCampaignItem,
)
from app.models import TestCase as TestCaseModel
from app.models import TestConcept
from app.models import TestSuite as TestSuiteModel
from app.models import TestSuiteItem as TestSuiteItemModel
from app.models.cli_auth_session import CliAuthSession
from app.models.groups import Group, GroupMembership, Policy, user_application_policies
from app.models.project_membership import ProjectAccess
from app.models.user import User, UserRole
from app.models.user_token import UserToken, UserTokenPurpose
from app.schemas.cli_auth import CliStartRequest
from app.schemas.memberships import DEFAULT_EXTERNAL_DOC_TYPES
from app.services import audit as audit_service
from app.services import cli_auth
from app.services.audit import request_outcome, route_template
from app.services.integration_secrets import (
    ENVELOPE_PREFIX,
    decrypt_integration_secret,
    encrypt_integration_secret,
    is_encrypted,
)
from app.services.mail_service import MailConfigurationError
from tests.access_fixtures import (
    allow_doc_types,
    project_access_fixture,
    scenario_rules,
    scenario_type_tags,
)
from tests.bloom_interface import BloomInterface

REAL_CLIENT = httpx.AsyncClient


class BloomApiInterface(BloomInterface):

    def bloom_start_api(self):
        app = FastAPI()
        app.include_router(integrations.router, prefix=self.parameters.INTEGRATIONS_PREFIX)

        async def database():
            async with self.maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = database
        self.api = app

    def bloom_create_webhook_integration(self, project_id, **fields):
        return self.bloom_create_integration(
            project_id,
            webhook_secret=encrypt_integration_secret(self.parameters.WEBHOOK_SECRET),
            **fields,
        )

    def bloom_create_webhook_environment(self, change_status=None, **setting_fields):
        project_id = self.bloom_create_project()
        fields = {"jira_project_key": None, **setting_fields}
        setting_id = self.bloom_create_webhook_integration(project_id, **fields)
        defect_id = self.bloom_link_defect(
            project_id, "jira", self.parameters.JIRA_PROJECT, self.parameters.LINKED_NUMBER
        )
        change_id = self.bloom_link_change(
            project_id,
            "jira",
            self.parameters.JIRA_PROJECT,
            self.parameters.CHANGE_NUMBER,
            change_status or self.parameters.CHANGE_SUBMITTED,
        )
        self.bloom_start_api()
        return SimpleNamespace(
            project_id=project_id, setting_id=setting_id, defect_id=defect_id, change_id=change_id
        )

    def bloom_jira_webhook_body(self, issue_key, event=None, **fields):
        issue_fields = {
            "summary": self.parameters.WEBHOOK_SUMMARY,
            "issuetype": {"name": self.parameters.BUG},
            "status": {
                "name": self.parameters.JIRA_DONE,
                "statusCategory": {"key": self.parameters.JIRA_DONE_CATEGORY},
            },
        }
        issue_fields.update(fields)
        payload = {
            "webhookEvent": event or self.parameters.ISSUE_UPDATED,
            "issue": {"key": issue_key, "fields": issue_fields},
        }
        return json.dumps(payload).encode()

    def bloom_jira_event_body(self, event):
        return json.dumps({"webhookEvent": event}).encode()

    def bloom_sign(self, body):
        digest = hmac.new(self.parameters.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return f"{self.parameters.SIGNATURE_PREFIX}{digest}"

    def bloom_post_jira_webhook(self, body, signature=None, delivery=None, signed=True):
        headers = {"Content-Type": "application/json"}
        if signed:
            headers["X-Hub-Signature"] = (
                signature if signature is not None else self.bloom_sign(body)
            )
        if delivery is not None:
            headers["X-Atlassian-Webhook-Identifier"] = delivery
        return self._run(self._post(self.parameters.WEBHOOK_PATH, body, headers))

    def bloom_github_issue_body(self, number, repo):
        payload = {
            "action": "closed",
            "issue": {"number": number, "state": "closed"},
            "repository": {"full_name": repo},
        }
        return json.dumps(payload).encode()

    def bloom_oversized_webhook_body(self):
        return b"{" + b"x" * self.parameters.HOOK_OVERSIZED_BYTES

    def bloom_post_github_webhook(self, body, signature=None, delivery=None):
        headers = {"X-GitHub-Event": "issues", "Content-Type": "application/json"}
        if signature is not None:
            headers["X-Hub-Signature-256"] = signature
        if delivery is not None:
            headers["X-GitHub-Delivery"] = delivery
        return self._answer(self._run(self._post(self.parameters.HOOK_GITHUB_PATH, body, headers)))

    def bloom_post_gitlab_webhook(self, number, repo, token=None, delivery=None):
        payload = {
            "object_attributes": {"iid": number, "state": "closed", "action": "close"},
            "project": {"path_with_namespace": repo},
        }
        headers = {"X-Gitlab-Event": "Issue Hook", "Content-Type": "application/json"}
        if token is not None:
            headers["X-Gitlab-Token"] = token
        if delivery is not None:
            headers["X-Gitlab-Event-UUID"] = delivery
        body = json.dumps(payload).encode()
        return self._answer(self._run(self._post(self.parameters.HOOK_GITLAB_PATH, body, headers)))

    def bloom_encrypt_secret(self, secret, key=None):
        return self._with_key(key, encrypt_integration_secret, secret)

    def bloom_decrypt_secret(self, envelope, key=None):
        return self._with_key(key, decrypt_integration_secret, envelope)

    def bloom_is_encrypted(self, value):
        return is_encrypted(value)

    def bloom_envelope_prefix(self):
        return ENVELOPE_PREFIX

    def bloom_new_encryption_key(self):
        return Fernet.generate_key().decode()

    def bloom_api_create_setting(self, headers, project_id, tracker, token, webhook_secret):
        body = {
            "project_id": project_id,
            "tracker": tracker,
            "token": token,
            "webhook_secret": webhook_secret,
            "enabled": True,
        }
        return self.bloom_api_call("POST", "/api/integrations/settings", headers, json=body)

    def bloom_api_rotate_setting_token(self, headers, setting_id, token):
        path = f"/api/integrations/settings/{setting_id}"
        return self.bloom_api_call("PATCH", path, headers, json={"token": token})

    def bloom_read_setting_secrets(self, setting_id):
        setting = self._run(self._get(IntegrationSetting, setting_id))
        return setting.token_encrypted, setting.webhook_secret

    def bloom_set_defect_status(self, defect_id, status):
        self._run(self._update(Defect, defect_id, status=status))

    def bloom_update_setting(self, setting_id, **fields):
        self._run(self._update(IntegrationSetting, setting_id, **fields))

    def bloom_add_test_case(self, project_id, tc_id, title, **fields):
        return self._run(
            self._add(TestCaseModel(project_id=project_id, tc_id=tc_id, title=title, **fields))
        )

    def bloom_log_sync_event(self, target, target_id, event_type):
        async def log():
            async with self.maker() as db:
                integrations._log_target_sync_event(
                    db, target, target_id, "inbound", "jira", event_type
                )
                await db.commit()

        self._run(log())

    def bloom_record_pushes(self):
        pushed = []

        async def push(target, setting, changed):
            pushed.append(target.id)

        self.patches.enter_context(patch.object(integrations, "_push_to_jira", push))
        return pushed

    def bloom_push_edits(self, defect_id, change_id, changes):
        async def edit():
            async with self.maker() as db:
                defect = await db.get(Defect, defect_id)
                change = await db.get(ChangeRequest, change_id)
                await integrations.sync_defect_to_tracker(db, defect, changes)
                await integrations.sync_change_request_to_tracker(db, change, changes)

        self._run(edit())

    def bloom_serve_jira_pages(self, pages):
        seen = []

        def answer(request):
            if request.url.path.endswith(self.parameters.JIRA_MYSELF):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                )
            if request.method == "GET":
                return httpx.Response(self.parameters.STATUS_OK, json={"fields": {}})
            seen.append(json.loads(request.content))
            if len(seen) > len(pages):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": [], "isLast": True}
                )
            return httpx.Response(self.parameters.STATUS_OK, json=pages[len(seen) - 1])

        self.bloom_serve(answer)
        return seen

    def bloom_serve_atlassian_gateway(self, cloud_id, issues):
        gateway = f"{self.parameters.ATLASSIAN_GATEWAY}/{cloud_id}/"

        def answer(request):
            url = str(request.url)
            if url.endswith(self.parameters.TENANT_INFO):
                return httpx.Response(self.parameters.STATUS_OK, json={"cloudId": cloud_id})
            if url.startswith(gateway):
                if request.url.path.endswith(self.parameters.JIRA_MYSELF):
                    return httpx.Response(
                        self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                    )
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": list(issues), "isLast": True}
                )
            return httpx.Response(self.parameters.STATUS_UNAUTHORIZED)

        self.bloom_serve(answer)

    def bloom_try_sync_now(self, setting_id, admin_email):
        try:
            return self.bloom_sync_now(setting_id, admin_email), None
        except HTTPException as exc:
            return None, (exc.status_code, exc.detail)

    def bloom_try_validate_jira_filter(self, issue_types, priority_map):
        try:
            integrations._validate_jira_filter(issue_types, priority_map)
        except HTTPException as exc:
            return exc.status_code, exc.detail
        return None

    def bloom_link_defect_before_reserving(self, project_id, number, title):
        original = integrations._reserve_webhook_delivery

        async def reserve(db, setting, tracker, delivery_id):
            await self._link_defect(
                project_id, "jira", self.parameters.JIRA_PROJECT, number, {"title": title}
            )
            return await original(db, setting, tracker, delivery_id)

        self.patches.enter_context(patch.object(integrations, "_reserve_webhook_delivery", reserve))

    def bloom_api_verify(self, headers, project_id, test_case_id, requirement_id):
        body = {
            "project_id": project_id,
            "source_type": "TC",
            "source_id": test_case_id,
            "target_type": "REQ",
            "target_id": requirement_id,
            "role": "verifies",
        }
        return self.bloom_api_call("POST", "/api/links", headers, json=body)

    def bloom_api_approve_test_case(self, headers, test_case_id):
        path = f"/api/artefacts/test-case/{test_case_id}"
        actor = self.bloom_api_call("GET", path + "/workflow", headers).body["creator"]["id"]
        self.bloom_api_call(
            "PUT", path + "/workflow/assignees", headers, json={"reviewer_id": actor}
        )
        self.bloom_api_call("POST", path + "/requests", headers, json={"kind": "review"})
        comment = {"body": "Reviewed the requested test case."}
        self.bloom_api_call("POST", path + "/comments", headers, json=comment)
        self.bloom_api_call("POST", path + "/requests", headers, json={"kind": "approval"})
        signed = self.bloom_api_call("POST", path + "/sign-off", headers, json={"step": "approve"})
        return actor, signed

    def bloom_api_add_tracked_defect(self, headers, prefix):
        project = self.bloom_api_new_project(headers, prefix)
        body = {
            "project_id": project["id"],
            "title": f"Defect {prefix}",
            "external_tracker": "github",
            "external_repo_full_name": "MbedLabs/bloom",
            "external_issue_number": 7,
            "external_issue_url": "https://github.com/MbedLabs/bloom/issues/7",
        }
        return self.bloom_api_call("POST", "/api/defects", headers, json=body).body

    def bloom_api_refresh_defect_while_tracker_fails(self, headers, defect_id, failure):
        refusal = httpx.HTTPStatusError(
            "401",
            request=httpx.Request("GET", "https://api.github.com"),
            response=httpx.Response(401),
        )
        failures = {
            "no route": httpx.ConnectError("no route to host"),
            "no route to an address": httpx.ConnectError("no route to host 10.0.0.5"),
            "read timeout": httpx.ReadTimeout("timed out"),
            "connect timeout": httpx.ConnectTimeout("timed out"),
            "unreadable answer": ValueError("not json"),
            "refusal": refusal,
        }

        async def fail(*args, **kwargs):
            raise failures[failure]

        path, body = f"/api/defects/{defect_id}/refresh-external", {
            "token": "a-token-the-test-never-uses"
        }
        with patch.object(defects_api, "_fetch_github_issue", fail):
            answer = self._run(self._request("POST", path, headers, json=body))
        return SimpleNamespace(status=answer.status_code, body=answer.json(), text=answer.text)

    def bloom_api_setup(self, body, mail="recorded"):
        sent = {}

        def record(**fields):
            if mail == "unavailable":
                raise MailConfigurationError("SMTP is disabled")
            sent.update(fields)

        with patch.object(setup_api, "send_admin_welcome_email", record):
            answer = self.bloom_api_call("POST", "/api/setup", json=body)
        return answer, sent

    def bloom_list_accounts(self):
        rows = self._run(self._all(select(User).order_by(User.id)))
        return [(row.email, row.role.value, row.is_active, row.hashed_password) for row in rows]

    def bloom_start_api_with_admin(self):
        self.bloom_start_full_api()
        self.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        headers, _ = self.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        return headers

    def bloom_api_new_project(self, headers, prefix, **fields):
        body = {"name": f"Project {prefix}", "prefix": prefix, **fields}
        return self.bloom_api_call("POST", "/api/projects", headers, json=body).body

    def bloom_api_add_requirements(self, headers, project_id, count):
        for number in range(count):
            self.bloom_api_call(
                "POST",
                "/api/requirements",
                headers,
                json={"project_id": project_id, "title": f"Req {number}"},
            )

    def bloom_api_add_test_case(self, headers, project_id, title, **fields):
        body = {"project_id": project_id, "title": title, **fields}
        return self.bloom_api_call("POST", "/api/test-cases", headers, json=body)

    def bloom_api_add_suite(self, headers, project_id, name, cases):
        body = {
            "project_id": project_id,
            "name": name,
            "test_case_ids": [case["id"] for case in cases],
        }
        return self.bloom_api_call("POST", "/api/test-suites", headers, json=body).body

    def bloom_api_add_campaign_with_one_case(self, headers, prefix):
        project = self.bloom_api_new_project(headers, prefix)
        case = self.bloom_api_add_test_case(headers, project["id"], f"Case {prefix}").body
        body = {
            "project_id": project["id"],
            "name": f"Campaign {prefix}",
            "test_case_ids": [case["id"]],
        }
        campaign = self.bloom_api_call("POST", "/api/campaigns", headers, json=body).body
        return SimpleNamespace(project=project, case=case, campaign=campaign)

    def bloom_api_count_statements(self, method, path, headers):
        skipped = ("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT", "BEGIN", "COMMIT")
        counted = []

        def record(conn, cursor, statement, parameters, context, executemany):
            if not statement.strip().upper().startswith(skipped):
                counted.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", record)
        try:
            answer = self.bloom_api_call(method, path, headers)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", record)
        return answer, len(counted)

    def bloom_start_full_api(self):
        self.patches.enter_context(patch.dict(main.app.dependency_overrides))
        main.app.dependency_overrides[get_db] = self._serve_session
        self.patches.enter_context(patch.object(limiter, "enabled", False))
        self.api = main.app

    def bloom_create_external_reader_environment(self, doc_types=()):
        values = self.parameters
        self.bloom_start_full_api()
        project_id = self.bloom_create_project(values.VISIBILITY_PREFIX)
        user_id = self.bloom_add_account(
            values.EXTERNAL_EMAIL, values.API_PASSWORD, values.EXTERNAL_ROLE
        )
        self.bloom_add_external_member(
            project_id,
            user_id,
            values.EXTERNAL_PERMISSIONS,
            values.CUSTOMER_VISIBILITY,
            doc_types,
        )
        headers, _ = self.bloom_log_in(values.EXTERNAL_EMAIL, values.API_PASSWORD)
        return SimpleNamespace(project_id=project_id, user_id=user_id, headers=headers)

    def bloom_default_external_doc_types(self):
        return sorted(DEFAULT_EXTERNAL_DOC_TYPES)

    def bloom_add_baseline(self, project_id, baseline_id, name, snapshot):
        return self._run(
            self._add(
                Baseline(
                    project_id=project_id,
                    baseline_id=baseline_id,
                    name=name,
                    baseline_type="Milestone",
                    snapshot=snapshot,
                )
            )
        )

    def bloom_add_requirement(self, project_id, req_id, visibility):
        return self._run(
            self._add(
                Requirement(
                    project_id=project_id,
                    req_id=req_id,
                    title=req_id,
                    status=self.parameters.DOCUMENT_STATUS,
                    visibility=visibility,
                )
            )
        )

    def bloom_add_project_variable(self, project_id, key, value):
        return self._run(
            self._add(
                ProjectVariable(project_id=project_id, kind="parameter", key=key, value=value)
            )
        )

    def bloom_add_comment(self, kind, artefact_id, body):
        return self._run(
            self._add(
                ArtefactComment(
                    artefact_type=kind, artefact_id=artefact_id, author_name="System", body=body
                )
            )
        )

    def bloom_add_activity(self, kind, artefact_id, summary):
        return self._run(
            self._add(
                ArtefactActivity(
                    artefact_type=kind,
                    artefact_id=artefact_id,
                    event_type="created",
                    summary=summary,
                )
            )
        )

    def bloom_add_artefact_link(self, project_id, source_id, target_id):
        source_type, target_type, role = self.parameters.READER_LINK
        return self._run(
            self._add(
                ArtefactLink(
                    project_id=project_id,
                    source_type=source_type,
                    source_id=source_id,
                    target_type=target_type,
                    target_id=target_id,
                    role=role,
                )
            )
        )

    def bloom_api_list_test_cases(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/test-cases", headers, params=query)

    def bloom_api_get_test_case(self, headers, test_case_id):
        return self.bloom_api_call("GET", f"/api/test-cases/{test_case_id}", headers)

    def bloom_api_comments(self, headers, kind, artefact_id):
        return self.bloom_api_call("GET", f"/api/artefacts/{kind}/{artefact_id}/comments", headers)

    def bloom_api_activity(self, headers, kind, artefact_id):
        return self.bloom_api_call("GET", f"/api/artefacts/{kind}/{artefact_id}/activity", headers)

    def bloom_api_list_links(self, headers, project_id):
        return self.bloom_api_call("GET", "/api/links", headers, params={"project_id": project_id})

    def bloom_api_list_projects(self, headers):
        return self.bloom_api_call("GET", "/api/projects", headers)

    def bloom_api_list_requirements(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/requirements", headers, params=query)

    def bloom_api_read_requirement(self, headers, requirement_id):
        return self.bloom_api_call("GET", f"/api/requirements/{requirement_id}", headers)

    def bloom_api_traceability(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/traceability", headers, params=query)

    def bloom_api_dashboard_stats(self, headers):
        dashboard_stats_cache._store.clear()
        return self.bloom_api_call("GET", "/api/dashboard/stats", headers)

    def bloom_api_import_from(self, headers, project_id, source_project_id, doc_type, doc_ids):
        body = {
            "source_project_id": source_project_id,
            "doc_type": doc_type,
            "doc_ids": doc_ids,
            "include_links": True,
        }
        return self.bloom_api_call("POST", f"/api/projects/{project_id}/import", headers, json=body)

    def bloom_api_upload_reqif(self, headers, project_id, content):
        files = {"file": ("requirements.reqif", content, "application/xml")}
        path = f"/api/projects/{project_id}/import/reqif"
        return self._answer(self._run(self._upload(path, headers, files)))

    def bloom_create_export_project(self):
        values = self.parameters
        project = self.bloom_create_project(values.EXPORT_PREFIX)
        shown, hidden = values.CUSTOMER_VISIBILITY, values.INTERNAL_VISIBILITY
        pairs = (
            (values.EXPORT_SHOWN_REQ, values.EXPORT_SHOWN_TC, values.EXPORT_SHOWN_TITLE, shown),
            (values.EXPORT_HIDDEN_REQ, values.EXPORT_HIDDEN_TC, values.EXPORT_HIDDEN_TITLE, hidden),
        )
        for req_id, tc_id, title, visibility in pairs:
            requirement = self._run(
                self._add(
                    Requirement(
                        project_id=project, req_id=req_id, title=title, visibility=visibility
                    )
                )
            )
            fields = {"last_execution_status": values.EXPORT_PASSED} if visibility == shown else {}
            test_case = self.bloom_add_test_case(
                project, tc_id, title, visibility=visibility, **fields
            )
            self.bloom_add_artefact_link(project, test_case, requirement)
        return project

    def bloom_add_group_exporter(self, project_id, email, permissions):
        user_id = self.bloom_add_account(
            email, self.parameters.API_PASSWORD, self.parameters.EXTERNAL_ROLE
        )
        self._run(self._add_group_exporter(project_id, user_id, email, permissions))
        return user_id

    def bloom_api_export(self, headers, project_id, kind, pdf=False):
        path = f"/api/projects/{project_id}/export/{kind}"
        query = {"format": "pdf"} if pdf and kind != self.parameters.EXPORT_DOSSIER else None
        answer = self._run(self._request("GET", path, headers, params=query))
        is_pdf = answer.content.startswith(b"%PDF")
        return SimpleNamespace(
            status=answer.status_code,
            content_type=answer.headers.get("content-type"),
            is_pdf=is_pdf,
            text="" if is_pdf else answer.text,
            rows=[] if is_pdf else list(csv.DictReader(io.StringIO(answer.text))),
        )

    def bloom_list_audit_details(self, action):
        query = select(AuditEvent).where(AuditEvent.action == action).order_by(AuditEvent.id)
        return [event.details for event in self._run(self._all(query))]

    def bloom_api_list_docs_of_types(self, headers, prefix, types):
        query = [("type", doc_type) for doc_type in types]
        return self.bloom_api_call("GET", f"/api/projects/{prefix}/docs", headers, params=query)

    def bloom_api_open_doc(self, headers, prefix, slug, doc_id):
        return self.bloom_api_call("GET", f"/api/projects/{prefix}/docs/{slug}/{doc_id}", headers)

    def bloom_api_create_requirement_of_origin(self, headers, project_id, title, origin):
        body = {"project_id": project_id, "title": title, "req_origin": origin}
        return self.bloom_api_call("POST", "/api/requirements", headers, json=body)

    def bloom_api_set_requirement_origin(self, headers, requirement_id, origin):
        path = f"/api/requirements/{requirement_id}"
        return self.bloom_api_call("PATCH", path, headers, json={"req_origin": origin})

    def bloom_api_coverage_gaps(self, headers, project_id):
        return self.bloom_api_call("GET", f"/api/traceability/coverage-gaps/{project_id}", headers)

    def bloom_api_impact(self, headers, requirement_id):
        return self.bloom_api_call("GET", f"/api/traceability/impact/{requirement_id}", headers)

    def bloom_add_test_suite(self, project_id, suite_id, visibility, test_case_ids):
        suite = self._run(
            self._add(
                TestSuiteModel(
                    project_id=project_id,
                    suite_id=suite_id,
                    name=suite_id,
                    status=self.parameters.DOCUMENT_STATUS,
                    visibility=visibility,
                )
            )
        )
        for order, test_case_id in enumerate(test_case_ids):
            self._run(
                self._add(
                    TestSuiteItemModel(suite_id=suite, test_case_id=test_case_id, order=order)
                )
            )
        return suite

    def bloom_api_list_test_suites(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/test-suites", headers, params=query)

    def bloom_api_get_test_suite(self, headers, suite_id):
        return self.bloom_api_call("GET", f"/api/test-suites/{suite_id}", headers)

    def bloom_add_controlled_pair(self, project_id, kind, code):
        prefix = self.parameters.VISIBILITY_PREFIX
        visible, hidden = f"{prefix}-{code}-001", f"{prefix}-{code}-002"
        shown, internal = self.parameters.CUSTOMER_VISIBILITY, self.parameters.INTERNAL_VISIBILITY
        return SimpleNamespace(
            public=visible,
            visible=self._run(self._add(self._controlled(kind, project_id, visible, shown))),
            hidden=self._run(self._add(self._controlled(kind, project_id, hidden, internal))),
        )

    def bloom_api_probe_controlled(self, headers, project_id, path, pair):
        query = {"project_id": project_id}
        return SimpleNamespace(
            listed=self.bloom_api_call("GET", path, headers, params=query),
            hidden=self.bloom_api_call("GET", f"{path}/{pair.hidden}", headers),
            visible=self.bloom_api_call("GET", f"{path}/{pair.visible}", headers),
        )

    def bloom_add_campaign(self, project_id, campaign_id, visibility, suite_ids, items):
        campaign = self._run(
            self._add(
                TestCampaign(
                    project_id=project_id,
                    campaign_id=campaign_id,
                    name=campaign_id,
                    status="Planned",
                    visibility=visibility,
                )
            )
        )
        for suite_id in suite_ids:
            self._run(self._add(CampaignSuite(campaign_id=campaign, suite_id=suite_id)))
        for test_case_id, fields in items:
            self._run(
                self._add(
                    TestCampaignItem(campaign_id=campaign, test_case_id=test_case_id, **fields)
                )
            )
        return campaign

    def bloom_allow_bud_sync(self):
        async def credential():
            return object()

        main.app.dependency_overrides[require_bud_sync_token] = credential

    def bloom_api_list_campaigns(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/campaigns", headers, params=query)

    def bloom_api_get_campaign(self, headers, campaign_id):
        return self.bloom_api_call("GET", f"/api/campaigns/{campaign_id}", headers)

    def bloom_api_sync_results(self, headers, results):
        body = {"results": results}
        return self.bloom_api_call("POST", "/api/campaigns/sync-results", headers, json=body)

    def bloom_rules_for(self, permissions):
        return scenario_rules(permissions)

    def bloom_api_try_log_in(self, email, password):
        headers = {"user-agent": self.parameters.AUDITLOG_USER_AGENT}
        body = {"email": email, "password": password}
        return self._run(self._request("POST", "/api/auth/login", headers, json=body))

    def bloom_add_design(self, project_id, design_id):
        return self._run(
            self._add(DesignItem(project_id=project_id, design_id=design_id, title=design_id))
        )

    def bloom_api_set_design_visibility(self, headers, design_id, visibility):
        body = {"visibility": visibility}
        return self.bloom_api_call("PATCH", f"/api/designs/{design_id}", headers, json=body)

    def bloom_api_delete_design(self, headers, design_id):
        return self.bloom_api_call("DELETE", f"/api/designs/{design_id}", headers)

    def bloom_api_audit(self, headers, **query):
        return self.bloom_api_call("GET", "/api/audit", headers, params=query)

    def bloom_add_audit_events(self, hours, rows, actors):
        ids = []
        for hour, (actor, action, target, outcome, ip, request_id) in zip(hours, rows):
            actor_id = actors.get(actor, actor)
            ids.append(
                self._run(
                    self._add(
                        AuditEvent(
                            occurred_at=datetime(2026, 10, 12, hour),
                            actor_user_id=actor_id,
                            actor_type="anonymous" if actor_id is None else "user",
                            action=action,
                            target_type=target,
                            target_id=str(hour),
                            outcome=outcome,
                            ip=ip,
                            request_id=request_id,
                        )
                    )
                )
            )
        return ids

    def bloom_api_audit_pages(self, headers, action, field, direction):
        ids = []
        for offset in (0, self.parameters.AUDITLOG_PAGE):
            page = self.bloom_api_audit(
                headers,
                action=action,
                sort=field,
                dir=direction,
                limit=self.parameters.AUDITLOG_PAGE,
                offset=offset,
            )
            if page.status != self.parameters.STATUS_OK:
                return page.status
            ids.extend(item["id"] for item in page.body["items"])
        return ids

    def bloom_route_methods_of(self, module):
        return sorted(
            {
                method
                for _, route in self._api_routes(main.app)
                if route.endpoint.__module__ == module
                for method in route.methods
            }
        )

    def bloom_api_send(self, method, path, headers=None, address=None, errors=True, **fields):
        headers = {"user-agent": self.parameters.RQA_AGENT, **(headers or {})}
        return self._run(self._send_from(method, path, headers, address, errors, fields))

    def bloom_new_cli_world(self):
        self._run(self.engine.dispose())
        self.engine = create_async_engine(self.parameters.SYNC_DATABASE)
        self._run(self._create_tables())
        self.maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.bloom_enforce_foreign_keys()
        self.patches.enter_context(patch.object(settings, "CLI_CODE_MODE_ENABLED", True))
        return self._run(self._seed_cli_world())

    def bloom_set_code_mode(self, enabled):
        self.patches.enter_context(patch.object(settings, "CLI_CODE_MODE_ENABLED", enabled))

    def bloom_cli_challenge(self, verifier=None):
        verifier = verifier or self.parameters.CLIS_VERIFIER
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        letters = base64.b32encode(hashlib.sha256(challenge.encode()).digest()[:5]).decode()
        return challenge, f"{letters[:4]}-{letters[4:]}"

    def bloom_cli_start(self, **overrides):
        challenge, _ = self.bloom_cli_challenge()
        body = {"client_name": "Example client", "mode": "code", "code_challenge": challenge}
        body.update({"state": "test-state", **overrides})
        return self._cli("POST", "/start", json=body)

    def bloom_cli_session(self, **overrides):
        return self.bloom_cli_start(**overrides).json()["session_id"]

    def bloom_cli_approve(self, headers, session_id, request_code=None):
        code = request_code or self.bloom_cli_challenge()[1]
        body = {"session_id": session_id, "request_code": code}
        return self._cli("POST", "/approve", headers, json=body)

    def bloom_cli_check(self, headers, session_id, request_code=None):
        code = request_code or self.bloom_cli_challenge()[1]
        body = {"session_id": session_id, "request_code": code}
        return self._cli("POST", "/check", headers, json=body)

    def bloom_cli_exchange(self, session_id, code, verifier=None):
        body = {
            "session_id": session_id,
            "code": code,
            "code_verifier": verifier or self.parameters.CLIS_VERIFIER,
        }
        return self._cli("POST", "/exchange", json=body)

    def bloom_cli_deny(self, headers, session_id, **extra):
        return self._cli("POST", "/deny", headers, json={"session_id": session_id, **extra})

    def bloom_cli_lookup(self, headers, session_id):
        return self._cli("GET", f"/sessions/{session_id}", headers)

    def bloom_cli_refresh(self, body):
        return self._cli("POST", "/refresh", json=body)

    def bloom_cli_post(self, path, headers=None, body=None):
        return self._cli("POST", f"/{path}", headers, json=body)

    def bloom_cli_signed_in(self, headers):
        session_id = self.bloom_cli_session()
        code = self.bloom_cli_approve(headers, session_id).json()["exchange_code"]
        return self.bloom_cli_exchange(session_id, code).json()

    def bloom_cli_stored_ids(self):
        return {str(value) for value in self._run(self._all(select(CliAuthSession.id)))}

    def bloom_cli_get_session(self, session_id):
        return self._run(self._get(CliAuthSession, UUID(session_id)))

    def bloom_cli_change_session(self, session_id, **values):
        statement = update(CliAuthSession).where(CliAuthSession.id == UUID(session_id))
        self._run(self._execute_statement(statement.values(**values)))

    def bloom_cli_expire(self, session_id):
        self.bloom_cli_change_session(
            session_id, expires_at=datetime.utcnow() - timedelta(seconds=1)
        )

    def bloom_set_session_version(self, user_id, version):
        self._run(
            self._execute_statement(
                update(User).where(User.id == user_id).values(session_version=version)
            )
        )

    def bloom_change_refresh_rows(self, **values):
        self._run(self._execute_statement(update(UserToken).values(**values)))

    def bloom_count_user_tokens(self):
        return len(self._run(self._all(select(UserToken))))

    def bloom_token_headers(self, claims):
        return {"Authorization": "Bearer " + create_access_token(claims)}

    def bloom_password_reset_purpose(self):
        return UserTokenPurpose.password_reset

    def bloom_callback_code(self, target):
        return parse_qs(urlsplit(target).query)["code"][0]

    def bloom_unknown_session(self):
        return str(uuid4())

    def bloom_approve_with_stale_account(self, user_id):
        return self._run(self._approve_with_stale_account(user_id))

    def bloom_approve_after_concurrent_approval(self, headers, session_id, user_id):
        original = cli_auth.check_request_code

        async def approved_elsewhere(db, checked_id, typed):
            checked = await original(db, checked_id, typed)
            async with self.maker() as other:
                await other.execute(
                    update(CliAuthSession)
                    .where(CliAuthSession.id == checked_id)
                    .values(user_id=user_id, exchange_code_hash="approved-elsewhere")
                )
                await other.commit()
            return checked

        with patch.object(cli_auth, "check_request_code", approved_elsewhere):
            return self.bloom_cli_approve(headers, session_id)

    def bloom_api_send_through_image(
        self,
        received_from,
        forwarded=None,
        trusted=None,
        method="GET",
        path="/api/projects",
        **fields,
    ):
        chain = f"{forwarded}, {received_from}" if forwarded else received_from
        headers = {**fields.pop("headers", {}), "X-Forwarded-For": chain}
        app = ProxyHeadersMiddleware(self.api, trusted_hosts="127.0.0.1,::1")
        with patch.object(settings, "TRUSTED_PROXY_NETWORKS", list(trusted or [])):
            return self._run(
                self._send_to(app, ("127.0.0.1", 50000), method, path, headers, fields)
            )

    def bloom_api_send_direct(
        self, address, forwarded, trusted=None, method="GET", path="/api/projects", **fields
    ):
        headers = {**fields.pop("headers", {}), "X-Forwarded-For": forwarded}
        with patch.object(settings, "TRUSTED_PROXY_NETWORKS", list(trusted or [])):
            return self._run(
                self._send_to(self.api, (address, 50000), method, path, headers, fields)
            )

    def bloom_with_login_limit(self, sends):
        limiter.reset()
        try:
            with patch.object(limiter, "enabled", True):
                return [send() for send in sends]
        finally:
            limiter.reset()

    def bloom_with_refusal_threshold(self, threshold, sends):
        with patch.object(settings, "AUDIT_REFUSAL_THRESHOLD", threshold):
            return [send() for send in sends]

    def bloom_client_address(self, trusted, peer, *forwarded):
        with patch.object(settings, "TRUSTED_PROXY_NETWORKS", list(trusted)):
            return client_address(self._scope(peer, *forwarded))

    def bloom_rate_limit_keys(self, trusted, peer, *forwarded):
        with patch.object(settings, "TRUSTED_PROXY_NETWORKS", list(trusted)):
            request = Request(self._scope(peer, *forwarded))
            return rate_limit_key(request), get_remote_address(request)

    def bloom_trusted_proxy_setting(self):
        return settings.TRUSTED_PROXY_NETWORKS

    def bloom_load_trusted_proxies(self, secret, env_value=None, networks=None):
        fields = {"SECRET_KEY": secret, "_env_file": None}
        if networks is not None:
            fields["TRUSTED_PROXY_NETWORKS"] = networks
        with patch.dict(
            "os.environ", {} if env_value is None else {"TRUSTED_PROXY_NETWORKS": env_value}
        ):
            try:
                return Settings(**fields).TRUSTED_PROXY_NETWORKS, None
            except ValidationError as error:
                return None, type(error).__name__

    def bloom_request_records(self, response=None, **match):
        found = []
        for record in self.bloom_list_audit_events(self.parameters.RQA_ACTION):
            values = {**(record.details or {}), "outcome": record.outcome, "ip": record.ip}
            if response is not None and record.request_id != response.headers.get("x-request-id"):
                continue
            if all(values.get(key) == value for key, value in match.items()):
                found.append(record)
        return found

    def bloom_audit_columns(self):
        return list(AuditEvent.__table__.columns.keys())

    def bloom_list_every_audit_event(self):
        return self._run(self._all(select(AuditEvent).order_by(AuditEvent.id)))

    def bloom_cli_headers(self, user_id):
        user = self._run(self._get(User, user_id))
        refresh = self._run(
            self._add(
                UserToken(
                    user_id=user_id,
                    purpose=UserTokenPurpose.refresh,
                    token_hash="c" * 64,
                    expires_at=datetime.utcnow() + timedelta(days=1),
                )
            )
        )
        claims = {"sub": str(user_id), "type": "user", "ver": user.session_version}
        token = create_access_token({**claims, "cli_refresh_id": refresh})
        return {"Authorization": f"Bearer {token}"}

    def bloom_user_token_headers(self, user_id):
        user = self._run(self._get(User, user_id))
        claims = {"sub": str(user_id), "type": "user", "ver": user.session_version}
        return {"Authorization": f"Bearer {create_access_token(claims)}"}

    def bloom_deactivate(self, user_id):
        self._run(
            self._execute_statement(update(User).where(User.id == user_id).values(is_active=False))
        )

    def bloom_add_notification(self, user_id):
        return self._run(
            self._add(Notification(user_id=user_id, event_type="comment", title="For the owner"))
        )

    def bloom_add_old_refusals(self, address, count, minutes):
        for _ in range(count):
            self._run(
                self._add(
                    AuditEvent(
                        occurred_at=datetime.utcnow() - timedelta(minutes=minutes),
                        actor_type="anonymous",
                        action=self.parameters.RQA_ACTION,
                        ip=address,
                        outcome="denied",
                    )
                )
            )

    def bloom_set_refusal_threshold(self, threshold):
        self.patches.enter_context(patch.object(settings, "AUDIT_REFUSAL_THRESHOLD", threshold))

    def bloom_refusal_window(self):
        return settings.AUDIT_REFUSAL_THRESHOLD, settings.AUDIT_REFUSAL_WINDOW_MINUTES

    def bloom_cors_origin(self):
        return settings.CORS_ORIGINS[0]

    def bloom_sign_in_many_times_rate_limited(self, address, count, body):
        limiter.reset()
        try:
            with patch.object(limiter, "enabled", True):
                return [
                    self.bloom_api_send("POST", "/api/auth/login", address=address, json=body)
                    for _ in range(count)
                ]
        finally:
            limiter.reset()

    def bloom_send_while_audit_fails(self, path):
        async def unavailable(scope):
            raise OperationalError("INSERT", {}, Exception("database unavailable"))

        root = logging.getLogger()
        handler = BufferingHandler(self.parameters.LOG_CAPACITY)
        root.addHandler(handler)
        try:
            with patch.object(audit_service, "_open_session", unavailable):
                answer = self.bloom_api_send("GET", path)
        finally:
            root.removeHandler(handler)
        return answer, "\n".join(record.getMessage() for record in handler.buffer)

    def bloom_add_exploding_route(self, path, message):
        routes = list(main.app.router.routes)

        @main.app.get(path)
        async def explode():
            raise RuntimeError(message)

        self.patches.callback(setattr, main.app.router, "routes", routes)

    def bloom_route_template(self, path):
        class Route:
            path_format = "/{project_id}/things/{thing_id}"
            path_regex = re.compile(r"^/(?P<project_id>[^/]+)/things/(?P<thing_id>[^/]+)$")

        return route_template({"route": Route(), "path": path}), route_template({"path": path})

    def bloom_request_outcomes(self, codes):
        return [request_outcome(code) for code in codes], request_outcome(404, refused=True)

    def bloom_read_created_bodies(self):
        plain = CreatedBody(gzipped=False)
        plain.feed(b'{"id": 4, ')
        plain.feed(b'"doc_id": "PRJ-DOC-004"}')
        packed = CreatedBody(gzipped=True)
        packed.feed(gzip.compress(b'{"id": 5}'))
        large = CreatedBody(gzipped=False)
        large.feed(b"x" * (CREATED_BODY_LIMIT + 1))
        broken = CreatedBody(gzipped=True)
        broken.feed(b"not gzip")
        return tuple(body.parsed() for body in (plain, packed, large, broken))

    def bloom_api_get_baseline(self, headers, baseline_id):
        return self.bloom_api_call("GET", f"/api/baselines/{baseline_id}", headers)

    def bloom_api_list_settings(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/integrations/settings", headers, params=query)

    def bloom_api_related(self, headers, kind, artefact_id):
        return self.bloom_api_call("GET", f"/api/artefacts/{kind}/{artefact_id}/related", headers)

    def bloom_api_list_variables(self, headers, project_id):
        query = {"project_id": project_id}
        return self.bloom_api_call("GET", "/api/project-variables", headers, params=query)

    def bloom_add_document(self, project_id, doc_id, title, visibility):
        return self._run(
            self._add(
                Document(
                    project_id=project_id,
                    doc_id=doc_id,
                    title=title,
                    doc_type=self.parameters.DOCUMENT_TYPE,
                    visibility=visibility,
                    status=self.parameters.DOCUMENT_STATUS,
                    version=self.parameters.DOCUMENT_VERSION,
                )
            )
        )

    def bloom_api_list_documents(self, headers, project_id):
        return self._run(self._request("GET", f"/api/projects/{project_id}/documents", headers))

    def bloom_api_get_document(self, headers, document_id):
        return self._run(self._request("GET", f"/api/documents/{document_id}", headers))

    def bloom_api_me(self, headers):
        answer = self._run(self._request("GET", "/api/auth/me", headers))
        return answer.json().get("id") if answer.status_code == 200 else None

    def bloom_api_create_artefact(self, headers, kind, project_id, title, **fields):
        body = {"project_id": project_id, "title": title, **fields}
        if kind == self.parameters.DOCUMENT_KIND:
            body.setdefault("doc_type", self.parameters.DOCUMENT_TYPE)
            path = f"/api/projects/{project_id}/documents"
        else:
            path = self.parameters.ARTEFACT_PATHS[kind]
        return self._run(self._request("POST", path, headers, json=body))

    def bloom_api_update_artefact(self, headers, kind, artefact_id, body):
        path = f"{self.parameters.ARTEFACT_PATHS[kind]}/{artefact_id}"
        return self._run(self._request("PATCH", path, headers, json=body))

    def bloom_api_activity_types(self, headers, kind, artefact_id):
        path = f"/api/artefacts/{kind}/{artefact_id}/activity"
        answer = self._run(self._request("GET", path, headers))
        if answer.status_code != 200:
            return None
        return [event["event_type"] for event in answer.json()]

    def bloom_api_sign_off(self, headers, kind, artefact_id, step):
        path = f"/api/artefacts/{kind}/{artefact_id}/sign-off"
        return self._run(self._request("POST", path, headers, json={"step": step}))

    def bloom_api_review(self, headers, kind, artefact_id, reviewer_id):
        base = f"/api/artefacts/{kind}/{artefact_id}"
        assigned = self._run(
            self._request(
                "PUT",
                base + "/workflow/assignees",
                headers,
                json={"reviewer_id": reviewer_id, "approver_id": reviewer_id},
            )
        )
        requested = self._run(
            self._request(
                "POST", base + "/requests", headers, json={"kind": self.parameters.REVIEW_REQUEST}
            )
        )
        commented = self._run(
            self._request(
                "POST", base + "/comments", headers, json={"body": self.parameters.REVIEW_COMMENT}
            )
        )
        signed = self.bloom_api_sign_off(headers, kind, artefact_id, self.parameters.REVIEW_STEP)
        return [assigned.status_code, requested.status_code, commented.status_code], signed

    def bloom_api_link(self, headers, project_id, source_id, target_id):
        body = {
            "project_id": project_id,
            "source_type": self.parameters.LINK_SOURCE,
            "source_id": source_id,
            "target_type": self.parameters.LINK_TARGET,
            "target_id": target_id,
            "role": self.parameters.LINK_ROLE,
        }
        return self._run(self._request("POST", "/api/links", headers, json=body))

    def bloom_api_list_docs(self, headers, prefix, doc_type):
        path = f"/api/projects/{prefix}/docs"
        return self._run(self._request("GET", path, headers, params={"type": doc_type}))

    def bloom_log_in(self, email, password):
        answer = self._run(
            self._request("POST", "/api/auth/login", json={"email": email, "password": password})
        )
        token = answer.json().get("access_token") if answer.status_code == 200 else None
        return {"Authorization": f"Bearer {token}"}, answer.status_code

    def bloom_api_create_project(self, headers, prefix):
        body = {"name": f"Project {prefix}", "prefix": prefix}
        return self._run(self._request("POST", "/api/projects", headers, json=body))

    def bloom_api_create_baseline(self, headers, project_id, name):
        body = {"project_id": project_id, "name": name}
        return self._run(self._request("POST", "/api/baselines", headers, json=body))

    def bloom_api_create_user(self, headers, email, password, role, full_name=None):
        body = {
            "email": email,
            "full_name": full_name or email,
            "password": password,
            "role": role,
        }
        return self._run(self._request("POST", "/api/users", headers, json=body))

    def bloom_api_create_policy(
        self, headers, name, permissions, types=None, visibility="internal"
    ):
        return self.bloom_api_create_policy_rules(
            headers, name, scenario_rules(permissions, visibility, types)
        )

    def bloom_api_create_policy_rules(self, headers, name, rules):
        body = {"name": name, "rules": rules}
        return self._run(self._request("POST", "/api/policies", headers, json=body))

    def bloom_api_create_group(self, headers, name, policy_ids):
        body = {"name": name, "description": name, "policy_ids": policy_ids}
        return self._run(self._request("POST", "/api/groups", headers, json=body))

    def bloom_api_add_group_member(self, headers, group_id, user_id):
        path = f"/api/groups/{group_id}/members"
        return self._run(self._request("POST", path, headers, json={"user_id": user_id}))

    def bloom_api_admit_group(self, headers, group_id, project_id):
        path = f"/api/groups/{group_id}/grants"
        return self._run(self._request("POST", path, headers, json={"project_id": project_id}))

    def bloom_api_add_project_member(self, headers, project_id, user_id, policy_ids, owner=False):
        path = f"/api/projects/{project_id}/members"
        body = {"user_id": user_id, "policy_ids": policy_ids}
        if owner:
            body["owner"] = True
        return self._run(self._request("POST", path, headers, json=body))

    def bloom_api_update_project_member(self, headers, project_id, member_id, policy_ids):
        path = f"/api/projects/{project_id}/members/{member_id}"
        body = {"policy_ids": policy_ids}
        return self._run(self._request("PATCH", path, headers, json=body))

    def bloom_api_send_group_members(self, headers, group_id, body):
        return self.bloom_api_call("POST", f"/api/groups/{group_id}/members", headers, json=body)

    def bloom_api_get_group(self, headers, group_id):
        return self._run(self._request("GET", f"/api/groups/{group_id}", headers))

    def bloom_api_read_baselines(self, headers, project_id, baseline_id):
        listed = self._run(
            self._request("GET", "/api/baselines", headers, params={"project_id": project_id})
        )
        detail = self._run(self._request("GET", f"/api/baselines/{baseline_id}", headers))
        return listed, detail

    def bloom_capture_access_request_mail(self):
        sent = []
        self.patches.enter_context(
            patch.object(
                access_requests_api,
                "send_access_request_email",
                lambda **mail: sent.append(mail),
            )
        )
        return sent

    def bloom_api_create_requirement(self, headers, project_id, title, status=None):
        body = {"project_id": project_id, "title": title}
        if status is not None:
            body["status"] = status
        return self._run(self._request("POST", "/api/requirements", headers, json=body))

    def bloom_api_open_requirement_doc(self, headers, prefix, ref):
        path = f"/api/projects/{prefix}/docs/requirements/{ref}"
        return self._run(self._request("GET", path, headers))

    def bloom_api_request_access(self, headers, resource_type, resource_ref, prefix):
        body = {
            "resource_type": resource_type,
            "resource_ref": str(resource_ref),
            "project_prefix": prefix,
        }
        return self._run(self._request("POST", "/api/access-requests", headers, json=body))

    def bloom_api_my_access_request(self, headers, resource_type, resource_ref, prefix):
        query = {
            "resource_type": resource_type,
            "resource_ref": str(resource_ref),
            "project_prefix": prefix,
        }
        return self._run(self._request("GET", "/api/access-requests/mine", headers, params=query))

    def bloom_api_list_access_requests(self, headers, prefix):
        query = {"project_prefix": prefix}
        return self._run(self._request("GET", "/api/access-requests", headers, params=query))

    def bloom_api_decide_access_request(self, headers, request_id, decision):
        path = f"/api/access-requests/{request_id}/decision"
        return self._run(self._request("POST", path, headers, json={"decision": decision}))

    def bloom_api_list_all_access_requests(self, headers, status=None):
        query = {"status": status} if status else None
        return self._run(self._request("GET", "/api/access-requests", headers, params=query))

    def bloom_api_request_access_while_mail_fails(
        self, headers, resource_type, resource_ref, prefix
    ):
        def fail(**mail):
            raise MailConfigurationError(self.parameters.ARQ_MAIL_ERROR)

        with patch.object(access_requests_api, "send_access_request_email", fail):
            return self.bloom_api_request_access(headers, resource_type, resource_ref, prefix)

    def bloom_list_audit_events(self, action):
        query = select(AuditEvent).where(AuditEvent.action == action).order_by(AuditEvent.id)
        return self._run(self._all(query))

    def bloom_api_get_requirement(self, headers, requirement_id):
        return self._run(self._request("GET", f"/api/requirements/{requirement_id}", headers))

    def bloom_api_get_user(self, headers, user_id):
        return self._run(self._request("GET", f"/api/users/{user_id}", headers))

    def bloom_api_audit_event(self, headers, action, target_type, target_id):
        query = {"action": action, "target_type": target_type, "target_id": str(target_id)}
        page = self._run(self._request("GET", "/api/audit", headers, params=query))
        items = page.json().get("items") if page.status_code == 200 else None
        return items[0] if items else None

    def bloom_api_post_and_read_logs(self, posts):
        root = logging.getLogger()
        handler = BufferingHandler(self.parameters.LOG_CAPACITY)
        level = root.level
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        try:
            for path, body in posts:
                self._run(self._request("POST", path, json=body))
        finally:
            root.removeHandler(handler)
            root.setLevel(level)
        return "\n".join(
            record.getMessage()
            for record in handler.buffer
            if record.name.startswith(self.parameters.APP_LOGGERS)
        )

    def bloom_api_delete_project(self, headers, project_id):
        return self._run(self._request("DELETE", f"/api/projects/{project_id}", headers))

    def bloom_api_get_project(self, headers, project_id):
        return self._run(self._request("GET", f"/api/projects/{project_id}", headers))

    def bloom_api_call(self, method, path, headers=None, json=None, params=None):
        answer = self._run(self._request(method, path, headers, json=json, params=params))
        try:
            body = answer.json()
        except ValueError:
            body = None
        return SimpleNamespace(status=answer.status_code, body=body)

    def bloom_api_delete_user(self, headers, user_id):
        return self.bloom_api_call("DELETE", f"/api/users/{user_id}", headers)

    def bloom_api_list_user_ids(self, headers):
        listed = self.bloom_api_call("GET", "/api/users", headers)
        rows = listed.body.get("items", []) if isinstance(listed.body, dict) else listed.body or []
        return listed.status, [row["id"] for row in rows]

    def bloom_enforce_foreign_keys(self):
        async def enforce():
            async with self.engine.connect() as conn:
                await conn.exec_driver_sql(self.parameters.SQLITE_FOREIGN_KEYS)

        self._run(enforce())

    def bloom_doc_id_pattern(self):
        return id_generator.DOC_ID_PATTERN.pattern

    def bloom_api_routes(self):
        routes = []
        for path, route in self._api_routes(main.app):
            names = set()
            pending = list(route.dependant.dependencies)
            while pending:
                dependency = pending.pop()
                name = getattr(dependency.call, "__name__", None)
                if name:
                    names.add(name)
                pending.extend(dependency.dependencies)
            methods = ",".join(sorted(route.methods or set()))
            integer_path = any(
                self._is_integer(param.field_info.annotation)
                for param in route.dependant.path_params
            )
            routes.append(
                SimpleNamespace(
                    path=path,
                    methods=methods,
                    method_list=sorted(route.methods or set()),
                    endpoint=route.endpoint.__name__,
                    dependencies=names,
                    integer_path=integer_path,
                )
            )
        return routes

    def _is_integer(self, annotation):
        return (
            isinstance(annotation, type) and issubclass(annotation, int) and annotation is not bool
        )

    def _api_routes(self, router, prefix=""):
        for route in router.routes:
            if isinstance(route, APIRoute):
                path = f"{prefix}{route.path}"
                if path.startswith(self.parameters.API_PREFIX):
                    yield path, route
                continue
            original = getattr(route, "original_router", None)
            context = getattr(route, "include_context", None)
            if original is not None and context is not None:
                yield from self._api_routes(original, f"{prefix}{context.prefix}")

    def bloom_seed_admin_email(self):
        return settings.ADMIN_EMAIL

    def bloom_api_set_role(self, headers, user_id, role):
        return self.bloom_api_call("PATCH", f"/api/users/{user_id}", headers, json={"role": role})

    async def _update(self, model, row_id, **fields):
        async with self.maker() as db:
            row = await db.get(model, row_id)
            for name, value in fields.items():
                setattr(row, name, value)
            await db.commit()

    def _controlled(self, kind, project_id, public, visibility):
        common = {"project_id": project_id, "visibility": visibility}
        if kind == "design":
            return DesignItem(
                design_id=public,
                title=public,
                status="Draft",
                priority="Medium",
                design_type="Architecture",
                **common,
            )
        if kind == "risk":
            return RiskItem(
                risk_id=public,
                title=public,
                status="Open",
                severity="Medium",
                probability="Medium",
                risk_category="Technical",
                **common,
            )
        if kind == "change":
            return ChangeRequest(
                change_id=public,
                title=public,
                status="Submitted",
                priority="Medium",
                change_type="Enhancement",
                **common,
            )
        if kind == "concept":
            return TestConcept(concept_id=public, name=public, status="Draft", coverage=0, **common)
        return Defect(
            defect_id=public,
            title=public,
            status="Open",
            severity="Medium",
            priority="Medium",
            **common,
        )

    def _answer(self, answer):
        try:
            body = answer.json()
        except ValueError:
            body = None
        return SimpleNamespace(status=answer.status_code, body=body)

    def _with_key(self, key, call, value):
        try:
            if key is None:
                return SimpleNamespace(value=call(value), status=None)
            with patch.object(settings, "INTEGRATION_ENCRYPTION_KEY", key):
                return SimpleNamespace(value=call(value), status=None)
        except HTTPException as exc:
            return SimpleNamespace(value=None, status=exc.status_code)

    def _cli(self, method, path, headers=None, json=None):
        return self.bloom_api_send(method, self.parameters.CLI_PREFIX + path, headers, json=json)

    async def _seed_cli_world(self):
        async with self.maker() as db:
            user = User(
                email="cli-reader@example.com",
                full_name="CLI Reader",
                hashed_password="unused",
                role=UserRole.maintainer,
                is_active=True,
            )
            other = User(
                email="other@example.com",
                full_name="Other",
                hashed_password="unused",
                role=UserRole.external,
                is_active=True,
            )
            project = Project(name="Demo", prefix="PRJ")
            policy = Policy(name="App reader", scope="app", permissions={"application": ["view"]})
            db.add_all([user, other, project, policy])
            await db.flush()
            db.add(
                project_access_fixture(
                    user_id=user.id, project_id=project.id, permissions={"REQ": ["view"]}
                )
            )
            await db.execute(
                user_application_policies.insert().values(user_id=user.id, policy_id=policy.id)
            )
            await db.commit()
            claims = {"sub": str(user.id), "type": "user", "ver": 1}
            return SimpleNamespace(
                headers={"Authorization": "Bearer " + create_access_token(claims)},
                user_id=user.id,
                other_id=other.id,
            )

    async def _approve_with_stale_account(self, user_id):
        challenge, request_code = self.bloom_cli_challenge()
        async with self.maker() as db:
            start = CliStartRequest(
                client_name="Client", mode="code", code_challenge=challenge, state="state"
            )
            session = await cli_auth.start_session(db, start)
            await db.commit()
            session_id = session.id
        async with self.maker() as db:
            account = await db.get(User, user_id)
            async with self.maker() as other:
                await other.execute(
                    update(User).where(User.id == user_id).values(session_version=2)
                )
                await other.commit()
            try:
                await cli_auth.approve_session(db, session_id, account, request_code)
                reason = None
            except cli_auth.CliAuthorizationError as refused:
                reason = refused.reason
        stored = await self._get(CliAuthSession, session_id)
        return reason, stored.user_id, stored.exchange_code_hash

    def _scope(self, peer, *forwarded):
        return {
            "type": "http",
            "client": (peer, 50000) if peer else None,
            "headers": [(b"x-forwarded-for", value.encode("latin-1")) for value in forwarded],
        }

    async def _send_to(self, app, origin, method, path, headers, fields):
        transport = httpx.ASGITransport(app=app, client=origin)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, headers=headers, **fields)

    async def _send_from(self, method, path, headers, address, errors, fields):
        origin = (address, 4321) if address else ("127.0.0.1", 123)
        transport = httpx.ASGITransport(app=self.api, client=origin, raise_app_exceptions=errors)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, headers=headers, **fields)

    async def _execute_statement(self, statement):
        async with self.maker() as db:
            await db.execute(statement)
            await db.commit()

    async def _upload(self, path, headers, files):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.post(path, headers=headers, files=files)

    async def _add_group_exporter(self, project_id, user_id, name, permissions):
        async with self.maker() as db:
            read = {resource: ["view"] for resource in permissions}
            policy = Policy(
                name=name,
                permissions=permissions,
                type_tags=scenario_type_tags(read, self.parameters.CUSTOMER_VISIBILITY),
            )
            group = Group(name=name)
            db.add_all([policy, group])
            await db.flush()
            db.add_all(
                [
                    GroupMembership(group_id=group.id, user_id=user_id),
                    ProjectAccess(group_id=group.id, project_id=project_id, policies=[policy]),
                ]
            )
            await db.commit()

    async def _post(self, path, body, headers):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.post(path, content=body, headers=headers)

    async def _request(self, method, path, headers=None, json=None, params=None):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, headers=headers, json=json, params=params)
