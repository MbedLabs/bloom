"""
* @file     ${tests/api/report_requests.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests report requests: who may ask, the machine mailbox and the decisions.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the report requests.
"""

import base64

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ReportRequestsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_request_needs_a_visible_source_and_is_made_once(self):
        values = self.parameters
        for kind in values.RPQ_KINDS:
            world = self.bloom.bloom_new_report_request_world()
            body = {"source_kind": kind, "source_id": world.sources[kind], "run_id": values.RPQ_RUN}
            post = lambda who, sent: self.bloom.bloom_api_call(
                "POST", "/api/report-requests", who, json=sent
            )
            guarded = (
                post(None, body).status,
                post(world.outsider, body).status,
                post(world.reader, {**body, "run_id": values.RPQ_RUN + 1}).status,
            )
            self.assertEqual(
                guarded,
                (values.STATUS_UNAUTHORIZED, values.STATUS_NOT_FOUND, values.STATUS_NOT_FOUND),
                msg=values.MSG_RPQ_GUARDED.format(kind=kind),
                abort_on_fail=False,
                method="POST",
                endpoint="/api/report-requests",
            )
            first, again = post(world.reader, body), post(world.reader, body)
            seen_by_admin = self.bloom.bloom_api_call(
                "GET", "/api/report-requests", world.admin, params=body
            ).body
            self.assertEqual(
                (first.status, first.body["id"] == again.body["id"], seen_by_admin),
                (values.STATUS_CREATED, True, None),
                msg=values.MSG_RPQ_ONE.format(kind=kind),
                abort_on_fail=False,
            )
            mailbox = self.bloom.bloom_api_call(
                "GET", "/api/bud/report-requests", world.machine
            ).body
            self.assertEqual(
                (
                    self.bloom.bloom_api_call(
                        "GET", "/api/bud/report-requests", world.reader
                    ).status,
                    [row["requester_email"] for row in mailbox],
                ),
                (values.STATUS_UNAUTHORIZED, ["reader-1@example.com"]),
                msg=values.MSG_RPQ_MAILBOX,
                abort_on_fail=False,
                method="GET",
                endpoint="/api/bud/report-requests",
            )

    def bud_a_refusal_reaches_the_reader_with_its_reason(self):
        values = self.parameters
        world = self.bloom.bloom_new_report_request_world()
        body = {
            "source_kind": "test-case",
            "source_id": world.sources["test-case"],
            "run_id": values.RPQ_RUN,
        }
        row = self.bloom.bloom_api_call(
            "POST", "/api/report-requests", world.reader, json=body
        ).body
        path = f"/api/bud/report-requests/{row['id']}/refuse"
        blank = self.bloom.bloom_api_call(
            "POST", path, world.machine, json={"reason": " ", "publisher": "Publisher"}
        )
        self.assertEqual(
            blank.status,
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_RPQ_BLANK_REASON,
            abort_on_fail=False,
            method="POST",
            endpoint=path,
        )
        refused = self.bloom.bloom_api_call(
            "POST",
            path,
            world.machine,
            json={"reason": "Evidence incomplete", "publisher": "Publisher (Bud user #7)"},
        )
        state = self.bloom.bloom_api_call(
            "GET", "/api/report-requests", world.reader, params=body
        ).body
        self.assertEqual(
            (refused.status, state["status"], state["reason"], "publisher" in state),
            (values.STATUS_OK, "refused", "Evidence incomplete", False),
            msg=values.MSG_RPQ_REFUSED,
            abort_on_fail=False,
            method="POST",
            endpoint=path,
        )
        events = self.bloom.bloom_list_audit_events("report.refused")
        self.assertEqual(
            [(event.actor_type, event.details["bud_publisher"]) for event in events],
            [("service", "Publisher (Bud user #7)")],
            msg=values.MSG_RPQ_ATTRIBUTED,
            abort_on_fail=False,
        )

    def bud_only_the_report_of_the_requested_run_delivers(self):
        values = self.parameters
        world = self.bloom.bloom_new_report_request_world()
        body = {
            "source_kind": "test-case",
            "source_id": world.sources["test-case"],
            "run_id": values.RPQ_RUN,
        }
        row = self.bloom.bloom_api_call(
            "POST", "/api/report-requests", world.reader, json=body
        ).body
        unreadable = self.bloom.bloom_api_publish_report(world.machine, values.RPQ_RUN, "invalid")
        self.assertEqual(
            (
                unreadable.status,
                self.bloom.bloom_api_call(
                    "GET", "/api/report-requests", world.reader, params=body
                ).body["status"],
            ),
            (values.STATUS_UNPROCESSABLE, "pending"),
            msg=values.MSG_RPQ_BAD_FILE,
            abort_on_fail=False,
        )
        content = base64.b64encode(values.RPQ_PDF).decode()
        other = self.bloom.bloom_api_publish_report(world.machine, values.RPQ_RUN + 1, content)
        self.assertEqual(
            (
                other.status,
                self.bloom.bloom_api_call(
                    "GET", "/api/report-requests", world.reader, params=body
                ).body["status"],
            ),
            (values.STATUS_CREATED, "pending"),
            msg=values.MSG_RPQ_OTHER_RUN,
            abort_on_fail=False,
        )
        published = self.bloom.bloom_api_publish_report(world.machine, values.RPQ_RUN, content)
        state = self.bloom.bloom_api_call(
            "GET", "/api/report-requests", world.reader, params=body
        ).body
        self.assertEqual(
            (published.status, state["status"], state["doc_id"]),
            (values.STATUS_CREATED, "delivered", published.body["doc_id"]),
            msg=values.MSG_RPQ_DELIVERED,
            abort_on_fail=False,
        )
        late = self.bloom.bloom_api_call(
            "POST",
            f"/api/bud/report-requests/{row['id']}/refuse",
            world.machine,
            json={"reason": "Late refusal", "publisher": "Publisher"},
        )
        self.assertEqual(
            late.status,
            values.STATUS_CONFLICT,
            msg=values.MSG_RPQ_LATE_REFUSAL,
            abort_on_fail=False,
        )

    def bud_deletions_work_with_a_pending_request(self):
        values = self.parameters
        for target in ("project", "account"):
            world = self.bloom.bloom_new_report_request_world()
            body = {
                "source_kind": "test-case",
                "source_id": world.sources["test-case"],
                "run_id": values.RPQ_RUN,
            }
            self.bloom.bloom_api_call("POST", "/api/report-requests", world.reader, json=body)
            path = (
                f"/api/projects/{world.project}"
                if target == "project"
                else f"/api/users/{world.reader_id}"
            )
            deleted = self.bloom.bloom_api_call("DELETE", path, world.admin)
            self.assertEqual(
                (
                    deleted.status,
                    self.bloom.bloom_api_call(
                        "GET", "/api/bud/report-requests", world.machine
                    ).body,
                ),
                (values.STATUS_NO_CONTENT, []),
                msg=values.MSG_RPQ_DELETION.format(target=target),
                abort_on_fail=False,
                method="DELETE",
                endpoint=path,
            )

    def bud_deleting_a_delivered_report_keeps_the_request(self):
        values = self.parameters
        world = self.bloom.bloom_new_report_request_world()
        body = {
            "source_kind": "test-case",
            "source_id": world.sources["test-case"],
            "run_id": values.RPQ_RUN,
        }
        document = self.bloom.bloom_add_record(
            "Document",
            project_id=world.project,
            doc_id="PRJ-RPT-001",
            title="Report",
            doc_type="RPT",
        )
        self.bloom.bloom_add_record(
            "ReportRequest",
            project_id=world.project,
            bud_run_id=values.RPQ_RUN,
            requester_id=world.reader_id,
            status="delivered",
            document_id=document,
        )
        deleted = self.bloom.bloom_api_call("DELETE", f"/api/documents/{document}", world.admin)
        state = self.bloom.bloom_api_call(
            "GET", "/api/report-requests", world.reader, params=body
        ).body
        self.assertEqual(
            (deleted.status, state["status"], state["doc_id"]),
            (values.STATUS_NO_CONTENT, "delivered", None),
            msg=values.MSG_RPQ_HISTORY,
            abort_on_fail=False,
        )
