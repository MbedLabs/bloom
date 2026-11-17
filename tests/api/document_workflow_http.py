"""
* @file     ${tests/api/document_workflow_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests review, approval and archived content of controlled documents over HTTP.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the document workflow over HTTP.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocumentWorkflowHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_risk_keeps_its_operational_status_and_filters_by_it(self):
        values = self.parameters
        for status in values.DWH_RISK_STATUSES:
            self.bloom.bloom_new_workflow_world()
            risk = self.bloom.bloom_add_record(
                "RiskItem", project_id=1, risk_id="PRJ-RSK-001", title="Risk", status=status
            )
            self.bloom.bloom_add_record(
                "Requirement",
                project_id=1,
                req_id="PRJ-REQ-001",
                title="Requirement",
                status="Draft",
            )
            listed = self.bloom.bloom_api_call(
                "GET", "/api/projects/PRJ/docs", params={"type": "RSK", "status": status}
            )
            detail = self.bloom.bloom_api_call("GET", "/api/projects/PRJ/docs/risks/PRJ-RSK-001")
            self.assertEqual(
                (
                    listed.status,
                    listed.body["total"],
                    [(item["doc_id"], item["status"]) for item in listed.body["items"]],
                    detail.status,
                    detail.body["status"],
                    self.bloom.bloom_read_record("RiskItem", risk).status,
                    self.bloom.bloom_list_records("ArtefactWorkflow"),
                ),
                (
                    values.STATUS_OK,
                    1,
                    [("PRJ-RSK-001", status)],
                    values.STATUS_OK,
                    status,
                    status,
                    [],
                ),
                msg=values.MSG_DWH_RISK_STATUS.format(status=status),
                abort_on_fail=False,
            )

    def bud_an_unsupported_requirement_status_invents_no_draft(self):
        values = self.parameters
        for status in values.DWH_UNSUPPORTED_STATUSES:
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                "Requirement",
                project_id=1,
                req_id="PRJ-REQ-001",
                title="Preserved content",
                status=status,
                created_by_id=1,
            )
            path = f"/api/artefacts/requirement/{row}"
            state = self.bloom.bloom_api_call("GET", path + "/workflow")
            registry = self.bloom.bloom_api_call("GET", "/api/projects/PRJ/docs")
            drafts = self.bloom.bloom_api_call(
                "GET", "/api/projects/PRJ/docs", params={"status": "Draft"}
            ).body["total"]
            kept = self.bloom.bloom_read_record("Requirement", row)
            self.assertEqual(
                (
                    state.status,
                    state.body["phase"],
                    state.body["revision_number"],
                    self.bloom.bloom_list_records("ArtefactWorkflow"),
                    registry.body["items"][0]["status"],
                    drafts,
                    (kept.status, kept.title),
                ),
                (values.STATUS_OK, None, None, [], None, 0, (status, "Preserved content")),
                msg=values.MSG_DWH_UNSUPPORTED.format(status=status),
                abort_on_fail=False,
            )
            drafted = self.bloom.bloom_api_call("POST", path + "/draft").status
            kept = self.bloom.bloom_read_record("Requirement", row)
            state = self.bloom.bloom_api_call("GET", path + "/workflow").body
            self.assertEqual(
                (drafted, kept.status, kept.title, state["phase"], state["revision_number"]),
                (values.STATUS_OK, "Draft", "Preserved content", "Draft", 1),
                msg=values.MSG_DWH_DRAFTED.format(status=status),
                abort_on_fail=False,
            )

    def bud_a_legacy_change_status_stays_visible_and_filterable(self):
        values = self.parameters
        for status in values.DWH_LEGACY_CHANGE_STATUSES:
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                "ChangeRequest",
                project_id=1,
                change_id="PRJ-CHG-001",
                title="Legacy change",
                status=status,
            )
            listed = self.bloom.bloom_api_call(
                "GET", "/api/projects/PRJ/docs", params={"type": "CHG", "status": status}
            )
            state = self.bloom.bloom_api_call("GET", f"/api/artefacts/change/{row}/workflow")
            self.assertEqual(
                (
                    listed.status,
                    listed.body["items"][0]["status"],
                    state.status,
                    state.body["phase"],
                    state.body["revision_number"],
                    self.bloom.bloom_read_record("ChangeRequest", row).status,
                    self.bloom.bloom_list_records("ArtefactWorkflow"),
                ),
                (values.STATUS_OK, status, values.STATUS_OK, None, None, status, []),
                msg=values.MSG_DWH_LEGACY_CHANGE.format(status=status),
                abort_on_fail=False,
            )

    def bud_every_controlled_kind_has_a_creator_bound_workflow(self):
        values = self.parameters
        for slug, kind, fields, _, _ in values.DWH_KINDS:
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                kind, project_id=1, created_by_id=1, status="Draft", **fields
            )
            state = self.bloom.bloom_api_call("GET", f"/api/artefacts/{slug}/{row}/workflow")
            body = state.body
            self.assertEqual(
                (
                    state.status,
                    body["controlled"],
                    body["creator"]["id"],
                    body["created_by"]["id"],
                    body["assignee"]["id"],
                    body["phase"],
                    body["actions"]["comment"],
                    body["actions"]["request_review"],
                ),
                (values.STATUS_OK, True, 1, 1, 1, "Draft", True, True),
                msg=values.MSG_DWH_CONTROLLED.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_a_reading_administrator_cannot_comment_unassigned(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement", project_id=1, req_id="PRJ-REQ-001", title="Content", reviewer_id=2
        )
        path = f"/api/artefacts/requirement/{row}/comments"
        self.bloom.bloom_act_as(4)
        refused = self.bloom.bloom_api_call(
            "POST", path, json={"body": "Read is not review"}
        ).status
        self.bloom.bloom_act_as(2)
        allowed = self.bloom.bloom_api_call("POST", path, json={"body": "Assigned reviewer"})
        self.assertEqual(
            (refused, allowed.status, allowed.body["author_user_id"]),
            (values.STATUS_FORBIDDEN, values.STATUS_CREATED, 2),
            msg=values.MSG_DWH_READING_ADMIN,
            abort_on_fail=False,
        )

    def bud_creating_cannot_skip_the_draft_422(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        for route, payload, _ in values.DWH_CREATE_ROUTES:
            answer = self.bloom.bloom_api_call(
                "POST", route, json={"project_id": 1, "status": "Approved", **payload}
            )
            self.assertEqual(
                answer.status,
                values.STATUS_UNPROCESSABLE,
                msg=values.MSG_DWH_CREATE_DRAFT.format(route=route),
                abort_on_fail=False,
                method="POST",
                endpoint=route,
            )

    def bud_a_signed_approval_cannot_bypass_the_request_409(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Content",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        self.bloom.bloom_act_as(3)
        answer = self.bloom.bloom_api_call(
            "POST", f"/api/artefacts/requirement/{row}/sign-off", json={"step": "approve"}
        )
        stored = self.bloom.bloom_read_record("Requirement", row)
        self.assertEqual(
            (answer.status, stored.status, stored.approved_by_id),
            (values.STATUS_CONFLICT, "Draft", None),
            msg=values.MSG_DWH_DIRECT_APPROVAL,
            abort_on_fail=False,
        )

    def bud_review_approval_and_revision_keep_the_content(self):
        values = self.parameters
        for slug, kind, fields, route, code in values.DWH_KINDS:
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                kind, project_id=1, created_by_id=1, status="Draft", **fields
            )
            path = f"/api/artefacts/{slug}/{row}"
            self.bloom.bloom_api_call(
                "PUT", path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
            )
            self.bloom.bloom_act_as(2)
            self.bloom.bloom_api_call(
                "POST", path + "/comments", json={"body": "Comment before review request"}
            )
            self.bloom.bloom_act_as(1)
            requested = self.bloom.bloom_api_call(
                "POST", path + "/requests", json={"kind": "review"}
            ).status
            phase = self.bloom.bloom_read_record(kind, row).status
            repeat = self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
            events = [
                event["event_type"]
                for event in self.bloom.bloom_api_call("GET", path + "/activity").body
            ]
            self.assertEqual(
                (
                    requested,
                    phase,
                    repeat.status,
                    repeat.body["already_requested"],
                    events.count("review_requested"),
                    {"reviewed", "approved"} & set(events),
                ),
                (values.STATUS_CREATED, "Review", values.STATUS_OK, True, 1, set()),
                msg=values.MSG_DWH_REVIEW.format(kind=kind),
                abort_on_fail=False,
            )
            self.bloom.bloom_act_as(2)
            early = self.bloom.bloom_api_call(
                "POST", path + "/requests", json={"kind": "approval"}
            ).status
            self.bloom.bloom_api_call(
                "POST", path + "/comments", json={"body": "Reviewed the requested content"}
            )
            approval = self.bloom.bloom_api_call(
                "POST", path + "/requests", json={"kind": "approval"}
            ).status
            listed = self.bloom.bloom_api_call(
                "GET", "/api/projects/PRJ/docs", params={"status": "Approval"}
            ).body["items"]
            self.assertEqual(
                (early, approval, [(item["id"], item["status"]) for item in listed]),
                (values.STATUS_CONFLICT, values.STATUS_CREATED, [(row, "Approval")]),
                msg=values.MSG_DWH_APPROVAL.format(kind=kind),
                abort_on_fail=False,
            )
            self.bloom.bloom_act_as(4)
            outsider = self.bloom.bloom_api_call(
                "POST", path + "/sign-off", json={"step": "approve"}
            ).status
            self.bloom.bloom_act_as(3)
            signed = self.bloom.bloom_api_call("POST", path + "/sign-off", json={"step": "approve"})
            signoffs = sorted(
                (event["event_type"], event["actor_user_id"])
                for event in self.bloom.bloom_api_call("GET", path + "/activity").body
                if event["event_type"] in {"reviewed", "approved"}
            )
            archive = self.bloom.bloom_api_call("GET", path + "/revisions/1")
            title = "title" if "title" in fields else "name"
            self.assertEqual(
                (
                    outsider,
                    signed.status,
                    self.bloom.bloom_read_record(kind, row).status,
                    signed.body["reviewed_by_id"],
                    signed.body["approved_by_id"],
                    signoffs,
                    archive.body["snapshot"]["fields"][title],
                ),
                (
                    values.STATUS_FORBIDDEN,
                    values.STATUS_OK,
                    "Approved",
                    2,
                    3,
                    [("approved", 3), ("reviewed", 2)],
                    fields[title],
                ),
                msg=values.MSG_DWH_APPROVED.format(kind=kind),
                abort_on_fail=False,
            )
            change = self.bloom.bloom_add_record(
                "ChangeRequest",
                project_id=1,
                created_by_id=1,
                change_id="PRJ-CHG-900",
                title="Authorized change",
                status="Approved",
            )
            self.bloom.bloom_act_as(1)
            if slug != "change":
                link = {
                    "project_id": 1,
                    "source_type": "CHG",
                    "source_id": change,
                    "target_type": code,
                    "target_id": row,
                    "role": "impacts",
                }
                self.bloom.bloom_api_call("POST", "/api/links", json=link)
            reference = (
                self.bloom.bloom_read_record(kind, row).suite_id if slug == "test-suite" else row
            )
            saved = self.bloom.bloom_api_call(
                "PATCH", f"/api/{route}/{reference}", json={title: "Saved changed content"}
            )
            stored = self.bloom.bloom_read_record(kind, row)
            if slug == "change":
                self.assertEqual(
                    (saved.status, stored.status),
                    (values.STATUS_CONFLICT, "Approved"),
                    msg=values.MSG_DWH_CHANGE_FROZEN,
                    abort_on_fail=False,
                )
                continue
            state = self.bloom.bloom_api_call("GET", path + "/workflow").body
            self.assertEqual(
                (
                    saved.status,
                    stored.status,
                    state["revision_number"],
                    state["authorizing_change"]["id"],
                    stored.version if slug == "document" else "2",
                    state["reviewed_by"],
                    state["approved_by"],
                    self.bloom.bloom_api_call("GET", path + "/revisions/1").body == archive.body,
                ),
                (values.STATUS_OK, "Draft", 2, change, "2", None, None, True),
                msg=values.MSG_DWH_REVISED.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_an_edit_during_review_supersedes_the_request(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Original",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}"
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        self.bloom.bloom_act_as(2)
        self.bloom.bloom_api_call("POST", path + "/comments", json={"body": "Old content"})
        self.bloom.bloom_act_as(1)
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{row}", json={"title": "Changed"}
        ).status
        requests = self.bloom.bloom_list_records("ArtefactRequest")
        self.bloom.bloom_act_as(2)
        approval = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "approval"}
        ).status
        self.assertEqual(
            (
                edited,
                self.bloom.bloom_read_record("Requirement", row).status,
                requests[0].status,
                requests[0].decided_by_id,
                approval,
            ),
            (values.STATUS_OK, "Draft", "superseded", 1, values.STATUS_CONFLICT),
            msg=values.MSG_DWH_SUPERSEDED,
            abort_on_fail=False,
        )

    def bud_an_unassigned_review_notifies_without_assigning(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement", project_id=1, req_id="PRJ-REQ-001", title="Content", created_by_id=1
        )
        path = f"/api/artefacts/requirement/{row}"
        offered = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"][
            "request_review"
        ]
        requested = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "review"}
        ).status
        recipients = {
            entry.user_id for entry in self.bloom.bloom_list_records("ArtefactRequestRecipient")
        }
        self.bloom.bloom_act_as(2)
        actions = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"]
        refused = self.bloom.bloom_api_call(
            "POST", path + "/comments", json={"body": "Unassigned recipient"}
        ).status
        self.bloom.bloom_act_as(1)
        assigned = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", json={"reviewer_id": 2}
        ).status
        self.bloom.bloom_act_as(2)
        comment = self.bloom.bloom_api_call(
            "POST", path + "/comments", json={"body": "Assigned review"}
        ).status
        self.assertEqual(
            (
                offered,
                requested,
                recipients,
                actions["decline"],
                actions["comment"],
                refused,
                assigned,
                comment,
            ),
            (
                True,
                values.STATUS_CREATED,
                {1, 2, 3, 4},
                True,
                False,
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                values.STATUS_CREATED,
            ),
            msg=values.MSG_DWH_UNASSIGNED_REVIEW,
            abort_on_fail=False,
        )

    def bud_an_inactive_reviewer_falls_back_to_visible_recipients(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_change_record("User", 2, is_active=False)
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Content",
            created_by_id=1,
            reviewer_id=2,
        )
        path = f"/api/artefacts/requirement/{row}"
        request = self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        recipients = {
            entry.user_id for entry in self.bloom.bloom_list_records("ArtefactRequestRecipient")
        }
        self.bloom.bloom_act_as(3)
        offered = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"]["decline"]
        declined = self.bloom.bloom_api_call(
            "POST", f"/api/artefact-requests/{request.body['id']}/decline"
        ).status
        self.assertEqual(
            (
                request.status,
                recipients,
                offered,
                declined,
                self.bloom.bloom_read_record("Requirement", row).status,
            ),
            (values.STATUS_CREATED, {1, 3, 4}, True, values.STATUS_OK, "Draft"),
            msg=values.MSG_DWH_FALLBACK,
            abort_on_fail=False,
        )

    def bud_an_inactive_approver_falls_back_to_another_administrator(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_change_record("User", 3, is_active=False)
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Content",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}"
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        self.bloom.bloom_act_as(2)
        self.bloom.bloom_api_call("POST", path + "/comments", json={"body": "Assigned review"})
        approval = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "approval"}
        ).status
        self.bloom.bloom_act_as(4)
        offered = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"]["approve"]
        approved = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", json={"step": "approve"}
        ).status
        self.assertEqual(
            (
                approval,
                offered,
                approved,
                self.bloom.bloom_read_record("Requirement", row).approved_by_id,
            ),
            (values.STATUS_CREATED, True, values.STATUS_OK, 4),
            msg=values.MSG_DWH_APPROVER_FALLBACK,
            abort_on_fail=False,
        )

    def bud_an_external_reviewer_has_no_implicit_read(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_set_account_role(4, "external")
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Customer document",
            visibility="customer",
            created_by_id=1,
            reviewer_id=4,
        )
        internal = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-002",
            title="Internal document",
            visibility="internal",
            created_by_id=1,
            reviewer_id=4,
        )
        policy = self.bloom.bloom_add_access_entry(4, 1, {"REQ": ["review"]}, "customer")
        path = f"/api/artefacts/requirement/{row}"
        self.bloom.bloom_act_as(4)
        hidden = self.bloom.bloom_api_call("GET", path + "/workflow").status
        self.bloom.bloom_set_policy_permissions(policy, {"REQ": ["view", "review"]})
        shown = self.bloom.bloom_api_call("GET", path + "/workflow")
        commented = self.bloom.bloom_api_call(
            "POST", path + "/comments", json={"body": "Customer review"}
        ).status
        internal_comment = self.bloom.bloom_api_call(
            "POST", f"/api/artefacts/requirement/{internal}/comments", json={"body": "Hidden"}
        ).status
        self.bloom.bloom_set_policy_permissions(policy, {"REQ": ["view"]})
        revoked = self.bloom.bloom_api_call(
            "POST", path + "/comments", json={"body": "Review revoked"}
        ).status
        self.assertEqual(
            (
                hidden,
                shown.status,
                shown.body["actions"]["comment"],
                commented,
                internal_comment,
                revoked,
            ),
            (
                values.STATUS_NOT_FOUND,
                values.STATUS_OK,
                True,
                values.STATUS_CREATED,
                values.STATUS_NOT_FOUND,
                values.STATUS_FORBIDDEN,
            ),
            msg=values.MSG_DWH_EXTERNAL_READ,
            abort_on_fail=False,
        )

    def bud_deleting_a_project_keeps_the_approved_history(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Preserved",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}"
        self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
        )
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        self.bloom.bloom_act_as(2)
        self.bloom.bloom_api_call("POST", path + "/comments", json={"body": "Reviewed"})
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "approval"})
        self.bloom.bloom_act_as(3)
        signed = self.bloom.bloom_api_call("POST", path + "/sign-off", json={"step": "approve"})
        self.bloom.bloom_act_as(1)
        original = self.bloom.bloom_list_records("ArtefactRevision")[0].content_snapshot
        removed = self.bloom.bloom_api_call("DELETE", "/api/projects/1").status
        state = self.bloom.bloom_list_records("ArtefactWorkflow")[0]
        revision = self.bloom.bloom_list_records("ArtefactRevision")[0]
        self.assertEqual(
            (
                signed.status,
                removed,
                state.project_id,
                revision.content_snapshot == original,
                self.bloom.bloom_api_call("GET", path + "/revisions/1").status,
            ),
            (values.STATUS_OK, values.STATUS_NO_CONTENT, None, True, values.STATUS_NOT_FOUND),
            msg=values.MSG_DWH_PROJECT_DELETION,
            abort_on_fail=False,
        )

    def bud_an_external_owner_needs_a_review_policy_and_assignment(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_set_account_role(4, "external")
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Customer review",
            visibility="customer",
            created_by_id=1,
            reviewer_id=4,
        )
        policy = self.bloom.bloom_add_access_entry(4, 1, {"REQ": ["view"]}, "customer", owner=True)
        path = f"/api/artefacts/requirement/{row}/comments"
        self.bloom.bloom_act_as(4)
        denied = self.bloom.bloom_api_call("POST", path, json={"body": "No Review policy"}).status
        self.bloom.bloom_set_policy_permissions(policy, {"REQ": ["view", "review"]})
        allowed = self.bloom.bloom_api_call(
            "POST", path, json={"body": "Policy granted and assigned"}
        ).status
        self.bloom.bloom_change_record("Requirement", row, reviewer_id=2)
        unassigned = self.bloom.bloom_api_call("POST", path, json={"body": "Not assigned"}).status
        self.assertEqual(
            (denied, allowed, unassigned),
            (values.STATUS_FORBIDDEN, values.STATUS_CREATED, values.STATUS_FORBIDDEN),
            msg=values.MSG_DWH_EXTERNAL_OWNER,
            abort_on_fail=False,
        )

    def bud_controlled_creation_is_a_draft_owned_by_the_creator(self):
        values = self.parameters
        for route, payload, slug in values.DWH_CREATE_ROUTES + values.DWH_DOCUMENT_ROUTES:
            self.bloom.bloom_new_workflow_world()
            created = self.bloom.bloom_api_call("POST", route, json={"project_id": 1, **payload})
            workflow = self.bloom.bloom_api_call(
                "GET", f"/api/artefacts/{slug}/{created.body['id']}/workflow"
            )
            self.assertEqual(
                (
                    created.status,
                    created.body["status"],
                    workflow.status,
                    workflow.body["creator"]["id"],
                ),
                (values.STATUS_CREATED, "Draft", values.STATUS_OK, 1),
                msg=values.MSG_DWH_CREATED.format(kind=payload.get("doc_type", slug)),
                abort_on_fail=False,
                method="POST",
                endpoint=route,
            )

    def bud_project_deletion_removes_only_its_notifications(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_add_record("Project", id=2, name="ABC", prefix="ABC")
        removed = self.bloom.bloom_add_record(
            "Notification",
            user_id=1,
            project_id=1,
            event_type="review",
            title="Pending project review",
        )
        retained = self.bloom.bloom_add_record(
            "Notification", user_id=1, event_type="account", title="Account notification"
        )
        other = self.bloom.bloom_add_record(
            "Notification",
            user_id=1,
            project_id=2,
            event_type="review",
            title="Other project review",
        )
        self.bloom.bloom_set_account_role(4, "maintainer")
        self.bloom.bloom_act_as(4)
        refused = self.bloom.bloom_api_call("DELETE", "/api/projects/1").status
        before = [row.id for row in self.bloom.bloom_list_records("Notification")]
        self.bloom.bloom_act_as(1)
        deleted = self.bloom.bloom_api_call("DELETE", "/api/projects/1").status
        after = [row.id for row in self.bloom.bloom_list_records("Notification")]
        self.assertEqual(
            (refused, before, deleted, after),
            (
                values.STATUS_FORBIDDEN,
                [removed, retained, other],
                values.STATUS_NO_CONTENT,
                [retained, other],
            ),
            msg=values.MSG_DWH_NOTIFICATIONS,
            abort_on_fail=False,
        )

    def bud_deleting_the_requester_keeps_the_approved_identity(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Approved content",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}"
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        self.bloom.bloom_act_as(2)
        comment = self.bloom.bloom_api_call(
            "POST", path + "/comments", json={"body": "Reviewed"}
        ).body["id"]
        approval = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "approval"}
        ).body["id"]
        self.bloom.bloom_act_as(3)
        self.bloom.bloom_api_call("POST", path + "/sign-off", json={"step": "approve"})
        snapshot = self.bloom.bloom_list_records("ArtefactRevision")[0].content_snapshot
        self.bloom.bloom_act_as(4)
        deleted = self.bloom.bloom_api_call("DELETE", "/api/users/1").status
        retained = self.bloom.bloom_list_records("ArtefactRevision")[0]
        identities = retained.content_snapshot["signoff_identities"]
        self.assertEqual(
            (
                deleted,
                [request.id for request in self.bloom.bloom_list_records("ArtefactRequest")],
                retained.content_snapshot == snapshot,
                (retained.reviewed_by_id, retained.approved_by_id),
                (identities["2"]["full_name"], identities["3"]["full_name"]),
                self.bloom.bloom_read_record("ArtefactComment", comment).review_request_id,
            ),
            (values.STATUS_NO_CONTENT, [approval], True, (2, 3), ("Person 2", "Person 3"), None),
            msg=values.MSG_DWH_REQUESTER_DELETED,
            abort_on_fail=False,
        )

    def bud_pending_requests_follow_origin_membership_and_review(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_set_account_role(4, "external")
        policy = self.bloom.bloom_add_access_entry(4, 1, {"REQ": ["view", "review"]}, "customer")
        customer = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Visible request",
            visibility="customer",
            created_by_id=1,
            reviewer_id=4,
        )
        internal = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-002",
            title="Hidden request",
            visibility="internal",
            created_by_id=1,
            reviewer_id=2,
        )
        self.bloom.bloom_add_record("Project", id=2, name="ABC", prefix="ABC")
        for row in (customer, internal):
            self.bloom.bloom_api_call(
                "POST", f"/api/artefacts/requirement/{row}/requests", json={"kind": "review"}
            )
        self.bloom.bloom_act_as(4)
        visible = self.bloom.bloom_api_call("GET", "/api/projects/1/artefact-requests")
        other = self.bloom.bloom_api_call("GET", "/api/projects/2/artefact-requests").status
        self.bloom.bloom_set_policy_permissions(policy, {"REQ": ["view"]})
        revoked = self.bloom.bloom_api_call("GET", "/api/projects/1/artefact-requests")
        self.assertEqual(
            (
                visible.status,
                [(item["public_id"], item["doc_type"]) for item in visible.body],
                other,
                revoked.status,
                revoked.body,
            ),
            (
                values.STATUS_OK,
                [("PRJ-REQ-001", "REQ")],
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                [],
            ),
            msg=values.MSG_DWH_PENDING,
            abort_on_fail=False,
        )

    def bud_a_review_request_is_mailed_once_and_a_decline_answers_it(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Review delivery",
            created_by_id=1,
            reviewer_id=2,
        )
        path = f"/api/artefacts/requirement/{row}/requests"
        first = self.bloom.bloom_api_call("POST", path, json={"kind": "review"})
        sent = self.bloom.bloom_list_deliveries()
        repeat = self.bloom.bloom_api_call("POST", path, json={"kind": "review"})
        repeated = (
            len(self.bloom.bloom_list_deliveries()),
            len(self.bloom.bloom_list_records("Notification")),
        )
        self.bloom.bloom_act_as(2)
        declined = self.bloom.bloom_api_call(
            "POST", f"/api/artefact-requests/{first.body['id']}/decline"
        ).status
        request = self.bloom.bloom_read_record("ArtefactRequest", first.body["id"])
        self.assertEqual(
            (
                first.status,
                [message["to_email"] for message in sent],
                sent[0]["subject"],
                "Review requested: PRJ-REQ-001" in sent[0]["text_body"],
                "<title>Bloom PLM by EmbedLabs</title>" in sent[0]["html_body"]
                and "PRJ-REQ-001" in sent[0]["html_body"],
                (repeat.status, repeat.body["already_requested"]),
                repeated,
                declined,
                [message["to_email"] for message in self.bloom.bloom_list_deliveries()],
                (request.status, request.decided_by_id, request.decided_at is not None),
            ),
            (
                values.STATUS_CREATED,
                ["person2@example.com"],
                "Review requested: PRJ-REQ-001",
                True,
                True,
                (values.STATUS_OK, True),
                (1, 1),
                values.STATUS_OK,
                ["person2@example.com", "person1@example.com"],
                ("declined", 2, True),
            ),
            msg=values.MSG_DWH_DELIVERY,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_list_audit_events_like("workflow."),
            [("workflow.requested", 1), ("workflow.declined", 2)],
            msg=values.MSG_DWH_DELIVERY_AUDIT,
            abort_on_fail=False,
        )

    def bud_operational_kinds_keep_their_status_and_need_an_assigned_reviewer(self):
        values = self.parameters
        for slug, kind, fields in values.DWH_OPERATIONAL:
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(kind, project_id=1, created_by_id=1, **fields)
            status = self.bloom.bloom_read_record(kind, row).status
            path = f"/api/artefacts/{slug}/{row}"
            denied = self.bloom.bloom_api_call(
                "POST", path + "/comments", json={"body": "Not assigned"}
            ).status
            assigned = self.bloom.bloom_api_call(
                "PUT", path + "/workflow/assignees", json={"reviewer_id": 2}
            ).status
            self.bloom.bloom_act_as(2)
            allowed = self.bloom.bloom_api_call(
                "POST", path + "/comments", json={"body": "Assigned reviewer"}
            ).status
            workflow = self.bloom.bloom_api_call("GET", path + "/workflow").body
            self.bloom.bloom_act_as(3)
            unassigned = self.bloom.bloom_api_call(
                "POST", path + "/comments", json={"body": "Unassigned admin"}
            ).status
            self.assertEqual(
                (
                    denied,
                    assigned,
                    allowed,
                    workflow["controlled"],
                    workflow["status"],
                    self.bloom.bloom_read_record(kind, row).status,
                    workflow["actions"]["request_review"],
                    unassigned,
                ),
                (
                    values.STATUS_FORBIDDEN,
                    values.STATUS_OK,
                    values.STATUS_CREATED,
                    False,
                    status,
                    status,
                    False,
                    values.STATUS_FORBIDDEN,
                ),
                msg=values.MSG_DWH_OPERATIONAL.format(kind=fields.get("doc_type", kind)),
                abort_on_fail=False,
            )

    def bud_a_correction_of_approved_content_is_reapproved_without_a_new_number(self):
        values = self.parameters
        for slug, kind, fields, route, _ in values.DWH_KINDS[:-1]:
            self.bloom.bloom_new_workflow_world()
            self.bloom.bloom_add_record(
                "ChangeRequest",
                project_id=1,
                change_id="PRJ-CHG-UNLINKED",
                title="Unlinked approved change",
                status="Approved",
            )
            row = self.bloom.bloom_add_record(
                kind, project_id=1, created_by_id=1, status="Approved", **fields
            )
            title = "title" if "title" in fields else "name"
            path = f"/api/artefacts/{slug}/{row}"
            stored = self.bloom.bloom_read_record(kind, row)
            reference = stored.suite_id if slug == "test-suite" else row
            version = getattr(stored, "version", None)
            offered = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"][
                "edit_current"
            ]
            same = self.bloom.bloom_api_call(
                "PATCH", f"/api/{route}/{reference}", json={title: fields[title]}
            ).status
            unchanged = self.bloom.bloom_read_record(kind, row).status
            unknown_change = self.bloom.bloom_api_call(
                "POST", path + "/revisions", json={"change_request_id": 9999}
            ).status
            self.bloom.bloom_act_as(4)
            corrected = self.bloom.bloom_api_call(
                "PATCH", f"/api/{route}/{reference}", json={title: "Corrected mistake"}
            ).status
            state = self.bloom.bloom_api_call("GET", path + "/workflow").body
            original = self.bloom.bloom_api_call("GET", path + "/revisions/1").body
            self.assertEqual(
                (
                    offered,
                    same,
                    unchanged,
                    unknown_change,
                    corrected,
                    (
                        state["phase"],
                        state["revision_number"],
                        state["creator"]["id"],
                        state["assignee"]["id"],
                    ),
                    (state["reviewed_by"], state["approved_by"]),
                    getattr(self.bloom.bloom_read_record(kind, row), "version", None) == version,
                    original["snapshot"]["fields"][title],
                ),
                (
                    True,
                    values.STATUS_OK,
                    "Approved",
                    values.STATUS_CONFLICT,
                    values.STATUS_OK,
                    ("Draft", 1, 4, 1),
                    (None, None),
                    True,
                    fields[title],
                ),
                msg=values.MSG_DWH_CORRECTION.format(kind=kind),
                abort_on_fail=False,
            )
            self.bloom.bloom_api_call(
                "PUT", path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
            )
            self.bloom.bloom_act_as(1)
            self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
            self.bloom.bloom_act_as(2)
            self.bloom.bloom_api_call(
                "POST", path + "/comments", json={"body": "Checked correction"}
            )
            self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "approval"})
            self.bloom.bloom_act_as(3)
            approved = self.bloom.bloom_api_call(
                "POST", path + "/sign-off", json={"step": "approve"}
            ).status
            state = self.bloom.bloom_api_call("GET", path + "/workflow").body
            self.assertEqual(
                (
                    approved,
                    state["phase"],
                    state["revision_number"],
                    getattr(self.bloom.bloom_read_record(kind, row), "version", None) == version,
                    self.bloom.bloom_api_call("GET", path + "/revisions/1").body == original,
                ),
                (values.STATUS_OK, "Approved", 1, True, True),
                msg=values.MSG_DWH_REAPPROVED.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_a_used_change_authorises_one_revision(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Document",
            project_id=1,
            doc_id="PRJ-SPEC-001",
            doc_type="SPEC",
            title="Approved",
            status="Approved",
            version="1.0",
            created_by_id=1,
        )
        change = self.bloom.bloom_add_record(
            "ChangeRequest",
            project_id=1,
            change_id="PRJ-CHG-001",
            title="Authorized",
            status="Approved",
        )
        link = {
            "project_id": 1,
            "source_type": "CHG",
            "source_id": change,
            "target_type": "SPEC",
            "target_id": row,
            "role": "impacts",
        }
        self.bloom.bloom_api_call("POST", "/api/links", json=link)
        first = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/documents/{row}",
            json={"title": "Changed", "status": "Approved", "version": "1.0"},
        ).status
        after_first = (
            self.bloom.bloom_read_record("Document", row).version,
            self.bloom.bloom_read_record("Document", row).status,
        )
        self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{row}", json={"title": "Further correction"}
        )
        path = f"/api/artefacts/document/{row}"
        state = self.bloom.bloom_api_call("GET", path + "/workflow").body
        stay = (
            state["revision_number"],
            self.bloom.bloom_read_record("Document", row).version,
            state["authorizing_change"]["id"],
        )
        self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
        )
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        self.bloom.bloom_act_as(2)
        self.bloom.bloom_api_call("POST", path + "/comments", json={"body": "Reviewed"})
        self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "approval"})
        self.bloom.bloom_act_as(3)
        signed = self.bloom.bloom_api_call("POST", path + "/sign-off", json={"step": "approve"})
        self.bloom.bloom_act_as(1)
        retained = self.bloom.bloom_api_call("GET", path + "/revisions/2").body
        self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{row}", json={"title": "Corrected after approval"}
        )
        state = self.bloom.bloom_api_call("GET", path + "/workflow").body
        corrected = (
            state["phase"],
            state["revision_number"],
            self.bloom.bloom_read_record("Document", row).version,
            self.bloom.bloom_api_call("GET", path + "/revisions/2").body == retained,
        )
        next_change = self.bloom.bloom_add_record(
            "ChangeRequest",
            project_id=1,
            change_id="PRJ-CHG-002",
            title="Next change",
            status="Approved",
        )
        self.bloom.bloom_api_call("POST", "/api/links", json={**link, "source_id": next_change})
        self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{row}", json={"title": "Next authorized change"}
        )
        state = self.bloom.bloom_api_call("GET", path + "/workflow").body
        self.assertEqual(
            (
                first,
                after_first,
                stay,
                signed.status,
                corrected,
                (
                    state["revision_number"],
                    self.bloom.bloom_read_record("Document", row).version,
                    state["authorizing_change"]["id"],
                ),
            ),
            (
                values.STATUS_OK,
                ("2", "Draft"),
                (2, "2", change),
                values.STATUS_OK,
                ("Draft", 2, "2", True),
                (3, "3", next_change),
            ),
            msg=values.MSG_DWH_USED_CHANGE,
            abort_on_fail=False,
        )

    def bud_an_unapproved_change_cannot_authorise_a_revision_409(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-001",
            title="Approved",
            status="Approved",
            created_by_id=1,
        )
        change = self.bloom.bloom_add_record(
            "ChangeRequest", project_id=1, change_id="PRJ-CHG-001", title="Pending", status="Draft"
        )
        self.bloom.bloom_api_call(
            "POST",
            "/api/links",
            json={
                "project_id": 1,
                "source_type": "CHG",
                "source_id": change,
                "target_type": "REQ",
                "target_id": row,
                "role": "impacts",
            },
        )
        refused = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{row}", json={"title": "Unauthorized change"}
        ).status
        stored = self.bloom.bloom_read_record("Requirement", row)
        state = self.bloom.bloom_api_call("GET", f"/api/artefacts/requirement/{row}/workflow").body
        self.assertEqual(
            (refused, stored.title, stored.status, state["revision_number"], state["revisions"]),
            (values.STATUS_CONFLICT, "Approved", "Approved", 1, []),
            msg=values.MSG_DWH_UNAPPROVED_CHANGE,
            abort_on_fail=False,
        )

    def bud_a_version_cannot_change_without_authorisation_409(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Document",
            project_id=1,
            doc_id="PRJ-SPEC-001",
            doc_type="SPEC",
            title="Approved",
            status="Approved",
            version="1",
            created_by_id=1,
        )
        refused = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{row}", json={"version": "4"}
        ).status
        stored = self.bloom.bloom_read_record("Document", row)
        self.assertEqual(
            (refused, stored.version, stored.status),
            (values.STATUS_CONFLICT, "1", "Approved"),
            msg=values.MSG_DWH_VERSION,
            abort_on_fail=False,
        )

    def bud_the_assignee_is_handed_over_and_requests_review(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-901",
            title="Assigned",
            status="Draft",
            created_by_id=1,
        )
        path = f"/api/artefacts/requirement/{row}"
        state = self.bloom.bloom_api_call("GET", path + "/workflow").body
        handed = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", json={"assignee_id": 2}
        )
        notices = self.bloom.bloom_list_records("Notification", user_id=2)
        self.bloom.bloom_act_as(2)
        requested = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "review"}
        ).status
        self.bloom.bloom_act_as(1)
        back = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", json={"assignee_id": 3}
        )
        self.assertEqual(
            (
                state["assignee"]["id"],
                state["actions"]["assign_assignee"],
                {person["id"] for person in state["options"]["assignees"]},
                (
                    handed.status,
                    handed.body["assignee"]["id"],
                    handed.body["actions"]["request_review"],
                ),
                [notice.link_path for notice in notices],
                requested,
                (back.status, back.body["assignee"]["id"]),
            ),
            (
                1,
                True,
                {1, 2, 3, 4},
                (values.STATUS_OK, 2, True),
                [values.DWH_REQUIREMENT_LINK.format(req_id="PRJ-REQ-901")],
                values.STATUS_CREATED,
                (values.STATUS_OK, 3),
            ),
            msg=values.MSG_DWH_HANDOVER,
            abort_on_fail=False,
        )

    def bud_an_assignee_must_be_able_to_edit_422(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        self.bloom.bloom_change_record("User", 4, is_active=False)
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-902",
            title="Assigned",
            status="Draft",
            created_by_id=1,
        )
        path = f"/api/artefacts/requirement/{row}/workflow/assignees"
        refused = [
            self.bloom.bloom_api_call("PUT", path, json={"assignee_id": value}).status
            for value in (4, None, 999)
        ]
        defect = self.bloom.bloom_add_record(
            "Defect", project_id=1, defect_id="PRJ-DEF-902", title="Operational", created_by_id=1
        )
        on_defect = self.bloom.bloom_api_call(
            "PUT", f"/api/artefacts/defect/{defect}/workflow/assignees", json={"assignee_id": 2}
        ).status
        self.assertEqual(
            (refused, on_defect),
            ([values.STATUS_UNPROCESSABLE] * 3, values.STATUS_UNPROCESSABLE),
            msg=values.MSG_DWH_ASSIGNEE_REFUSED,
            abort_on_fail=False,
        )

    def bud_who_may_change_the_assignee(self):
        may = self.bloom.bloom_may_change_assignee
        self.assertEqual(
            (may(1, 1, 2, False), may(2, 1, 2, False), may(3, 1, 2, True), may(3, 1, 2, False)),
            (True, True, True, False),
            msg=self.parameters.MSG_DWH_MAY_CHANGE,
            abort_on_fail=False,
        )

    def bud_the_four_comment_until_approval(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-903",
            title="Discussed",
            status="Draft",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}"
        self.bloom.bloom_api_call("PUT", path + "/workflow/assignees", json={"assignee_id": 4})
        posted = []
        for author in (1, 4, 3, 2):
            self.bloom.bloom_act_as(author)
            posted.append(
                self.bloom.bloom_api_call(
                    "POST", path + "/comments", json={"body": f"From {author}"}
                ).status
            )
        notices = self.bloom.bloom_list_records("Notification", event_type="comment")
        received = {}
        for notice in notices:
            received[notice.user_id] = received.get(notice.user_id, 0) + 1
        self.assertEqual(
            (posted, received, {notice.link_path for notice in notices}),
            (
                [values.STATUS_CREATED] * 4,
                {1: 3, 2: 3, 3: 3, 4: 3},
                {values.DWH_REQUIREMENT_LINK.format(req_id="PRJ-REQ-903")},
            ),
            msg=values.MSG_DWH_DISCUSSION,
            abort_on_fail=False,
        )
        approved = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-904",
            title="Approved",
            status="Approved",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        answers = []
        for author in (1, 3, 4, 2):
            self.bloom.bloom_act_as(author)
            answers.append(
                self.bloom.bloom_api_call(
                    "POST",
                    f"/api/artefacts/requirement/{approved}/comments",
                    json={"body": "After approval"},
                ).status
            )
        self.assertEqual(
            answers,
            [
                values.STATUS_FORBIDDEN,
                values.STATUS_FORBIDDEN,
                values.STATUS_FORBIDDEN,
                values.STATUS_CREATED,
            ],
            msg=values.MSG_DWH_AFTER_APPROVAL,
            abort_on_fail=False,
        )

    def bud_every_new_workflow_starts_with_the_creator_as_assignee(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        legacy = self.bloom.bloom_add_record(
            "ChangeRequest",
            project_id=1,
            change_id="PRJ-CHG-905",
            title="Legacy",
            status="Submitted",
            created_by_id=1,
        )
        reviewed = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-905",
            title="In review",
            status="Review",
            created_by_id=1,
        )
        assignee = self.bloom.bloom_api_call(
            "GET", f"/api/artefacts/change/{legacy}/workflow"
        ).body["assignee"]["id"]
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{reviewed}", json={"title": "Changed"}
        ).status
        workflows = self.bloom.bloom_list_records(
            "ArtefactWorkflow", artefact_type="requirement", artefact_id=reviewed
        )
        self.assertEqual(
            (assignee, edited, [workflow.assignee_id for workflow in workflows]),
            (1, values.STATUS_OK, [1]),
            msg=values.MSG_DWH_NEW_WORKFLOW,
            abort_on_fail=False,
        )

    def bud_an_assignee_change_is_recorded_and_refused_to_an_outsider(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-906",
            title="Recorded",
            status="Draft",
            created_by_id=1,
        )
        changed = self.bloom.bloom_api_call(
            "PUT", f"/api/artefacts/requirement/{row}/workflow/assignees", json={"assignee_id": 2}
        ).status
        activity = self.bloom.bloom_list_records(
            "ArtefactActivity", artefact_id=row, event_type="assigned"
        )
        audit = self.bloom.bloom_list_audit_events("workflow.assigned")
        self.assertEqual(
            (changed, bool(activity), bool(audit), self.bloom.bloom_outsider_sets_assignee(row, 3)),
            (values.STATUS_OK, True, True, values.STATUS_FORBIDDEN),
            msg=values.MSG_DWH_ASSIGNEE_RECORDED,
            abort_on_fail=False,
        )

    def bud_the_creator_comments_during_review_and_approval(self):
        values = self.parameters
        for phase in ("Review", "Approval"):
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                "Requirement",
                project_id=1,
                req_id="PRJ-REQ-907",
                title="Phase",
                status="Review",
                created_by_id=1,
            )
            self.bloom.bloom_add_record(
                "ArtefactWorkflow",
                project_id=1,
                artefact_type="requirement",
                artefact_id=row,
                revision_number=1,
                revision_creator_id=1,
                assignee_id=1,
                phase=phase,
            )
            posted = self.bloom.bloom_api_call(
                "POST", f"/api/artefacts/requirement/{row}/comments", json={"body": f"In {phase}"}
            ).status
            self.assertEqual(
                posted,
                values.STATUS_CREATED,
                msg=values.MSG_DWH_PHASE_COMMENT.format(phase=phase),
                abort_on_fail=False,
            )

    def bud_a_review_edited_without_a_workflow_gets_one(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-908",
            title="In review",
            status="Review",
            created_by_id=1,
        )
        self.bloom.bloom_change_record("Requirement", row, title="Changed during review")
        workflows = self.bloom.bloom_list_records(
            "ArtefactWorkflow", artefact_type="requirement", artefact_id=row
        )
        self.assertEqual(
            [(workflow.phase, workflow.assignee_id) for workflow in workflows],
            [("Draft", 1)],
            msg=values.MSG_DWH_REVIEW_EDITED,
            abort_on_fail=False,
        )

    def bud_threads_quote_a_passage_and_collect_replies(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-911",
            title="Discussed",
            status="Draft",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}/comments"
        first = self.bloom.bloom_api_call(
            "POST", path, json={"body": "Unclear", "anchor": values.DWH_ANCHOR}
        )
        thread = first.body["id"]
        self.bloom.bloom_act_as(2)
        reply = self.bloom.bloom_api_call(
            "POST", path, json={"body": "Agreed", "parent_id": thread}
        )
        nested = self.bloom.bloom_api_call(
            "POST", path, json={"body": "Fixed", "parent_id": reply.body["id"]}
        )
        general = self.bloom.bloom_api_call("POST", path, json={"body": "General note"}).status
        listed = self.bloom.bloom_api_call("GET", path).body
        self.assertEqual(
            (
                first.status,
                first.body["anchor"],
                reply.status,
                nested.body["parent_id"],
                general,
                [item["body"] for item in listed],
                [item["body"] for item in listed[0]["replies"]],
                listed[1]["anchor"],
            ),
            (
                values.STATUS_CREATED,
                values.DWH_ANCHOR,
                values.STATUS_CREATED,
                thread,
                values.STATUS_CREATED,
                ["Unclear", "General note"],
                ["Agreed", "Fixed"],
                None,
            ),
            msg=values.MSG_DWH_THREADS,
            abort_on_fail=False,
        )
        quoted_reply = self.bloom.bloom_api_call(
            "POST", path, json={"body": "x", "parent_id": thread, "anchor": values.DWH_ANCHOR}
        ).status
        other = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-912",
            title="Discussed",
            status="Draft",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        elsewhere = self.bloom.bloom_api_call(
            "POST",
            f"/api/artefacts/requirement/{other}/comments",
            json={"body": "x", "parent_id": thread},
        ).status
        suite = self.bloom.bloom_add_record(
            "TestSuite", project_id=1, suite_id="PRJ-TS-911", name="Suite", created_by_id=1
        )
        self.bloom.bloom_act_as(1)
        on_suite = self.bloom.bloom_api_call(
            "POST",
            f"/api/artefacts/test-suite/{suite}/comments",
            json={"body": "x", "anchor": values.DWH_ANCHOR},
        ).status
        self.assertEqual(
            (quoted_reply, elsewhere, on_suite),
            (values.STATUS_UNPROCESSABLE, values.STATUS_UNPROCESSABLE, values.STATUS_UNPROCESSABLE),
            msg=values.MSG_DWH_THREAD_REFUSED,
            abort_on_fail=False,
        )

    def bud_the_creator_reviewer_and_approver_resolve_and_reopen_a_thread(self):
        values = self.parameters
        for status in ("Draft", "Approved"):
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                "Requirement",
                project_id=1,
                req_id=f"PRJ-REQ-913-{status}",
                title="Discussed",
                status=status,
                created_by_id=1,
                reviewer_id=2,
                approver_id=3,
            )
            path = f"/api/artefacts/requirement/{row}/comments"
            self.bloom.bloom_act_as(2)
            thread = self.bloom.bloom_api_call("POST", path, json={"body": "Open point"}).body["id"]
            reply = self.bloom.bloom_api_call(
                "POST", path, json={"body": "Reply", "parent_id": thread}
            ).body["id"]
            rounds = []
            for person in (1, 2, 3):
                self.bloom.bloom_act_as(person)
                resolved = self.bloom.bloom_api_call("POST", f"{path}/{thread}/resolve")
                reopened = self.bloom.bloom_api_call("POST", f"{path}/{thread}/reopen")
                rounds.append(
                    (
                        resolved.status,
                        resolved.body["resolved_by"]["id"],
                        reopened.status,
                        reopened.body["resolved_at"],
                    )
                )
            self.bloom.bloom_act_as(4)
            outsider = self.bloom.bloom_api_call("POST", f"{path}/{thread}/resolve").status
            self.bloom.bloom_act_as(1)
            on_reply = self.bloom.bloom_api_call("POST", f"{path}/{reply}/resolve").status
            events = {
                event.event_type
                for event in self.bloom.bloom_list_records("ArtefactActivity", artefact_id=row)
            }
            self.assertEqual(
                (rounds, outsider, on_reply, {"comment_resolved", "comment_reopened"} <= events),
                (
                    [(values.STATUS_OK, person, values.STATUS_OK, None) for person in (1, 2, 3)],
                    values.STATUS_FORBIDDEN,
                    values.STATUS_UNPROCESSABLE,
                    True,
                ),
                msg=values.MSG_DWH_RESOLVE.format(status=status),
                abort_on_fail=False,
            )

    def bud_a_reply_notifies_earlier_writers_who_still_see_it(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-914",
            title="Discussed",
            status="Draft",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}/comments"
        self.bloom.bloom_add_record(
            "ArtefactWorkflow",
            project_id=1,
            artefact_type="requirement",
            artefact_id=row,
            revision_number=1,
            revision_creator_id=1,
            assignee_id=4,
            phase="Draft",
        )
        self.bloom.bloom_act_as(4)
        thread = self.bloom.bloom_api_call("POST", path, json={"body": "From the assignee"}).body[
            "id"
        ]
        self.bloom.bloom_act_as(2)
        with self.bloom.bloom_hidden_from({4}):
            self.bloom.bloom_api_call("POST", path, json={"body": "Reply", "parent_id": thread})
        notified = {
            notice.user_id
            for notice in self.bloom.bloom_list_records("Notification", event_type="comment")
            if (notice.body or "").endswith(": Reply")
        }
        self.assertEqual(notified, {1, 3}, msg=values.MSG_DWH_REPLY_NOTICE, abort_on_fail=False)

    def bud_a_reviewer_reply_counts_as_the_review(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-915",
            title="Discussed",
            status="Draft",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        base = f"/api/artefacts/requirement/{row}"
        requested = self.bloom.bloom_api_call(
            "POST", base + "/requests", json={"kind": "review"}
        ).status
        thread = self.bloom.bloom_api_call(
            "POST", base + "/comments", json={"body": "Please check"}
        ).body["id"]
        self.bloom.bloom_act_as(2)
        replied = self.bloom.bloom_api_call(
            "POST", base + "/comments", json={"body": "Checked", "parent_id": thread}
        ).status
        approval = self.bloom.bloom_api_call(
            "POST", base + "/requests", json={"kind": "approval"}
        ).status
        self.assertEqual(
            (requested, replied, approval),
            (values.STATUS_CREATED, values.STATUS_CREATED, values.STATUS_CREATED),
            msg=values.MSG_DWH_REVIEWER_REPLY,
            abort_on_fail=False,
        )

    def bud_a_reply_reaches_a_former_reviewer_who_wrote_in_the_thread(self):
        values = self.parameters
        for hidden in (set(), {2}):
            self.bloom.bloom_new_workflow_world()
            row = self.bloom.bloom_add_record(
                "Requirement",
                project_id=1,
                req_id=f"PRJ-REQ-916-{len(hidden)}",
                title="Discussed",
                status="Draft",
                created_by_id=1,
                reviewer_id=2,
                approver_id=3,
            )
            path = f"/api/artefacts/requirement/{row}/comments"
            self.bloom.bloom_act_as(2)
            thread = self.bloom.bloom_api_call("POST", path, json={"body": "Reviewer point"}).body[
                "id"
            ]
            self.bloom.bloom_act_as(1)
            moved = self.bloom.bloom_api_call(
                "PUT",
                f"/api/artefacts/requirement/{row}/workflow/assignees",
                json={"reviewer_id": 4},
            ).status
            with self.bloom.bloom_hidden_from(hidden):
                self.bloom.bloom_api_call(
                    "POST", path, json={"body": "Answer", "parent_id": thread}
                )
            notified = {
                notice.user_id
                for notice in self.bloom.bloom_list_records("Notification", event_type="comment")
                if (notice.body or "").endswith(": Answer")
            }
            self.assertEqual(
                (moved, notified),
                (values.STATUS_OK, {2, 3, 4} - hidden),
                msg=values.MSG_DWH_FORMER_REVIEWER,
                abort_on_fail=False,
            )

    def bud_a_separate_assignee_resolves_a_thread(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-917",
            title="Discussed",
            status="Draft",
            created_by_id=1,
            reviewer_id=2,
            approver_id=3,
        )
        path = f"/api/artefacts/requirement/{row}/comments"
        handed = self.bloom.bloom_api_call(
            "PUT", f"/api/artefacts/requirement/{row}/workflow/assignees", json={"assignee_id": 4}
        ).status
        thread = self.bloom.bloom_api_call("POST", path, json={"body": "Open point"}).body["id"]
        self.bloom.bloom_act_as(4)
        resolved = self.bloom.bloom_api_call("POST", f"{path}/{thread}/resolve")
        self.assertEqual(
            (handed, resolved.status, resolved.body["resolved_by"]["id"]),
            (values.STATUS_OK, values.STATUS_OK, 4),
            msg=values.MSG_DWH_ASSIGNEE_RESOLVES,
            abort_on_fail=False,
        )

    def bud_an_administrator_requests_review_and_declines_in_their_own_name(self):
        values = self.parameters
        self.bloom.bloom_new_workflow_world()
        row = self.bloom.bloom_add_record(
            "Requirement",
            project_id=1,
            req_id="PRJ-REQ-950",
            title="Handed over",
            status="Draft",
            created_by_id=2,
            reviewer_id=3,
            approver_id=4,
        )
        path = f"/api/artefacts/requirement/{row}"
        state = self.bloom.bloom_api_call("GET", path + "/workflow").body
        requested = self.bloom.bloom_api_call("POST", path + "/requests", json={"kind": "review"})
        request_id = requested.body["id"]
        requester = self.bloom.bloom_read_record("ArtefactRequest", request_id).requester_id
        recipients = [
            entry.user_id for entry in self.bloom.bloom_list_records("ArtefactRequestRecipient")
        ]
        offered = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"]["decline"]
        declined = self.bloom.bloom_api_call(
            "POST", f"/api/artefact-requests/{request_id}/decline"
        ).status
        self.assertEqual(
            (
                state["assignee"]["id"],
                state["actions"]["request_review"],
                requested.status,
                requester,
                recipients,
                offered,
                declined,
                self.bloom.bloom_read_record("Requirement", row).status,
                self.bloom.bloom_read_record("ArtefactRequest", request_id).decided_by_id,
                self.bloom.bloom_list_audit_events_like("workflow."),
            ),
            (
                2,
                True,
                values.STATUS_CREATED,
                1,
                [3],
                True,
                values.STATUS_OK,
                "Draft",
                1,
                [("workflow.requested", 1), ("workflow.declined", 1)],
            ),
            msg=values.MSG_DWH_ADMIN_REQUEST,
            abort_on_fail=False,
        )
        again = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "review"}
        ).status
        self.bloom.bloom_act_as(2)
        review = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "review"}
        ).status
        self.bloom.bloom_act_as(3)
        self.bloom.bloom_api_call("POST", path + "/comments", json={"body": "Reviewed"})
        approval = self.bloom.bloom_api_call(
            "POST", path + "/requests", json={"kind": "approval"}
        ).status
        self.bloom.bloom_act_as(1)
        actions = self.bloom.bloom_api_call("GET", path + "/workflow").body["actions"]
        by_admin = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", json={"step": "approve"}
        ).status
        self.bloom.bloom_act_as(4)
        approved = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", json={"step": "approve"}
        ).status
        stored = self.bloom.bloom_read_record("Requirement", row)
        self.assertEqual(
            (
                again,
                review,
                approval,
                actions["approve"],
                actions["decline"],
                by_admin,
                approved,
                stored.reviewed_by_id,
                stored.approved_by_id,
            ),
            (
                values.STATUS_OK,
                values.STATUS_CREATED,
                values.STATUS_CREATED,
                False,
                True,
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                3,
                4,
            ),
            msg=values.MSG_DWH_ADMIN_NO_APPROVE,
            abort_on_fail=False,
        )
