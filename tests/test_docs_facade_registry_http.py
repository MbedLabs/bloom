"""The registry endpoint's filtering, sorting and paging, in SQL.

The screen used to fetch a project's documents whole and narrow them in the
browser. It now sends every filter, the sort and the page to the server, so the
questions that used to be answered in JavaScript are answered here - and these
drive the real route against real Postgres so the answers come from the query
plan and not from a fixture.

The browser-side counterpart (ui/src/test/registry-filtering.test.tsx) checks
only that the screen *asks* correctly. This checks the answering.
"""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_email


@pytest.fixture
def auth_headers(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def reviewer(api_client: TestClient, auth_headers):
    """A second user, so `reviewer=<id>` has someone to point at."""
    response = api_client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "email": unique_email("registry-reviewer"),
            "full_name": "Grace Hopper",
            "password": "Registry-Reviewer-1!",
            "role": "maintainer",
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture
def registry(api_client: TestClient, auth_headers, reviewer):
    """A project whose documents disagree on every axis the registry filters by.

    Four artefacts across two types, chosen so that a filter matching everything
    and a filter matching nothing are told apart by which identifiers come back.
    """
    project = create_project(api_client, auth_headers, "Registry")
    pid = project["id"]

    def post(path: str, body: dict) -> dict:
        response = api_client.post(path, headers=auth_headers, json={"project_id": pid, **body})
        assert response.status_code in (200, 201), response.text
        return response.json()

    alpha = post(
        "/api/requirements",
        {
            "title": "Alpha boot timing",
            "status": "Approved",
            "priority": "High",
            "req_type": "Functional",
            "req_origin": "Customer",
            "reviewer_id": reviewer["id"],
        },
    )
    bravo = post(
        "/api/requirements",
        {"title": "Bravo shutdown sequence", "status": "Draft", "priority": "Low"},
    )
    charlie = post("/api/test-cases", {"title": "Charlie cold start", "status": "Review"})
    delta = post(
        "/api/test-cases",
        {"title": "Delta brownout", "status": "Draft", "reviewer_id": reviewer["id"]},
    )

    # Charlie is linked both ways with nothing suspect; Alpha carries the only
    # suspect link. Bravo is linked to nothing at all.
    def link(source, source_type, target, target_type, role, suspect):
        response = api_client.post(
            "/api/links",
            headers=auth_headers,
            json={
                "project_id": pid,
                "source_type": source_type,
                "source_id": source["id"],
                "target_type": target_type,
                "target_id": target["id"],
                "role": role,
                "suspect": suspect,
            },
        )
        assert response.status_code in (200, 201), response.text

    # Bloom validates the role against the pair of types, so these are the roles
    # those pairs actually allow.
    link(charlie, "TC", alpha, "REQ", "verifies", suspect=True)
    link(charlie, "TC", delta, "TC", "relates_to", suspect=False)

    return {
        "project": project,
        "prefix": project["prefix"],
        "reviewer": reviewer,
        "alpha": alpha["req_id"],
        "bravo": bravo["req_id"],
        "charlie": charlie["tc_id"],
        "delta": delta["tc_id"],
    }


def ids(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["doc_id"] for item in response.json()["items"]]


def fetch(api_client, headers, prefix, **params):
    return api_client.get(f"/api/projects/{prefix}/docs", headers=headers, params=params)


class TestTheShellItReturns:
    def test_returns_every_document_of_the_project(self, api_client, auth_headers, registry):
        body = fetch(api_client, auth_headers, registry["prefix"]).json()

        assert body["total"] == 4
        assert sorted(item["doc_id"] for item in body["items"]) == sorted(
            [registry["alpha"], registry["bravo"], registry["charlie"], registry["delta"]]
        )

    def test_carries_the_columns_the_registry_renders(self, api_client, auth_headers, registry):
        items = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]
        alpha = next(item for item in items if item["doc_id"] == registry["alpha"])

        # The listing is projected down to the shell columns; every one of these
        # is a column the table draws, so dropping one from the projection has
        # to fail here rather than render a blank cell.
        assert alpha["title"] == "Alpha boot timing"
        assert alpha["doc_type"] == "REQ"
        assert alpha["status"] == "Approved"
        assert alpha["priority"] == "High"
        assert alpha["req_type"] == "Functional"
        assert alpha["req_origin"] == "Customer"
        assert alpha["reviewer_id"] == registry["reviewer"]["id"]
        # A customer-origin requirement is stored customer-visible, and that
        # stored value is what decides whether an external user sees the row -
        # so the listing has to report it rather than assume a default.
        assert alpha["visibility"] == "customer"
        assert alpha["created_at"] and alpha["updated_at"]

    def test_never_returns_the_document_body(self, api_client, auth_headers, registry):
        items = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]

        # These used to be read for every row and thrown away. The listing has
        # no use for them and must not start carrying them again.
        for item in items:
            assert "content_json" not in item
            assert "content_html" not in item
            assert "description" not in item

    def test_counts_the_links_in_both_directions(self, api_client, auth_headers, registry):
        items = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]
        by_id = {item["doc_id"]: item for item in items}

        # Charlie is the source of both links, Alpha and Delta a target each.
        assert by_id[registry["charlie"]]["outgoing_links"] == 2
        assert by_id[registry["charlie"]]["incoming_links"] == 0
        assert by_id[registry["alpha"]]["incoming_links"] == 1
        assert by_id[registry["bravo"]]["incoming_links"] == 0
        assert by_id[registry["bravo"]]["outgoing_links"] == 0

    def test_tallies_suspect_links_against_both_ends(self, api_client, auth_headers, registry):
        items = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]
        by_id = {item["doc_id"]: item for item in items}

        # One suspect link, so the document it points at and the one it leaves
        # both report it - that is what puts a document on the suspect filter.
        assert by_id[registry["alpha"]]["suspect_links"] == 1
        assert by_id[registry["charlie"]]["suspect_links"] == 1
        assert by_id[registry["delta"]]["suspect_links"] == 0

    def test_can_be_asked_to_skip_the_link_counts(self, api_client, auth_headers, registry):
        items = fetch(
            api_client, auth_headers, registry["prefix"], include_link_counts=False
        ).json()["items"]

        assert all(item["incoming_links"] == 0 for item in items)
        assert all(item["outgoing_links"] == 0 for item in items)


