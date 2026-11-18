"""
* @file     ${tests/api/document_attachments.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests files held against a document and Bud reports published as RPT documents.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the document attachments.
"""

import base64
import hashlib

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocumentAttachmentsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_writer_without_delete_cannot_remove_a_file_403(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[0])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "attachment-writer")
        policy = self.bloom.bloom_api_new_policy(
            self.admin, "Attachment writer", {"RPT": ["view", "create", "edit"]}
        )
        self.bloom.bloom_api_admit(self.admin, project["id"], user.id, policy_ids=[policy["id"]])
        uploaded = self.bloom.bloom_api_upload_attachment(
            user.headers, document, "report.pdf", values.ATT_PDF, "application/pdf"
        )
        denied = self.bloom.bloom_api_call(
            "DELETE", f"/api/attachments/{uploaded.body['id']}", user.headers
        )
        self.assertEqual(
            (
                uploaded.status,
                denied.status,
                uploaded.body["id"]
                in [
                    item["id"]
                    for item in self.bloom.bloom_api_call(
                        "GET", f"/api/documents/{document}/attachments", user.headers
                    ).body
                ],
            ),
            (values.STATUS_CREATED, values.STATUS_FORBIDDEN, True),
            msg=values.MSG_ATT_NO_DELETE,
            abort_on_fail=False,
        )

    def bud_upload_starts_are_limited_per_maintainer_429(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[1])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "rate-limited")
        policy = self.bloom.bloom_api_new_policy(self.admin, "rate-limited policy", {"*": ["*"]})
        self.bloom.bloom_api_admit(self.admin, project["id"], user.id, policy_ids=[policy["id"]])
        self.bloom.bloom_set_attachment_limit(2)
        answers = [
            self.bloom.bloom_api_upload_attachment(
                user.headers, document, name, values.ATT_PDF, "application/pdf"
            )
            for name in ("first.pdf", "second.pdf", "third.pdf")
        ]
        self.bloom.bloom_set_attachment_limit(100)
        self.assertEqual(
            ([answer.status for answer in answers], answers[2].headers.get("retry-after")),
            ([values.STATUS_CREATED, values.STATUS_CREATED, values.STATUS_TOO_MANY], "900"),
            msg=values.MSG_ATT_RATE,
            abort_on_fail=False,
        )

    def bud_one_upload_at_a_time_per_maintainer_429(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[2])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "racing-uploader")
        policy = self.bloom.bloom_api_new_policy(self.admin, "racing-uploader policy", {"*": ["*"]})
        self.bloom.bloom_api_admit(self.admin, project["id"], user.id, policy_ids=[policy["id"]])
        first, second = self.bloom.bloom_api_race_two_uploads(
            user.headers, document, values.ATT_PDF
        )
        refused = first if first.status == values.STATUS_TOO_MANY else second
        self.print_variables({"statuses": (first.status, second.status)})
        self.assertEqual(
            (sorted([first.status, second.status]), refused.headers.get("retry-after")),
            (sorted([values.STATUS_CREATED, values.STATUS_TOO_MANY]), "60"),
            msg=values.MSG_ATT_ONE_ACTIVE,
            abort_on_fail=False,
        )

    def bud_a_file_is_stored_and_listed(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[3])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        created = self.bloom.bloom_api_upload_attachment(
            self.admin, document, "report.pdf", values.ATT_PDF, "application/pdf"
        )
        self.assertEqual(
            (
                created.status,
                created.body["original_filename"],
                created.body["size_bytes"],
                [
                    item["id"]
                    for item in self.bloom.bloom_api_call(
                        "GET", f"/api/documents/{document}/attachments", self.admin
                    ).body
                ],
            ),
            (values.STATUS_CREATED, "report.pdf", len(values.ATT_PDF), [created.body["id"]]),
            msg=values.MSG_ATT_STORED,
            abort_on_fail=False,
        )

    def bud_the_bytes_come_back(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[4])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        created = self.bloom.bloom_api_upload_attachment(
            self.admin, document, "report.pdf", values.ATT_PDF, "application/pdf"
        )
        got = self.bloom.bloom_api_download(
            self.admin, f"/api/attachments/{created.body['id']}/download"
        )
        self.assertEqual(
            (
                got.status,
                got.content,
                "attachment" in got.headers["content-disposition"],
                got.headers["x-content-type-options"],
            ),
            (values.STATUS_OK, values.ATT_PDF, True, "nosniff"),
            msg=values.MSG_ATT_BYTES,
            abort_on_fail=False,
        )

    def bud_the_stored_name_drops_a_supplied_path(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[5])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        created = self.bloom.bloom_api_upload_attachment(
            self.admin, document, "../../etc/passwd.pdf", values.ATT_PDF, "application/pdf"
        )
        self.assertEqual(
            (created.status, "/" in created.body["original_filename"]),
            (values.STATUS_CREATED, False),
            msg=values.MSG_ATT_NAME,
            abort_on_fail=False,
        )

    def bud_a_type_that_is_not_allowed_is_refused_415(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[6])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        self.assertEqual(
            self.bloom.bloom_api_upload_attachment(
                self.admin, document, "run.exe", b"MZ", "application/x-msdownload"
            ).status,
            values.STATUS_UNSUPPORTED_MEDIA,
            msg=values.MSG_ATT_TYPE,
            abort_on_fail=False,
        )

    def bud_the_digest_of_the_stored_file_is_recorded(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[7])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        self.assertEqual(
            self.bloom.bloom_api_upload_attachment(
                self.admin, document, "report.pdf", values.ATT_PDF, "application/pdf"
            ).body["sha256"],
            hashlib.sha256(values.ATT_PDF).hexdigest(),
            msg=values.MSG_ATT_DIGEST,
            abort_on_fail=False,
        )

    def bud_removing_a_file_removes_it(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[8])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        created = self.bloom.bloom_api_upload_attachment(
            self.admin, document, "report.pdf", values.ATT_PDF, "application/pdf"
        )
        removed = self.bloom.bloom_api_call(
            "DELETE", f"/api/attachments/{created.body['id']}", self.admin
        )
        self.assertEqual(
            (
                removed.status,
                [
                    item["id"]
                    for item in self.bloom.bloom_api_call(
                        "GET", f"/api/documents/{document}/attachments", self.admin
                    ).body
                ],
            ),
            (values.STATUS_NO_CONTENT, []),
            msg=values.MSG_ATT_REMOVED,
            abort_on_fail=False,
        )

    def bud_a_missing_document_is_a_404(self):
        values = self.parameters
        self.assertEqual(
            self.bloom.bloom_api_call(
                "GET", "/api/documents/999999/attachments", self.admin
            ).status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_ATT_MISSING,
            abort_on_fail=False,
        )

    def bud_reading_files_needs_a_signed_in_user_401(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[9])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        self.assertEqual(
            self.bloom.bloom_api_call("GET", f"/api/documents/{document}/attachments").status,
            values.STATUS_UNAUTHORIZED,
            msg=values.MSG_ATT_ANONYMOUS,
            abort_on_fail=False,
        )

    def bud_a_bud_report_creates_a_report_document(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[10])
        published = self.bloom.bloom_api_publish_bud_report(self.token, project["prefix"])
        self.print_variables({"published": published.body})
        names = sorted(
            item["original_filename"]
            for item in self.bloom.bloom_api_call(
                "GET", f"/api/documents/{published.body['document_id']}/attachments", self.admin
            ).body
        )
        self.assertEqual(
            (
                published.status,
                published.body["created"],
                published.body["doc_id"].startswith(f"{project['prefix']}-RPT-"),
                names,
            ),
            (values.STATUS_CREATED, True, True, ["bud-run-41.pdf", "report_junit.xml"]),
            msg=values.MSG_ATT_REPORT,
            abort_on_fail=False,
        )

    def bud_the_report_is_listed_as_an_rpt_document(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[11])
        self.bloom.bloom_api_publish_bud_report(self.token, project["prefix"])
        docs = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project['prefix']}/docs", self.admin, params={"type": "RPT"}
        ).body["items"]
        self.assertEqual(
            [item["doc_type"] for item in docs],
            ["RPT"],
            msg=values.MSG_ATT_REGISTRY,
            abort_on_fail=False,
        )

    def bud_the_report_description_records_the_outcome(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[12])
        published = self.bloom.bloom_api_publish_bud_report(self.token, project["prefix"]).body
        description = self.bloom.bloom_api_call(
            "GET", f"/api/documents/{published['document_id']}", self.admin
        ).body["description"]
        self.assertEqual(
            [
                "2 passed, 1 failed" in description,
                "PRJ-TC-001" in description,
                values.ATT_RUN_URL in description,
            ],
            [True] * 3,
            msg=values.MSG_ATT_SUMMARY,
            abort_on_fail=False,
        )

    def bud_the_same_run_again_updates_its_document(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[13])
        first = self.bloom.bloom_api_publish_bud_report(self.token, project["prefix"]).body
        second = self.bloom.bloom_api_publish_bud_report(
            self.token, project["prefix"], name="Nightly HIL rerun"
        ).body
        files = self.bloom.bloom_api_call(
            "GET", f"/api/documents/{first['document_id']}/attachments", self.admin
        ).body
        self.assertEqual(
            (second["created"], second["document_id"] == first["document_id"], len(files)),
            (False, True, 2),
            msg=values.MSG_ATT_SAME_RUN,
            abort_on_fail=False,
        )

    def bud_another_run_gets_its_own_document(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[14])
        first = self.bloom.bloom_api_publish_bud_report(
            self.token, project["prefix"], run_id=41
        ).body
        second = self.bloom.bloom_api_publish_bud_report(
            self.token, project["prefix"], run_id=42
        ).body
        self.assertEqual(
            (second["created"], second["document_id"] != first["document_id"]),
            (True, True),
            msg=values.MSG_ATT_OTHER_RUN,
            abort_on_fail=False,
        )

    def bud_content_that_is_not_base64_is_refused_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[15])
        files = [
            {
                "filename": "broken.pdf",
                "content_type": "application/pdf",
                "content_base64": "not base64 at all!!",
            }
        ]
        self.assertEqual(
            self.bloom.bloom_api_publish_bud_report(
                self.token, project["prefix"], files=files
            ).status,
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_ATT_NOT_BASE64,
            abort_on_fail=False,
        )

    def bud_a_report_file_type_that_is_not_allowed_is_refused_415(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[16])
        files = [
            {
                "filename": "payload.exe",
                "content_type": "application/x-msdownload",
                "content_base64": base64.b64encode(b"MZ").decode(),
            }
        ]
        self.assertEqual(
            self.bloom.bloom_api_publish_bud_report(
                self.token, project["prefix"], files=files
            ).status,
            values.STATUS_UNSUPPORTED_MEDIA,
            msg=values.MSG_ATT_REPORT_TYPE,
            abort_on_fail=False,
        )

    def bud_a_report_for_an_unknown_project_is_a_404(self):
        values = self.parameters
        self.assertEqual(
            self.bloom.bloom_api_publish_bud_report(self.token, "XYZ", run_id=1, files=[]).status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_ATT_NO_PROJECT,
            abort_on_fail=False,
        )

    def bud_a_user_token_cannot_publish_401(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[17])
        body = {"project_prefix": project["prefix"], "bud_run_id": 1, "run_name": "x", "files": []}
        self.assertEqual(
            self.bloom.bloom_api_call(
                "POST", "/api/bud/test-reports", self.admin, json=body
            ).status,
            values.STATUS_UNAUTHORIZED,
            msg=values.MSG_ATT_USER_TOKEN,
            abort_on_fail=False,
        )

    def bud_publishing_needs_a_credential_401(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[18])
        body = {"project_prefix": project["prefix"], "bud_run_id": 1, "run_name": "x", "files": []}
        self.assertEqual(
            self.bloom.bloom_api_call("POST", "/api/bud/test-reports", json=body).status,
            values.STATUS_UNAUTHORIZED,
            msg=values.MSG_ATT_NO_TOKEN,
            abort_on_fail=False,
        )

    def bud_an_external_user_reaches_no_file_of_a_hidden_document_404(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.ATT_PREFIXES[19])
        document = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "RPT", "Bus report"
        ).body["id"]
        created = self.bloom.bloom_api_upload_attachment(
            self.admin, document, "r.pdf", values.ATT_PDF, "application/pdf"
        )
        external = self.bloom.bloom_api_scenario_member(
            self.admin, "hidden-files", "Requirements Author", [project["id"]], "external"
        )
        attempts = (
            ("the file list", "GET", f"/api/documents/{document}/attachments"),
            ("the download", "GET", f"/api/attachments/{created.body['id']}/download"),
            ("removal", "DELETE", f"/api/attachments/{created.body['id']}"),
        )
        for what, method, path in attempts:
            answer = self.bloom.bloom_api_call(method, path, external.headers)
            self.assertEqual(
                (answer.status, (answer.body or {}).get("detail") != "Not Found"),
                (values.STATUS_NOT_FOUND, True),
                msg=values.MSG_ATT_HIDDEN.format(what=what),
                abort_on_fail=False,
                method=method,
                endpoint=path,
            )
        self.assertEqual(
            [
                item["id"]
                for item in self.bloom.bloom_api_call(
                    "GET", f"/api/documents/{document}/attachments", self.admin
                ).body
            ],
            [created.body["id"]],
            msg=values.MSG_ATT_KEPT,
            abort_on_fail=False,
        )
