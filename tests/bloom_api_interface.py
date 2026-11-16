"""
* @file     ${tests/bloom_api_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's API tests: the routes served in-process over in-memory SQLite.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Requests go through an ASGI transport; no server is started.
"""

import csv
import hashlib
import hmac
import io
import json
import logging
from logging.handlers import BufferingHandler
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from sqlalchemy import event, select

import tests.parameters as params
from app import main
from app.api import access_requests as access_requests_api
from app.api import integrations
from app.core import id_generator
from app.core.cache import dashboard_stats_cache
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import limiter
from app.core.permissions import DOC_TYPE_RESOURCES
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
from app.models.groups import Group, GroupMembership, Policy
from app.models.project_membership import ProjectAccess
from app.models.user import User, UserRole
from app.schemas.memberships import DEFAULT_EXTERNAL_DOC_TYPES
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

    def bloom_start_full_api(self):
        self.patches.enter_context(patch.dict(main.app.dependency_overrides))
        main.app.dependency_overrides[get_db] = self._serve_session
        self.patches.enter_context(patch.object(limiter, "enabled", False))
        self.api = main.app

    def bloom_add_external_member(
        self, project_id, user_id, permissions, visibility, doc_types=None
    ):
        self._run(
            self._add_external_member(project_id, user_id, permissions, visibility, doc_types)
        )

    def bloom_add_internal_member(self, project_id, user_id, permissions):
        self._run(
            self._add(
                project_access_fixture(
                    user_id=user_id, project_id=project_id, permissions=permissions
                )
            )
        )

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

    async def _add_external_member(self, project_id, user_id, permissions, visibility, doc_types):
        async with self.maker() as db:
            membership = project_access_fixture(
                user_id=user_id,
                project_id=project_id,
                permissions=permissions,
                visibility=visibility,
                doc_types=[],
            )
            db.add(membership)
            await db.flush()
            for doc_type in DOC_TYPE_RESOURCES if doc_types is None else doc_types:
                allow_doc_types(membership.policies[0], [doc_type])
            await db.commit()

    async def _request(self, method, path, headers=None, json=None, params=None):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, headers=headers, json=json, params=params)
