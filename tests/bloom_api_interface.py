"""
* @file     ${tests/bloom_api_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's API tests: the routes served in-process over in-memory SQLite.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Requests go through an ASGI transport; no server is started.
"""

import hashlib
import hmac
import json
import logging
from logging.handlers import BufferingHandler
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy import event

import tests.parameters as params
from app import main
from app.api import access_requests as access_requests_api
from app.api import integrations
from app.core.database import get_db
from app.core.deps import limiter
from app.core.permissions import DOC_TYPE_RESOURCES
from app.core.security import get_password_hash
from app.models import ChangeRequest, Defect, Document, IntegrationSetting
from app.models import TestCase as TestCaseModel
from app.models.user import User, UserRole
from app.services.integration_secrets import encrypt_integration_secret
from tests.access_fixtures import (
    allow_doc_types,
    project_access_fixture,
    scenario_rules,
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

    def bloom_set_defect_status(self, defect_id, status):
        self._run(self._update(Defect, defect_id, status=status))

    def bloom_update_setting(self, setting_id, **fields):
        self._run(self._update(IntegrationSetting, setting_id, **fields))

    def bloom_add_test_case(self, project_id, tc_id, title):
        return self._run(self._add(TestCaseModel(project_id=project_id, tc_id=tc_id, title=title)))

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

    def bloom_add_admin(self, email, password):
        return self.bloom_add_account(email, password, UserRole.admin.value)

    def bloom_add_account(self, email, password, role):
        return self._run(
            self._add(
                User(
                    email=email,
                    full_name=email,
                    hashed_password=get_password_hash(password),
                    role=UserRole(role),
                    is_active=True,
                )
            )
        )

    def bloom_add_external_member(self, project_id, user_id, permissions, visibility):
        self._run(self._add_external_member(project_id, user_id, permissions, visibility))

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

    def bloom_api_create_policy(self, headers, name, permissions, types=None):
        return self.bloom_api_create_policy_rules(
            headers, name, scenario_rules(permissions, "internal", types)
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

    async def _update(self, model, row_id, **fields):
        async with self.maker() as db:
            row = await db.get(model, row_id)
            for name, value in fields.items():
                setattr(row, name, value)
            await db.commit()

    async def _post(self, path, body, headers):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.post(path, content=body, headers=headers)

    async def _add_external_member(self, project_id, user_id, permissions, visibility):
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
            for doc_type in DOC_TYPE_RESOURCES:
                allow_doc_types(membership.policies[0], [doc_type])
            await db.commit()

    async def _request(self, method, path, headers=None, json=None, params=None):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, headers=headers, json=json, params=params)