class TestNarrowing:
    def test_keeps_one_type(self, api_client, auth_headers, registry):
        assert sorted(
            ids(fetch(api_client, auth_headers, registry["prefix"], type="TC"))
        ) == sorted([registry["charlie"], registry["delta"]])

    def test_accepts_several_statuses_at_once(self, api_client, auth_headers, registry):
        one = ids(fetch(api_client, auth_headers, registry["prefix"], status="Draft"))
        assert sorted(one) == sorted([registry["bravo"], registry["delta"]])

        # Statuses accumulate rather than replace each other.
        both = ids(fetch(api_client, auth_headers, registry["prefix"], status=["Draft", "Review"]))
        assert len(both) == 3

    def test_narrows_to_one_priority(self, api_client, auth_headers, registry):
        assert ids(fetch(api_client, auth_headers, registry["prefix"], priority="Low")) == [
            registry["bravo"]
        ]

    def test_separates_assigned_from_unassigned(self, api_client, auth_headers, registry):
        assigned = ids(fetch(api_client, auth_headers, registry["prefix"], reviewer="assigned"))
        assert sorted(assigned) == sorted([registry["alpha"], registry["delta"]])

        unassigned = ids(fetch(api_client, auth_headers, registry["prefix"], reviewer="unassigned"))
        assert sorted(unassigned) == sorted([registry["bravo"], registry["charlie"]])

    def test_picks_out_one_reviewer_by_id(self, api_client, auth_headers, registry):
        picked = ids(
            fetch(
                api_client,
                auth_headers,
                registry["prefix"],
                reviewer=str(registry["reviewer"]["id"]),
            )
        )
        assert sorted(picked) == sorted([registry["alpha"], registry["delta"]])

    def test_refuses_a_reviewer_that_is_not_a_user_id(self, api_client, auth_headers, registry):
        response = fetch(api_client, auth_headers, registry["prefix"], reviewer="somebody")
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "state,expected",
        [
            ("linked", ["alpha", "charlie", "delta"]),
            ("unlinked", ["bravo"]),
            ("incoming", ["alpha", "delta"]),
            ("outgoing", ["charlie"]),
            ("suspect", ["alpha", "charlie"]),
            ("clean", ["bravo", "delta"]),
        ],
    )
    def test_tells_the_six_link_states_apart(
        self, api_client, auth_headers, registry, state, expected
    ):
        found = ids(fetch(api_client, auth_headers, registry["prefix"], links=state))
        assert sorted(found) == sorted(registry[name] for name in expected)

    def test_applies_a_link_filter_even_without_the_counts(
        self, api_client, auth_headers, registry
    ):
        # The counts are what the filter is a question about, so asking not to
        # be told them cannot quietly drop the filter.
        found = ids(
            fetch(
                api_client,
                auth_headers,
                registry["prefix"],
                links="unlinked",
                include_link_counts=False,
            )
        )
        assert found == [registry["bravo"]]

    def test_applies_every_filter_rather_than_the_last(self, api_client, auth_headers, registry):
        # Draft alone keeps two, TC alone keeps two, together only Delta.
        found = ids(fetch(api_client, auth_headers, registry["prefix"], status="Draft", type="TC"))
        assert found == [registry["delta"]]

    def test_bounds_a_date_range_inclusively_at_both_ends(self, api_client, auth_headers, registry):
        items = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]
        today = items[0]["created_at"][:10]

        # Everything was created in this test, so a range that is exactly today
        # has to keep all four - an exclusive bound would silently drop them.
        same_day = fetch(
            api_client, auth_headers, registry["prefix"], created_from=today, created_to=today
        )
        assert len(ids(same_day)) == 4

        after = fetch(api_client, auth_headers, registry["prefix"], created_from="2099-01-01")
        assert ids(after) == []


