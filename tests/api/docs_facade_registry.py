"""
* @file     ${tests/api/docs_facade_registry.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the filtering, sorting and paging of the document registry.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the document registry.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocsFacadeRegistryBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_registry_returns_every_document(self):
        values = self.parameters
        answer = self.bloom.bloom_api_registry(self.admin, self.registry.prefix)
        self.assertEqual(
            (answer.body["total"], sorted([item["doc_id"] for item in answer.body["items"]])),
            (4, sorted(self.registry.names.values())),
            msg=values.MSG_REG_ALL,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs",
        )

    def bud_a_row_carries_the_registry_columns(self):
        values = self.parameters
        alpha = next(
            item
            for item in self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body[
                "items"
            ]
            if item["doc_id"] == self.registry.names["alpha"]
        )
        self.print_variables({"alpha": alpha})
        self.assertEqual(
            (
                alpha["title"],
                alpha["doc_type"],
                alpha["status"],
                alpha["priority"],
                alpha["req_type"],
                alpha["req_origin"],
                alpha["reviewer_id"],
                alpha["visibility"],
                bool(alpha["created_at"] and alpha["updated_at"]),
            ),
            (
                "Alpha boot timing",
                "REQ",
                "Approved",
                "High",
                "Functional",
                "Customer",
                self.registry.reviewer["id"],
                "customer",
                True,
            ),
            msg=values.MSG_REG_COLUMNS,
            abort_on_fail=False,
        )

    def bud_no_row_carries_the_document_body(self):
        values = self.parameters
        items = self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body["items"]
        self.assertEqual(
            [
                key
                for item in items
                for key in ("content_json", "content_html", "description")
                if key in item
            ],
            [],
            msg=values.MSG_REG_NO_BODY,
            abort_on_fail=False,
        )

    def bud_links_are_counted_both_ways_and_suspect_on_both_ends(self):
        values = self.parameters
        by_id = {
            item["doc_id"]: item
            for item in self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body[
                "items"
            ]
        }
        name = self.registry.names
        self.assertEqual(
            (
                by_id[name["charlie"]]["outgoing_links"],
                by_id[name["charlie"]]["incoming_links"],
                by_id[name["alpha"]]["incoming_links"],
                by_id[name["bravo"]]["incoming_links"],
                by_id[name["bravo"]]["outgoing_links"],
            ),
            (2, 0, 1, 0, 0),
            msg=values.MSG_REG_LINK_COUNTS,
            abort_on_fail=False,
        )
        self.assertEqual(
            [by_id[name[key]]["suspect_links"] for key in ("alpha", "charlie", "delta")],
            [1, 1, 0],
            msg=values.MSG_REG_SUSPECT,
            abort_on_fail=False,
        )

    def bud_link_counts_can_be_left_out(self):
        values = self.parameters
        items = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, include_link_counts=False
        ).body["items"]
        self.assertEqual(
            {(item["incoming_links"], item["outgoing_links"]) for item in items},
            {(0, 0)},
            msg=values.MSG_REG_SKIP_COUNTS,
            abort_on_fail=False,
        )

    def bud_the_filters_narrow_the_rows(self):
        values = self.parameters
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, type="TC"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["charlie"], self.registry.names["delta"]]),
            msg=values.MSG_REG_FILTER.format(what="type", expected="charlie, delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, status="Draft"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["bravo"], self.registry.names["delta"]]),
            msg=values.MSG_REG_FILTER.format(what="status", expected="bravo, delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            len(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, status=["Draft", "Review"]
                    ).body["items"]
                ]
            ),
            3,
            msg=values.MSG_REG_FILTER.format(what="two statuses", expected="three rows"),
            abort_on_fail=False,
        )
        self.assertEqual(
            [
                item["doc_id"]
                for item in self.bloom.bloom_api_registry(
                    self.admin, self.registry.prefix, priority="Low"
                ).body["items"]
            ],
            [self.registry.names["bravo"]],
            msg=values.MSG_REG_FILTER.format(what="priority", expected="bravo"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, reviewer="assigned"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["alpha"], self.registry.names["delta"]]),
            msg=values.MSG_REG_FILTER.format(what="assigned reviewer", expected="alpha, delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, reviewer="unassigned"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["bravo"], self.registry.names["charlie"]]),
            msg=values.MSG_REG_FILTER.format(what="unassigned reviewer", expected="bravo, charlie"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, reviewer=str(self.registry.reviewer["id"])
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["alpha"], self.registry.names["delta"]]),
            msg=values.MSG_REG_FILTER.format(what="reviewer id", expected="alpha, delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            [
                item["doc_id"]
                for item in self.bloom.bloom_api_registry(
                    self.admin, self.registry.prefix, links="unlinked", include_link_counts=False
                ).body["items"]
            ],
            [self.registry.names["bravo"]],
            msg=values.MSG_REG_FILTER.format(what="unlinked rows without counts", expected="bravo"),
            abort_on_fail=False,
        )
        self.assertEqual(
            [
                item["doc_id"]
                for item in self.bloom.bloom_api_registry(
                    self.admin, self.registry.prefix, status="Draft", type="TC"
                ).body["items"]
            ],
            [self.registry.names["delta"]],
            msg=values.MSG_REG_FILTER.format(what="status and type together", expected="delta"),
            abort_on_fail=False,
        )

    def bud_a_reviewer_that_is_not_a_user_id_is_refused_422(self):
        values = self.parameters
        self.assertEqual(
            self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, reviewer="somebody"
            ).status,
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_REG_BAD_REVIEWER,
            abort_on_fail=False,
        )

    def bud_the_six_link_states_are_told_apart(self):
        values = self.parameters
        for state, expected in values.REG_LINK_STATES:
            found = [
                item["doc_id"]
                for item in self.bloom.bloom_api_registry(
                    self.admin, self.registry.prefix, links=state
                ).body["items"]
            ]
            self.assertEqual(
                sorted(found),
                sorted(self.registry.names[name] for name in expected),
                msg=values.MSG_REG_FILTER.format(
                    what=f"{state} links", expected=", ".join(expected)
                ),
                abort_on_fail=False,
            )

    def bud_a_date_range_is_inclusive(self):
        values = self.parameters
        today = self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body["items"][0][
            "created_at"
        ][:10]
        self.assertEqual(
            (
                len(
                    [
                        item["doc_id"]
                        for item in self.bloom.bloom_api_registry(
                            self.admin, self.registry.prefix, created_from=today, created_to=today
                        ).body["items"]
                    ]
                ),
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, created_from="2099-01-01"
                    ).body["items"]
                ],
            ),
            (4, []),
            msg=values.MSG_REG_DATES,
            abort_on_fail=False,
        )

    def bud_searching_matches_titles_ids_kinds_reviewers_and_dates(self):
        values = self.parameters
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, q="brownout"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["delta"]]),
            msg=values.MSG_REG_SEARCH.format(term="brownout", expected="delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, q="-REQ-"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["alpha"], self.registry.names["bravo"]]),
            msg=values.MSG_REG_SEARCH.format(term="-REQ-", expected="alpha, bravo"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, q="test case"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["charlie"], self.registry.names["delta"]]),
            msg=values.MSG_REG_SEARCH.format(term="test case", expected="charlie, delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, q="grace hopper"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["alpha"], self.registry.names["delta"]]),
            msg=values.MSG_REG_SEARCH.format(term="grace hopper", expected="alpha, delta"),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, q="BROWNOUT"
                    ).body["items"]
                ]
            ),
            sorted([self.registry.names["delta"]]),
            msg=values.MSG_REG_SEARCH.format(term="BROWNOUT", expected="delta"),
            abort_on_fail=False,
        )
        month = self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body["items"][0][
            "created_at"
        ][:7]
        self.assertEqual(
            len(
                [
                    item["doc_id"]
                    for item in self.bloom.bloom_api_registry(
                        self.admin, self.registry.prefix, q=month
                    ).body["items"]
                ]
            ),
            4,
            msg=values.MSG_REG_SEARCH.format(term=month, expected="all four"),
            abort_on_fail=False,
        )
        nothing = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, q="zzz-no-such-thing"
        )
        self.assertEqual(
            ([item["doc_id"] for item in nothing.body["items"]], nothing.body["total"]),
            ([], 0),
            msg=values.MSG_REG_NOTHING,
            abort_on_fail=False,
        )

    def bud_rows_are_ordered_as_asked(self):
        values = self.parameters
        stamps = [
            item["updated_at"]
            for item in self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body[
                "items"
            ]
        ]
        self.assertEqual(
            stamps,
            sorted(stamps, reverse=True),
            msg=values.MSG_REG_DEFAULT_ORDER,
            abort_on_fail=False,
        )
        up, down = [
            item["doc_id"]
            for item in self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, sort="doc_id", dir="asc"
            ).body["items"]
        ], [
            item["doc_id"]
            for item in self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, sort="doc_id", dir="desc"
            ).body["items"]
        ]
        self.assertEqual(
            (up, down),
            (sorted(up), list(reversed(up))),
            msg=values.MSG_REG_ID_ORDER,
            abort_on_fail=False,
        )
        self.assertEqual(
            [
                item["doc_id"]
                for item in self.bloom.bloom_api_registry(
                    self.admin, self.registry.prefix, sort="title", dir="asc"
                ).body["items"]
            ],
            [
                self.registry.names["alpha"],
                self.registry.names["bravo"],
                self.registry.names["charlie"],
                self.registry.names["delta"],
            ],
            msg=values.MSG_REG_TITLE_ORDER,
            abort_on_fail=False,
        )
        by_reviewer = [
            item["doc_id"]
            for item in self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, sort="reviewer", dir="asc"
            ).body["items"]
        ]
        self.assertEqual(
            sorted(by_reviewer[:2]),
            sorted([self.registry.names["bravo"], self.registry.names["charlie"]]),
            msg=values.MSG_REG_REVIEWER_ORDER,
            abort_on_fail=False,
        )
        by_origin = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, sort="req_origin", dir="asc"
        )
        found = [item["doc_id"] for item in by_origin.body["items"]]
        self.assertEqual(
            (by_origin.status, sorted(found[:2]), found[2:]),
            (
                values.STATUS_OK,
                sorted([self.registry.names["charlie"], self.registry.names["delta"]]),
                [self.registry.names["alpha"], self.registry.names["bravo"]],
            ),
            msg=values.MSG_REG_ORIGIN_ORDER,
            abort_on_fail=False,
        )
        refused = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, sort="content_html"
        )
        self.assertEqual(
            (refused.status, "content_html" in refused.body["detail"]),
            (values.STATUS_UNPROCESSABLE, True),
            msg=values.MSG_REG_BAD_SORT,
            abort_on_fail=False,
        )

    def bud_paging_keeps_the_whole_count(self):
        values = self.parameters
        page = self.bloom.bloom_api_registry(self.admin, self.registry.prefix, limit=2).body
        self.assertEqual(
            (len(page["items"]), page["total"], page["limit"]),
            (2, 4, 2),
            msg=values.MSG_REG_PAGE,
            abort_on_fail=False,
        )
        seen = [
            item["doc_id"]
            for item in self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, limit=2, skip=0
            ).body["items"]
        ] + [
            item["doc_id"]
            for item in self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, limit=2, skip=2
            ).body["items"]
        ]
        self.assertEqual(len(set(seen)), 4, msg=values.MSG_REG_PAGES, abort_on_fail=False)
        filtered = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, type="TC", limit=1
        ).body
        self.assertEqual(
            (filtered["total"], len(filtered["items"])),
            (2, 1),
            msg=values.MSG_REG_FILTERED_PAGE,
            abort_on_fail=False,
        )
        past = self.bloom.bloom_api_registry(self.admin, self.registry.prefix, limit=2, skip=99)
        self.assertEqual(
            (past.status, [item["doc_id"] for item in past.body["items"]], past.body["total"]),
            (values.STATUS_OK, [], 4),
            msg=values.MSG_REG_PAST_END,
            abort_on_fail=False,
        )

    def bud_the_type_summary_counts_each_type(self):
        values = self.parameters
        summary = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{self.registry.prefix}/doc-type-summary", self.admin
        )
        counts = {entry["doc_type"]: entry["count"] for entry in summary.body["types"]}
        self.assertEqual(
            (summary.status, counts, summary.body["total"]),
            (values.STATUS_OK, {"REQ": 2, "TC": 2}, 4),
            msg=values.MSG_REG_SUMMARY,
            abort_on_fail=False,
        )
        listed = self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body["items"]
        expected = {}
        for item in listed:
            count, suspect = expected.get(item["doc_type"], (0, 0))
            expected[item["doc_type"]] = (count + 1, suspect + item["suspect_links"])
        self.assertEqual(
            {
                entry["doc_type"]: (entry["count"], entry["suspect_links"])
                for entry in summary.body["types"]
            },
            expected,
            msg=values.MSG_REG_SUMMARY_AGREES,
            abort_on_fail=False,
        )

    def bud_the_summary_reports_membership_edges(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.REG_PREFIXES[0])
        cases = [
            self.bloom.bloom_api_add_test_case(self.admin, project["id"], f"TC {number}").body
            for number in range(2)
        ]
        suite = self.bloom.bloom_api_add_suite(self.admin, project["id"], "S", cases)
        self.bloom.bloom_api_call(
            "POST",
            "/api/campaigns",
            self.admin,
            json={"project_id": project["id"], "name": "C", "suite_ids": [suite["id"]]},
        )
        edges = {
            (e["source_type"], e["target_type"]): (e["count"], e["role"])
            for e in self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project['prefix']}/doc-type-summary", self.admin
            ).body["membership_edges"]
        }
        self.assertEqual(
            (edges[("TS", "TC")], edges[("CMP", "TS")]),
            ((2, "contains"), (1, "relates_to")),
            msg=values.MSG_REG_EDGES,
            abort_on_fail=False,
        )

    def bud_the_summary_stays_in_its_project(self):
        values = self.parameters
        other = self.bloom.bloom_api_new_project(self.admin, values.REG_PREFIXES[1])
        answer = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{other['prefix']}/doc-type-summary", self.admin
        )
        self.assertEqual(
            (answer.status, answer.body),
            (values.STATUS_OK, {"types": [], "total": 0, "membership_edges": []}),
            msg=values.MSG_REG_OTHER_PROJECT,
            abort_on_fail=False,
        )
        anonymous = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{self.registry.prefix}/doc-type-summary"
        )
        self.assertEqual(
            anonymous.status,
            values.STATUS_UNAUTHORIZED,
            msg=values.MSG_REG_SUMMARY_ANONYMOUS,
            abort_on_fail=False,
        )

    def bud_named_rows_are_returned_by_type_and_id(self):
        values = self.parameters
        rows = {
            name: next(
                item
                for item in self.bloom.bloom_api_registry(self.admin, self.registry.prefix).body[
                    "items"
                ]
                if item["doc_id"] == doc_id
            )
            for name, doc_id in self.registry.names.items()
        }
        named = self.bloom.bloom_api_registry(
            self.admin,
            self.registry.prefix,
            keys=[
                f"{rows[name]['doc_type']}:{rows[name]['id']}"
                for name in (
                    "alpha",
                    "charlie",
                )
            ],
        ).body
        self.assertEqual(
            (sorted(item["doc_id"] for item in named["items"]), named["total"]),
            (sorted([self.registry.names["alpha"], self.registry.names["charlie"]]), 2),
            msg=values.MSG_REG_KEYS,
            abort_on_fail=False,
        )
        across = self.bloom.bloom_api_registry(
            self.admin,
            self.registry.prefix,
            keys=[
                f"{rows[name]['doc_type']}:{rows[name]['id']}"
                for name in (
                    "bravo",
                    "delta",
                )
            ],
        ).body["items"]
        self.assertEqual(
            {item["doc_type"] for item in across},
            {"REQ", "TC"},
            msg=values.MSG_REG_KEYS_TYPES,
            abort_on_fail=False,
        )
        wrong_type = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, keys=[f"REQ:{rows['charlie']['id']}"]
        ).body["items"]
        self.assertNotIn(
            self.registry.names["charlie"],
            [item["doc_id"] for item in wrong_type],
            msg=values.MSG_REG_KEYS_WRONG_TYPE,
            abort_on_fail=False,
        )
        unknown = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, keys=["REQ:99999"]
        ).body
        self.assertEqual(
            (unknown["items"], unknown["total"]),
            ([], 0),
            msg=values.MSG_REG_KEYS_UNKNOWN,
            abort_on_fail=False,
        )
        related = self.bloom.bloom_api_registry(
            self.admin,
            self.registry.prefix,
            keys=[
                f"{rows[name]['doc_type']}:{rows[name]['id']}"
                for name in (
                    "alpha",
                    "bravo",
                )
            ],
            related_to=self.registry.names["charlie"],
        ).body["items"]
        self.assertEqual(
            [item["doc_id"] for item in related],
            [self.registry.names["alpha"]],
            msg=values.MSG_REG_KEYS_RELATED,
            abort_on_fail=False,
        )

    def bud_wrong_named_rows_are_refused_422(self):
        values = self.parameters
        cases = (
            ("a malformed key", ["REQ:not-a-number"]),
            ("an unknown type", ["NOPE:1"]),
            ("a batch of more than 500 keys", [f"REQ:{number}" for number in range(501)]),
        )
        for what, keys in cases:
            self.assertEqual(
                self.bloom.bloom_api_registry(self.admin, self.registry.prefix, keys=keys).status,
                values.STATUS_UNPROCESSABLE,
                msg=values.MSG_REG_KEYS_REFUSED.format(what=what),
                abort_on_fail=False,
            )

    def bud_a_named_row_of_another_project_is_not_returned(self):
        values = self.parameters
        other = self.bloom.bloom_api_new_project(self.admin, values.REG_PREFIXES[2])
        outsider = self.bloom.bloom_api_create_requirement(
            self.admin, other["id"], "Not yours"
        ).json()
        self.assertEqual(
            self.bloom.bloom_api_registry(
                self.admin, self.registry.prefix, keys=[f"REQ:{outsider['id']}"]
            ).body["items"],
            [],
            msg=values.MSG_REG_KEYS_PROJECT,
            abort_on_fail=False,
        )

    def bud_a_specification_is_returned_by_naming_it(self):
        values = self.parameters
        spec = self.bloom.bloom_api_add_typed_document(
            self.admin, self.registry.project["id"], "SPEC", "Bus specification"
        ).body
        items = self.bloom.bloom_api_registry(
            self.admin, self.registry.prefix, keys=[f"SPEC:{spec['id']}"]
        ).body["items"]
        self.assertEqual(
            [item["doc_id"] for item in items],
            [spec["doc_id"]],
            msg=values.MSG_REG_KEYS_SPEC,
            abort_on_fail=False,
        )
