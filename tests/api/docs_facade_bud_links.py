"""
* @file     ${tests/api/docs_facade_bud_links.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that the document list carries the last Bud run of a test case.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the Bud run link in the document list.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocsFacadeBudLinksBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_document_list_shows_the_last_bud_run(self):
        path = f"/api/projects/{self.parameters.BUDL_PREFIX}/docs"
        answer = self.bloom.bloom_api_call("GET", path, self.member, params={"type": "TC"})
        self.print_variables({"answer": answer.body})
        items = answer.body.get("items", [])
        self.assertEqual(
            (answer.status, [(item["doc_id"], item["last_bud_run_id"]) for item in items]),
            (
                self.parameters.STATUS_OK,
                [
                    (
                        f"{self.parameters.BUDL_PREFIX}-TC-001",
                        self.parameters.BUDL_CASE["last_bud_run_id"],
                    )
                ],
            ),
            msg=self.parameters.MSG_BUDL_RUN,
            abort_on_fail=False,
            method="GET",
            endpoint=path,
        )