class TestSearching:
    def test_matches_a_title(self, api_client, auth_headers, registry):
        assert ids(fetch(api_client, auth_headers, registry["prefix"], q="brownout")) == [
            registry["delta"]
        ]

    def test_matches_part_of_an_identifier(self, api_client, auth_headers, registry):
        found = ids(fetch(api_client, auth_headers, registry["prefix"], q="-REQ-"))
        assert sorted(found) == sorted([registry["alpha"], registry["bravo"]])

    def test_matches_the_human_label_of_the_kind(self, api_client, auth_headers, registry):
        # "Test Case" is what the table shows; "TC" is what it stores.
        found = ids(fetch(api_client, auth_headers, registry["prefix"], q="test case"))
        assert sorted(found) == sorted([registry["charlie"], registry["delta"]])

    def test_matches_the_reviewers_name_which_is_not_in_the_row(
        self, api_client, auth_headers, registry
    ):
        found = ids(fetch(api_client, auth_headers, registry["prefix"], q="grace hopper"))
        assert sorted(found) == sorted([registry["alpha"], registry["delta"]])

    def test_ignores_case(self, api_client, auth_headers, registry):
        assert ids(fetch(api_client, auth_headers, registry["prefix"], q="BROWNOUT")) == [
            registry["delta"]
        ]

    def test_matches_a_date_by_its_iso_prefix(self, api_client, auth_headers, registry):
        month = fetch(api_client, auth_headers, registry["prefix"]).json()["items"][0][
            "created_at"
        ][:7]

        assert len(ids(fetch(api_client, auth_headers, registry["prefix"], q=month))) == 4

    def test_a_term_matching_nothing_returns_nothing(self, api_client, auth_headers, registry):
        response = fetch(api_client, auth_headers, registry["prefix"], q="zzz-no-such-thing")
        assert ids(response) == []
        assert response.json()["total"] == 0


class TestOrdering:
    def test_defaults_to_most_recently_updated_first(self, api_client, auth_headers, registry):
        items = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]
        stamps = [item["updated_at"] for item in items]

        assert stamps == sorted(stamps, reverse=True)

    def test_sorts_by_identifier_in_both_directions(self, api_client, auth_headers, registry):
        up = ids(fetch(api_client, auth_headers, registry["prefix"], sort="doc_id", dir="asc"))
        down = ids(fetch(api_client, auth_headers, registry["prefix"], sort="doc_id", dir="desc"))

        assert up == sorted(up)
        assert down == list(reversed(up))

    def test_sorts_by_title_case_insensitively(self, api_client, auth_headers, registry):
        found = ids(fetch(api_client, auth_headers, registry["prefix"], sort="title", dir="asc"))

        assert found == [
            registry["alpha"],
            registry["bravo"],
            registry["charlie"],
            registry["delta"],
        ]

    def test_sorts_by_reviewer_name_not_by_reviewer_id(self, api_client, auth_headers, registry):
        found = ids(fetch(api_client, auth_headers, registry["prefix"], sort="reviewer", dir="asc"))

        # The two without a reviewer sort as the empty string, so they lead.
        assert sorted(found[:2]) == sorted([registry["bravo"], registry["charlie"]])

    def test_sorts_by_a_column_only_one_type_has(self, api_client, auth_headers, registry):
        # req_origin exists on requirements alone; the test cases contribute a
        # typed NULL, which has to sort as the empty string rather than fail or
        # scatter. Ascending: the two NULLs, then Customer, then the Internal
        # a requirement defaults to.
        response = fetch(api_client, auth_headers, registry["prefix"], sort="req_origin", dir="asc")
        assert response.status_code == 200
        found = ids(response)
        assert sorted(found[:2]) == sorted([registry["charlie"], registry["delta"]])
        assert found[2:] == [registry["alpha"], registry["bravo"]]

    def test_refuses_a_column_it_cannot_sort_by(self, api_client, auth_headers, registry):
        response = fetch(api_client, auth_headers, registry["prefix"], sort="content_html")

        # Falling back silently would show an arbitrary order under a heading
        # that claims otherwise.
        assert response.status_code == 422
        assert "content_html" in response.json()["detail"]


