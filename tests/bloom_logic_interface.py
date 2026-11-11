"""
* @file     ${tests/bloom_logic_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's logic tests: services and helpers called directly, without the app.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Only the lifespan check loads the application object, inside that one call.
"""

import asyncio
import base64
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
import tempfile
import time
import tomllib
import typing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import yaml
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from sqlalchemy import select, text

from app import audit
from app.api import artefact_utils, campaigns, docs_facade, integrations
from app.core import id_generator, security
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    get_external_doc_types,
)
from app.models import (
    AuditEvent,
    Document,
    IntegrationSetting,
    SystemMarker,
    user_token,
)
from app.models.user import User, UserRole
from app.schemas import ProjectCreate, schemas
from app.services import (
    attachment_storage,
    integration_sync,
    jira_outbound,
    token_service,
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

    def bloom_list_docs_routes(self):
        return [route.path for route in docs_facade.router.routes]

    def bloom_external_doc_types_as_admin(self, project_id):
        db = AsyncMock()
        admin = SimpleNamespace(id=self.parameters.EXTERNAL_USER_ID, role=UserRole.admin)
        allowed = self._run(get_external_doc_types(db, admin, project_id))
        return SimpleNamespace(allowed=allowed, queries=db.execute.await_count)

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
                patch.object(attachment_storage, "get_attachment_root", lambda: root),
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
