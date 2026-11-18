"""
* @file     ${tests/sec/request_audit.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the record every HTTP request leaves in the audit log.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the request audit.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class RequestAuditBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_web_calls_are_recorded_with_actor_client_route_and_target(self):
        values, client = self.parameters, "web"
        address = values.RQA_CLIENTS[client]
        headers = self.admin if client == "web" else self.bloom.bloom_cli_headers(self.admin_id)
        send = self.bloom.bloom_api_send
        read = send("GET", f"/api/projects/{self.project}", headers, address)
        created = send(
            "POST",
            "/api/requirements",
            {**headers, "Accept-Encoding": "gzip"},
            address,
            json={
                "project_id": self.project,
                "title": values.RQA_TITLE,
                "description": values.RQA_LONG_DESCRIPTION,
            },
        )
        requirement = created.json()
        changed = send(
            "PATCH",
            f"/api/requirements/{requirement['id']}",
            headers,
            address,
            json={"title": values.RQA_NEW_TITLE},
        )
        deleted = send("DELETE", f"/api/requirements/{requirement['id']}", headers, address)
        answers = (read, created, changed, deleted)
        self.print_variables({"statuses": [answer.status_code for answer in answers]})
        self.assertEqual(
            [answer.status_code for answer in answers],
            [values.STATUS_OK, values.STATUS_CREATED, values.STATUS_OK, values.STATUS_NO_CONTENT],
            msg=values.MSG_RQA_STATUSES.format(client=client),
            abort_on_fail=False,
        )
        self.assertEqual(
            created.headers.get("content-encoding"),
            "gzip",
            msg=values.MSG_RQA_GZIP,
            abort_on_fail=False,
        )
        expected = [
            (read, "GET", "/api/projects/{project_id}", 200, "project", str(self.project)),
            (created, "POST", "/api/requirements", 201, None, None),
            (
                changed,
                "PATCH",
                "/api/requirements/{requirement_id}",
                200,
                "requirement",
                str(requirement["id"]),
            ),
            (
                deleted,
                "DELETE",
                "/api/requirements/{requirement_id}",
                204,
                "requirement",
                str(requirement["id"]),
            ),
        ]
        for answer, method, route, status, target_type, target_id in expected:
            records = self.bloom.bloom_request_records(
                answer, method=method, route=route, status=status
            )
            self.assertEqual(
                [
                    (
                        record.actor_type,
                        record.actor_user_id,
                        record.details["client"],
                        record.details["auth"],
                        record.outcome,
                        record.target_type,
                        record.target_id,
                        bool(record.ip),
                        record.user_agent,
                    )
                    for record in records
                ],
                [
                    (
                        "user",
                        self.admin_id,
                        client,
                        "bearer",
                        "success",
                        target_type,
                        target_id,
                        True,
                        values.RQA_AGENT,
                    )
                ],
                msg=values.MSG_RQA_CALL.format(client=client, method=method),
                abort_on_fail=False,
            )
        [creation] = self.bloom.bloom_request_records(created) or [None]
        self.assertEqual(
            (creation.details.get("created_id"), creation.details.get("created_doc_id")),
            (requirement["id"], requirement["req_id"]),
            msg=values.MSG_RQA_CREATED.format(client=client),
            abort_on_fail=False,
        )
        [project_read] = self.bloom.bloom_request_records(read) or [None]
        self.assertEqual(
            project_read.project_id,
            self.project,
            msg=values.MSG_RQA_PROJECT.format(client=client),
            abort_on_fail=False,
        )

    def bud_cli_calls_are_recorded_with_actor_client_route_and_target(self):
        values, client = self.parameters, "cli"
        address = values.RQA_CLIENTS[client]
        headers = self.admin if client == "web" else self.bloom.bloom_cli_headers(self.admin_id)
        send = self.bloom.bloom_api_send
        read = send("GET", f"/api/projects/{self.project}", headers, address)
        created = send(
            "POST",
            "/api/requirements",
            {**headers, "Accept-Encoding": "gzip"},
            address,
            json={
                "project_id": self.project,
                "title": values.RQA_TITLE,
                "description": values.RQA_LONG_DESCRIPTION,
            },
        )
        requirement = created.json()
        changed = send(
            "PATCH",
            f"/api/requirements/{requirement['id']}",
            headers,
            address,
            json={"title": values.RQA_NEW_TITLE},
        )
        deleted = send("DELETE", f"/api/requirements/{requirement['id']}", headers, address)
        answers = (read, created, changed, deleted)
        self.print_variables({"statuses": [answer.status_code for answer in answers]})
        self.assertEqual(
            [answer.status_code for answer in answers],
            [values.STATUS_OK, values.STATUS_CREATED, values.STATUS_OK, values.STATUS_NO_CONTENT],
            msg=values.MSG_RQA_STATUSES.format(client=client),
            abort_on_fail=False,
        )
        self.assertEqual(
            created.headers.get("content-encoding"),
            "gzip",
            msg=values.MSG_RQA_GZIP,
            abort_on_fail=False,
        )
        expected = [
            (read, "GET", "/api/projects/{project_id}", 200, "project", str(self.project)),
            (created, "POST", "/api/requirements", 201, None, None),
            (
                changed,
                "PATCH",
                "/api/requirements/{requirement_id}",
                200,
                "requirement",
                str(requirement["id"]),
            ),
            (
                deleted,
                "DELETE",
                "/api/requirements/{requirement_id}",
                204,
                "requirement",
                str(requirement["id"]),
            ),
        ]
        for answer, method, route, status, target_type, target_id in expected:
            records = self.bloom.bloom_request_records(
                answer, method=method, route=route, status=status
            )
            self.assertEqual(
                [
                    (
                        record.actor_type,
                        record.actor_user_id,
                        record.details["client"],
                        record.details["auth"],
                        record.outcome,
                        record.target_type,
                        record.target_id,
                        bool(record.ip),
                        record.user_agent,
                    )
                    for record in records
                ],
                [
                    (
                        "user",
                        self.admin_id,
                        client,
                        "bearer",
                        "success",
                        target_type,
                        target_id,
                        True,
                        values.RQA_AGENT,
                    )
                ],
                msg=values.MSG_RQA_CALL.format(client=client, method=method),
                abort_on_fail=False,
            )
        [creation] = self.bloom.bloom_request_records(created) or [None]
        self.assertEqual(
            (creation.details.get("created_id"), creation.details.get("created_doc_id")),
            (requirement["id"], requirement["req_id"]),
            msg=values.MSG_RQA_CREATED.format(client=client),
            abort_on_fail=False,
        )
        [project_read] = self.bloom.bloom_request_records(read) or [None]
        self.assertEqual(
            project_read.project_id,
            self.project,
            msg=values.MSG_RQA_PROJECT.format(client=client),
            abort_on_fail=False,
        )

    def bud_service_credential_calls_name_the_credential(self):
        values, send = self.parameters, self.bloom.bloom_api_send
        address = values.RQA_SERVICE_ADDRESS
        issued = send(
            "POST",
            "/api/service-credentials",
            self.admin,
            address,
            json={"name": values.RQA_SERVICE_NAME},
        )
        credential = issued.json()
        service = {"Authorization": f"Bearer {credential['token']}"}
        mailbox = send("GET", "/api/bud/report-requests", service, address, params={"after_id": 0})
        published = send(
            "POST",
            "/api/bud/test-reports",
            service,
            address,
            json={"project_prefix": values.RQA_PREFIX, **values.RQA_RUN},
        )
        self.print_variables(
            {"statuses": (issued.status_code, mailbox.status_code, published.status_code)}
        )
        self.assertEqual(
            (issued.status_code, mailbox.status_code, published.status_code),
            (values.STATUS_CREATED, values.STATUS_OK, values.STATUS_CREATED),
            msg=values.MSG_RQA_SERVICE_STATUSES,
            abort_on_fail=False,
        )
        for what, answer in (("read", mailbox), ("publish", published)):
            records = self.bloom.bloom_request_records(answer)
            self.assertEqual(
                [
                    (
                        r.actor_type,
                        r.actor_user_id,
                        r.details.get("service_credential_id"),
                        "client" in r.details,
                    )
                    for r in records
                ],
                [("service", None, credential["id"], False)],
                msg=values.MSG_RQA_SERVICE.format(what=what),
                abort_on_fail=False,
            )
        [read] = self.bloom.bloom_request_records(mailbox) or [None]
        self.assertEqual(
            read.details.get("query"),
            ["after_id"],
            msg=values.MSG_RQA_SERVICE_QUERY,
            abort_on_fail=False,
        )
        [created] = self.bloom.bloom_request_records(published) or [None]
        body = published.json()
        self.assertEqual(
            (created.details.get("created_id"), created.details.get("created_doc_id")),
            (body["document_id"], body["doc_id"]),
            msg=values.MSG_RQA_SERVICE_CREATED,
            abort_on_fail=False,
        )
        [issue] = self.bloom.bloom_request_records(issued) or [None]
        self.assertEqual(
            (issue.details.get("created_id"), credential["token"] in repr(issue.details)),
            (credential["id"], False),
            msg=values.MSG_RQA_ISSUED,
            abort_on_fail=False,
        )

    def bud_refused_attempts_are_denied_with_the_address(self):
        values, send = self.parameters, self.bloom.bloom_api_send
        address = values.RQA_REFUSED_ADDRESS
        forged = send("GET", "/api/projects", values.RQA_FORGED, address)
        forbidden = send("GET", f"/api/projects/{self.project}", self.member, address)
        hidden = send("GET", f"/api/designs/{self.design}", self.member, address)
        missing = send("GET", f"/api/designs/{values.RQA_MISSING_ID}", self.member, address)
        answers = (forged, forbidden, hidden, missing)
        self.print_variables({"statuses": [answer.status_code for answer in answers]})
        self.assertEqual(
            [answer.status_code for answer in answers],
            [
                values.STATUS_UNAUTHORIZED,
                values.STATUS_FORBIDDEN,
                values.STATUS_NOT_FOUND,
                values.STATUS_NOT_FOUND,
            ],
            msg=values.MSG_RQA_REFUSED_STATUSES,
            abort_on_fail=False,
        )
        records = {
            name: self.bloom.bloom_request_records(answer)
            for name, answer in zip(("forged", "forbidden", "hidden", "missing"), answers)
        }
        for what in ("forged", "forbidden", "hidden"):
            self.assertEqual(
                [(record.outcome, record.ip) for record in records[what]],
                [("denied", address)],
                msg=values.MSG_RQA_DENIED.format(what=what),
                abort_on_fail=False,
            )
        self.assertEqual(
            (
                [r.actor_type for r in records["forged"]],
                [r.project_id for r in records["forbidden"]],
                [r.target_id for r in records["hidden"]],
            ),
            (["anonymous"], [self.project], [str(self.design)]),
            msg=values.MSG_RQA_REFUSAL_DETAILS,
            abort_on_fail=False,
        )
        self.assertEqual(
            [r.outcome for r in records["missing"]],
            ["failure"],
            msg=values.MSG_RQA_MISSING,
            abort_on_fail=False,
        )

    def bud_rate_limited_sign_in_is_denied(self):
        values = self.parameters
        address = values.RQA_LIMITED_ADDRESS
        answers = self.bloom.bloom_sign_in_many_times_rate_limited(
            address, values.RQA_LOGIN_LIMIT + 1, values.RQA_WRONG_LOGIN
        )
        first, last = answers[0], answers[-1]
        self.print_variables({"statuses": [answer.status_code for answer in answers]})
        self.assertEqual(
            (first.status_code, last.status_code),
            (values.STATUS_UNAUTHORIZED, values.STATUS_TOO_MANY),
            msg=values.MSG_RQA_LIMITED,
            abort_on_fail=False,
        )
        records = self.bloom.bloom_request_records(first) + self.bloom.bloom_request_records(
            last, route="/api/auth/login"
        )
        self.assertEqual(
            [(record.outcome, record.ip) for record in records],
            [("denied", address), ("denied", address)],
            msg=values.MSG_RQA_LIMITED_DENIED,
            abort_on_fail=False,
        )

    def bud_repeated_refusals_are_detected_once_per_window(self):
        values, send = self.parameters, self.bloom.bloom_api_send
        address = values.RQA_REPEATED_ADDRESS
        threshold, window = self.bloom.bloom_refusal_window()
        detected = lambda: [
            e
            for e in self.bloom.bloom_list_audit_events("security.repeated_refusals")
            if e.ip == address
        ]
        for _ in range(threshold - 1):
            send("GET", "/api/projects", values.RQA_FORGED, address)
        below = detected()
        for _ in range(6):
            send("GET", "/api/projects", values.RQA_FORGED, address)
        after = detected()
        self.print_variables(
            {
                "threshold": threshold,
                "records below": len(below),
                "records after": [e.details for e in after],
            }
        )
        self.assertEqual(below, [], msg=values.MSG_RQA_BELOW, abort_on_fail=False)
        self.assertEqual(
            [(e.outcome, e.details) for e in after],
            [("denied", {"address": address, "count": threshold, "window_minutes": window})],
            msg=values.MSG_RQA_DETECTED,
            abort_on_fail=False,
        )
        self.assertEqual(
            len(self.bloom.bloom_request_records(outcome="denied", ip=address)),
            threshold + 5,
            msg=values.MSG_RQA_DENIED_COUNT,
            abort_on_fail=False,
        )

    def bud_refusals_outside_the_window_do_not_count(self):
        values, send = self.parameters, self.bloom.bloom_api_send
        address = values.RQA_WINDOW_ADDRESS
        self.bloom.bloom_set_refusal_threshold(values.RQA_WINDOW_THRESHOLD)
        self.bloom.bloom_add_old_refusals(address, values.RQA_OLD_REFUSALS, values.RQA_OLD_MINUTES)
        detected = lambda: [
            e
            for e in self.bloom.bloom_list_audit_events("security.repeated_refusals")
            if e.ip == address
        ]
        send("GET", "/api/projects", values.RQA_FORGED, address)
        first = len(detected())
        send("GET", "/api/projects", values.RQA_FORGED, address)
        send("GET", "/api/projects", values.RQA_FORGED, address)
        third = len(detected())
        self.print_variables({"records after one refusal": first, "after three": third})
        self.assertEqual(first, 0, msg=values.MSG_RQA_OLD, abort_on_fail=False)
        self.assertEqual(third, 1, msg=values.MSG_RQA_WINDOW, abort_on_fail=False)

    def bud_no_record_holds_a_password_token_or_query_value(self):
        values, send = self.parameters, self.bloom.bloom_api_send
        address = values.RQA_SECRET_ADDRESS
        token = self.admin["Authorization"].split()[1]
        send(
            "POST",
            "/api/auth/login",
            None,
            address,
            json={"email": values.RQA_ADMIN, "password": values.RQA_WRONG_PASSWORD},
        )
        searched = send(
            "GET", "/api/projects", self.admin, address, params={"search": values.RQA_SEARCH}
        )
        [record] = self.bloom.bloom_request_records(searched) or [None]
        self.assertEqual(
            (searched.status_code, record.details.get("query")),
            (values.STATUS_OK, ["search"]),
            msg=values.MSG_RQA_QUERY_NAMES,
            abort_on_fail=False,
        )
        stored = repr(
            [
                {column: str(getattr(event, column)) for column in self.bloom.bloom_audit_columns()}
                for event in self.bloom.bloom_list_every_audit_event()
            ]
        )
        for name, secret in (
            ("password", values.API_PASSWORD),
            ("wrong password", values.RQA_WRONG_PASSWORD),
            ("token", token),
            ("search text", values.RQA_SEARCH),
        ):
            self.assertNotIn(
                secret,
                stored,
                msg=values.MSG_RQA_NO_SECRET.format(secret=name),
                abort_on_fail=False,
            )

    def bud_health_probes_and_metrics_scrapes_are_recorded(self):
        values = self.parameters
        for route in ("/api/health", "/api/metrics"):
            answer = self.bloom.bloom_api_send("GET", route)
            records = self.bloom.bloom_request_records(answer, route=route, method="GET")
            self.assertEqual(
                [
                    (
                        r.actor_type,
                        r.details["auth"],
                        r.details["status"],
                        r.details["duration_ms"] >= 0,
                    )
                    for r in records
                ],
                [("anonymous", "none", answer.status_code, True)],
                msg=values.MSG_RQA_PROBE.format(route=route),
                abort_on_fail=False,
            )

    def bud_an_audit_write_failure_leaves_the_answer_unchanged(self):
        values = self.parameters
        before = len(self.bloom.bloom_list_audit_events(values.RQA_ACTION))
        answer, logged = self.bloom.bloom_send_while_audit_fails("/api/health")
        after = len(self.bloom.bloom_list_audit_events(values.RQA_ACTION))
        self.print_variables(
            {"status": answer.status_code, "records before": before, "after": after}
        )
        self.assertEqual(
            (answer.status_code, bool(answer.headers.get("x-request-id"))),
            (values.STATUS_OK, True),
            msg=values.MSG_RQA_WRITE_FAILED,
            abort_on_fail=False,
        )
        self.assertEqual(
            (after - before, values.RQA_FAILURE_LOG in logged),
            (0, True),
            msg=values.MSG_RQA_NOT_WRITTEN,
            abort_on_fail=False,
        )

    def bud_the_audit_log_filters_by_actor_type_address_request_and_status(self):
        values = self.parameters
        refused = self.bloom.bloom_api_send(
            "GET", "/api/projects", values.RQA_FORGED, values.RQA_FILTER_ADDRESS
        )
        page = lambda **query: self.bloom.bloom_api_audit(self.admin, limit=500, **query).body[
            "items"
        ]
        by_request = page(request_id=refused.headers["x-request-id"])
        self.assertEqual(
            [item["details"]["status"] for item in by_request],
            [values.STATUS_UNAUTHORIZED],
            msg=values.MSG_RQA_FILTER.format(field="request id"),
            abort_on_fail=False,
        )
        checks = (
            ("status", {item["details"]["status"] for item in page(status=401)}, {401}),
            (
                "actor type",
                {item["actor_type"] for item in page(actor_type="anonymous")},
                {"anonymous"},
            ),
            (
                "address",
                {item["ip"] for item in page(ip=values.RQA_FILTER_ADDRESS)},
                {values.RQA_FILTER_ADDRESS},
            ),
            (
                "action and outcome",
                {item["action"] for item in page(action="api.", outcome="denied")},
                {values.RQA_ACTION},
            ),
        )
        for field, actual, expected in checks:
            self.assertEqual(
                actual, expected, msg=values.MSG_RQA_FILTER.format(field=field), abort_on_fail=False
            )
        self.assertEqual(
            page(ip=values.RQA_UNKNOWN_ADDRESS),
            [],
            msg=values.MSG_RQA_FILTER_NONE,
            abort_on_fail=False,
        )

    def bud_route_templates_carry_their_prefix_and_outcomes_follow_the_status(self):
        values = self.parameters
        self.assertEqual(
            self.bloom.bloom_route_template(values.RQA_ROUTE_PATH),
            (values.RQA_ROUTE_TEMPLATE, "unmatched"),
            msg=values.MSG_RQA_TEMPLATE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_request_outcomes(values.RQA_OUTCOME_CODES),
            (values.RQA_OUTCOMES, "denied"),
            msg=values.MSG_RQA_OUTCOMES,
            abort_on_fail=False,
        )

    def bud_a_created_body_is_read_plain_or_gzip_and_bounded(self):
        self.assertEqual(
            self.bloom.bloom_read_created_bodies(),
            self.parameters.RQA_CREATED_BODIES,
            msg=self.parameters.MSG_RQA_BODIES,
            abort_on_fail=False,
        )

    def bud_the_actor_set_by_a_dependency_reaches_the_middleware(self):
        answer = self.bloom.bloom_api_send("GET", "/api/auth/me", self.member)
        records = self.bloom.bloom_request_records(answer, route="/api/auth/me")
        self.assertEqual(
            [(r.actor_type, r.actor_user_id) for r in records],
            [("user", self.member_id)],
            msg=self.parameters.MSG_RQA_DEPENDENCY_ACTOR,
            abort_on_fail=False,
        )

    def bud_an_allowed_cors_preflight_is_answered_by_the_cors_layer_alone(self):
        origin = self.bloom.bloom_cors_origin()
        before = len(self.bloom.bloom_request_records(method="OPTIONS"))
        answer = self.bloom.bloom_api_send(
            "OPTIONS",
            "/api/projects",
            {
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        after = len(self.bloom.bloom_request_records(method="OPTIONS"))
        self.print_variables({"status": answer.status_code, "headers": dict(answer.headers)})
        self.assertEqual(
            (
                answer.status_code,
                answer.headers.get("access-control-allow-origin"),
                "x-request-id" in answer.headers,
                after - before,
            ),
            (self.parameters.STATUS_OK, origin, False, 0),
            msg=self.parameters.MSG_RQA_PREFLIGHT,
            abort_on_fail=False,
        )

    def bud_a_refused_cors_preflight_is_answered_403_and_recorded_as_denied(self):
        values = self.parameters
        answer = self.bloom.bloom_api_send(
            "OPTIONS",
            "/api/projects",
            {"Origin": values.RQA_FOREIGN_ORIGIN, "Access-Control-Request-Method": "DELETE"},
        )
        records = self.bloom.bloom_request_records(answer, method="OPTIONS", status=403)
        self.assertEqual(
            (
                answer.status_code,
                "access-control-allow-origin" in answer.headers,
                [(r.outcome, r.actor_type, r.details["path"], bool(r.ip)) for r in records],
            ),
            (values.STATUS_FORBIDDEN, False, [("denied", "anonymous", "/api/projects", True)]),
            msg=values.MSG_RQA_REFUSED_PREFLIGHT,
            abort_on_fail=False,
        )

    def bud_a_request_from_a_foreign_origin_is_recorded_without_cors_permission(self):
        values = self.parameters
        answer = self.bloom.bloom_api_send(
            "GET", "/api/projects", {"Origin": values.RQA_FOREIGN_ORIGIN}
        )
        records = self.bloom.bloom_request_records(answer, route="/api/projects")
        self.assertEqual(
            (
                answer.status_code,
                "access-control-allow-origin" in answer.headers,
                [(r.outcome, r.actor_type, bool(r.ip)) for r in records],
            ),
            (values.STATUS_UNAUTHORIZED, False, [("denied", "anonymous", True)]),
            msg=values.MSG_RQA_FOREIGN,
            abort_on_fail=False,
        )

    def bud_a_cors_answer_keeps_its_headers_with_the_request_id(self):
        origin = self.bloom.bloom_cors_origin()
        answer = self.bloom.bloom_api_send("GET", "/api/health", {"Origin": origin})
        records = self.bloom.bloom_request_records(answer, route="/api/health")
        self.assertEqual(
            (
                answer.headers.get("access-control-allow-origin"),
                bool(answer.headers.get("x-request-id")),
                [r.outcome for r in records],
            ),
            (origin, True, ["success"]),
            msg=self.parameters.MSG_RQA_CORS_ID,
            abort_on_fail=False,
        )

    def bud_an_unhandled_error_leaves_a_failure_record_with_status_500(self):
        values = self.parameters
        answer = self.bloom.bloom_api_send("GET", values.RQA_EXPLODING_PATH, errors=False)
        records = self.bloom.bloom_request_records(
            answer, route=values.RQA_EXPLODING_PATH, status=500, method="GET"
        )
        self.print_variables(
            {"status": answer.status_code, "records": [r.details for r in records]}
        )
        self.assertEqual(
            (
                answer.status_code,
                [
                    (r.outcome, bool(r.request_id), values.RQA_EXPLOSION in repr(r.details))
                    for r in records
                ],
            ),
            (values.STATUS_SERVER_ERROR, [("failure", True, False)]),
            msg=values.MSG_RQA_500,
            abort_on_fail=False,
        )

    def bud_a_500_quotes_the_supplied_request_id_of_its_record(self):
        values = self.parameters
        answer = self.bloom.bloom_api_send(
            "GET", values.RQA_EXPLODING_PATH, {"X-Request-ID": values.RQA_SUPPLIED_ID}, errors=False
        )
        body = answer.json()
        records = self.bloom.bloom_request_records(
            answer, route=values.RQA_EXPLODING_PATH, status=500
        )
        self.print_variables({"body": body})
        self.assertEqual(
            (
                answer.status_code,
                answer.headers.get("x-request-id"),
                body["request_id"],
                values.RQA_QUOTE in body["detail"],
                [r.request_id for r in records],
            ),
            (
                values.STATUS_SERVER_ERROR,
                values.RQA_SUPPLIED_ID,
                values.RQA_SUPPLIED_ID,
                True,
                [values.RQA_SUPPLIED_ID],
            ),
            msg=values.MSG_RQA_500_ID,
            abort_on_fail=False,
        )

    def bud_a_deactivated_account_is_denied_and_named(self):
        values = self.parameters
        former = self.bloom.bloom_add_account(
            values.RQA_FORMER, values.API_PASSWORD, values.API_MEMBER_ROLE
        )
        headers = self.bloom.bloom_user_token_headers(former)
        self.bloom.bloom_deactivate(former)
        answer = self.bloom.bloom_api_send("GET", "/api/projects", headers)
        records = self.bloom.bloom_request_records(answer)
        self.assertEqual(
            (answer.status_code, [(r.actor_type, r.actor_user_id, r.outcome) for r in records]),
            (values.STATUS_FORBIDDEN, [("user", former, "denied")]),
            msg=values.MSG_RQA_DEACTIVATED,
            abort_on_fail=False,
        )

    def bud_another_users_notification_is_a_denied_404(self):
        values = self.parameters
        owner = self.bloom.bloom_add_account(
            values.RQA_OWNER, values.API_PASSWORD, values.API_MEMBER_ROLE
        )
        notification = self.bloom.bloom_add_notification(owner)
        hidden = self.bloom.bloom_api_send(
            "POST", f"/api/notifications/{notification}/read", self.member
        )
        missing = self.bloom.bloom_api_send(
            "POST", f"/api/notifications/{values.RQA_MISSING_ID}/read", self.member
        )
        self.assertEqual(
            (hidden.status_code, missing.status_code),
            (values.STATUS_NOT_FOUND, values.STATUS_NOT_FOUND),
            msg=values.MSG_RQA_NOTIFICATION,
            abort_on_fail=False,
        )
        self.assertEqual(
            (
                [r.outcome for r in self.bloom.bloom_request_records(hidden)],
                [r.outcome for r in self.bloom.bloom_request_records(missing)],
            ),
            (["denied"], ["failure"]),
            msg=values.MSG_RQA_NOTIFICATION_OUTCOMES,
            abort_on_fail=False,
        )

    def bud_a_404_is_denied_to_an_anonymous_caller_and_a_failure_to_a_signed_in_user(self):
        values, send = self.parameters, self.bloom.bloom_api_send
        scanned = send("GET", "/api/.env")
        unknown_route = send("GET", "/api/no-such-thing", self.member)
        missing_row = send("GET", f"/api/designs/{values.RQA_MISSING_ID}", self.member)
        answers = (scanned, unknown_route, missing_row)
        self.assertEqual(
            [answer.status_code for answer in answers],
            [values.STATUS_NOT_FOUND] * 3,
            msg=values.MSG_RQA_404_STATUSES,
            abort_on_fail=False,
        )
        records = [self.bloom.bloom_request_records(answer) for answer in answers]
        self.assertEqual(
            (
                [(r.actor_type, r.outcome, r.details["route"]) for r in records[0]],
                [(r.actor_type, r.details["auth"], r.outcome) for r in records[1]],
                [(r.actor_type, r.outcome) for r in records[2]],
            ),
            (
                [("anonymous", "denied", "unmatched")],
                [("anonymous", "bearer", "denied")],
                [("user", "failure")],
            ),
            msg=values.MSG_RQA_404,
            abort_on_fail=False,
        )