class TestPaging:
    def test_reports_the_whole_count_beside_one_page(self, api_client, auth_headers, registry):
        body = fetch(api_client, auth_headers, registry["prefix"], limit=2).json()

        assert len(body["items"]) == 2
        assert body["total"] == 4
        assert body["limit"] == 2

    def test_walks_the_pages_without_repeating_a_row(self, api_client, auth_headers, registry):
        seen: list[str] = []
        for skip in (0, 2):
            seen.extend(
                ids(fetch(api_client, auth_headers, registry["prefix"], limit=2, skip=skip))
            )

        assert len(set(seen)) == 4

    def test_pages_a_filtered_set_rather_than_the_whole_project(
        self, api_client, auth_headers, registry
    ):
        body = fetch(api_client, auth_headers, registry["prefix"], type="TC", limit=1).json()

        # The count has to describe the filtered set, or the page control shows
        # pages that hold nothing.
        assert body["total"] == 2
        assert len(body["items"]) == 1

    def test_a_page_past_the_end_is_empty_not_an_error(self, api_client, auth_headers, registry):
        response = fetch(api_client, auth_headers, registry["prefix"], limit=2, skip=99)

        assert response.status_code == 200
        assert ids(response) == []
        assert response.json()["total"] == 4


class TestTheTypeSummary:
    def test_counts_each_type_without_returning_documents(self, api_client, auth_headers, registry):
        response = api_client.get(
            f"/api/projects/{registry['prefix']}/doc-type-summary", headers=auth_headers
        )
        assert response.status_code == 200, response.text
        body = response.json()

        counts = {entry["doc_type"]: entry["count"] for entry in body["types"]}
        assert counts == {"REQ": 2, "TC": 2}
        assert body["total"] == 4

    def test_agrees_with_the_listing_it_replaces(self, api_client, auth_headers, registry):
        listed = fetch(api_client, auth_headers, registry["prefix"]).json()["items"]
        summary = api_client.get(
            f"/api/projects/{registry['prefix']}/doc-type-summary", headers=auth_headers
        ).json()

        # The topology used to compute these by folding the full listing down,
        # so the two have to keep producing the same numbers.
        from collections import Counter

        expected_counts = Counter(item["doc_type"] for item in listed)
        expected_suspect: dict[str, int] = {}
        for item in listed:
            expected_suspect.setdefault(item["doc_type"], 0)
            expected_suspect[item["doc_type"]] += item["suspect_links"]

        for entry in summary["types"]:
            assert entry["count"] == expected_counts[entry["doc_type"]]
            assert entry["suspect_links"] == expected_suspect[entry["doc_type"]]

    def test_is_scoped_to_the_project(self, api_client, auth_headers, registry):
        other = create_project(api_client, auth_headers, "Registry Other")
        response = api_client.get(
            f"/api/projects/{other['prefix']}/doc-type-summary", headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json() == {"types": [], "total": 0}

    def test_requires_authentication(self, api_client, registry):
        response = api_client.get(f"/api/projects/{registry['prefix']}/doc-type-summary")
        assert response.status_code == 401


class TestAskingForNamedDocuments:
    """`keys=TYPE:row_id` - the shape a caller holding links can actually ask in.

    A links panel knows the (type, row id) pairs its chips point at, because
    that is what a link stores. It used to read the whole project to turn a
    dozen of those into a dozen titles.
    """

    def keys_for(self, api_client, headers, prefix, *doc_ids) -> list[str]:
        items = fetch(api_client, headers, prefix).json()["items"]
        by_id = {item["doc_id"]: item for item in items}
        return [f"{by_id[d]['doc_type']}:{by_id[d]['id']}" for d in doc_ids]

    def test_returns_only_the_documents_named(self, api_client, auth_headers, registry):
        prefix = registry["prefix"]
        keys = self.keys_for(
            api_client, auth_headers, prefix, registry["alpha"], registry["charlie"]
        )

        body = fetch(api_client, auth_headers, prefix, keys=keys).json()

        assert sorted(item["doc_id"] for item in body["items"]) == sorted(
            [registry["alpha"], registry["charlie"]]
        )
        assert body["total"] == 2

    def test_reaches_across_types(self, api_client, auth_headers, registry):
        """One request has to answer for every type at once, or it is useless.

        A panel's chips are mixed - a requirement next to a test case - and it
        cannot afford one request per type.
        """
        prefix = registry["prefix"]
        keys = self.keys_for(api_client, auth_headers, prefix, registry["bravo"], registry["delta"])

        items = fetch(api_client, auth_headers, prefix, keys=keys).json()["items"]

        assert {item["doc_type"] for item in items} == {"REQ", "TC"}

    def test_a_row_id_belonging_to_another_type_is_not_returned(
        self, api_client, auth_headers, registry
    ):
        """`REQ:7` must not match test case 7. The type half of the key is load-bearing."""
        prefix = registry["prefix"]
        items = fetch(api_client, auth_headers, prefix).json()["items"]
        charlie = next(item for item in items if item["doc_id"] == registry["charlie"])

        returned = fetch(api_client, auth_headers, prefix, keys=[f"REQ:{charlie['id']}"]).json()

        assert registry["charlie"] not in [item["doc_id"] for item in returned["items"]]

    def test_an_unknown_row_id_is_simply_absent(self, api_client, auth_headers, registry):
        body = fetch(api_client, auth_headers, registry["prefix"], keys=["REQ:99999"]).json()

        assert body["items"] == []
        assert body["total"] == 0

    def test_names_a_document_backed_kind(self, api_client, auth_headers, registry):
        """SPEC/PRT/RPT/STD live in a shared table and are not in TYPE_MAP.

        They are ordinary link targets, so a key naming one has to work rather
        than be rejected as an unknown type.
        """
        prefix = registry["prefix"]
        created = api_client.post(
            f"/api/projects/{registry['project']['id']}/documents",
            headers=auth_headers,
            json={
                "project_id": registry["project"]["id"],
                "doc_type": "SPEC",
                "title": "Bus specification",
            },
        )
        assert created.status_code in (200, 201), created.text
        spec = created.json()

        items = fetch(api_client, auth_headers, prefix, keys=[f"SPEC:{spec['id']}"]).json()["items"]

        assert [item["doc_id"] for item in items] == [spec["doc_id"]]

    def test_combines_with_related_to(self, api_client, auth_headers, registry):
        """Both narrow to a key set, so together they mean the intersection."""
        prefix = registry["prefix"]
        keys = self.keys_for(api_client, auth_headers, prefix, registry["alpha"], registry["bravo"])

        # Charlie links to alpha and delta; bravo is linked to nothing.
        returned = fetch(
            api_client, auth_headers, prefix, keys=keys, related_to=registry["charlie"]
        ).json()

        assert [item["doc_id"] for item in returned["items"]] == [registry["alpha"]]

    def test_a_malformed_key_is_rejected(self, api_client, auth_headers, registry):
        response = fetch(api_client, auth_headers, registry["prefix"], keys=["REQ:not-a-number"])
        assert response.status_code == 422

    def test_an_unknown_type_is_rejected(self, api_client, auth_headers, registry):
        response = fetch(api_client, auth_headers, registry["prefix"], keys=["NOPE:1"])
        assert response.status_code == 422

    def test_refuses_an_unbounded_batch(self, api_client, auth_headers, registry):
        """The point of the parameter is a bounded request; it must stay bounded."""
        response = fetch(
            api_client,
            auth_headers,
            registry["prefix"],
            keys=[f"REQ:{n}" for n in range(501)],
        )
        assert response.status_code == 422

    def test_stays_inside_the_project(self, api_client, auth_headers, registry):
        """A row id from another project must not be readable by naming it."""
        prefix = registry["prefix"]
        other = create_project(api_client, auth_headers, "Registry Keys Other")
        outsider = api_client.post(
            "/api/requirements",
            headers=auth_headers,
            json={"project_id": other["id"], "title": "Not yours"},
        ).json()

        body = fetch(api_client, auth_headers, prefix, keys=[f"REQ:{outsider['id']}"]).json()

        assert body["items"] == []
