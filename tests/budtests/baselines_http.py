"""Baselines over HTTP: what a reader with limited access gets from a stored snapshot."""

import secrets
import string

import tests.budtests.support  # noqa: F401
from budtestlibrary import BudTestCase
from fastapi.testclient import TestClient
from tests.budtests.config import BaselinesHttp as c
from tests.budtests.parameters import BaselinesHttp as p


class BaselinesHttp(BudTestCase):
    """A baseline of one requirement and one SPEC document, read by a user who may view
    requirements and baselines only."""

    def setUpClass(self):
        """Start Bloom in process; create the project, its two records, the baseline and the
        reader."""
        from app.core.config import settings
        from app.core.deps import limiter
        from app.main import app

        limiter.enabled = False
        self.context = TestClient(app, base_url=c.BASE_URL)
        self.client = self.context.__enter__()
        self.admin = self._login(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
        self.project = self._project()
        self.requirement = self._created(
            self.client.post(
                c.REQUIREMENTS_ROUTE,
                headers=self.admin,
                json={"project_id": self.project, "title": self._unique("Requirement")},
            )
        )
        self.document = self._created(
            self.client.post(
                c.DOCUMENTS_ROUTE.format(project_id=self.project),
                headers=self.admin,
                json={
                    "project_id": self.project,
                    "title": self._unique("Document"),
                    "doc_type": p.DOCUMENT_TYPE,
                },
            )
        )
        self.baseline = self._created(
            self.client.post(
                c.BASELINES_ROUTE,
                headers=self.admin,
                json={"project_id": self.project, "name": self._unique("Baseline")},
            )
        )["id"]
        self.reader = self._reader()

    def tearDownClass(self):
        """Stop Bloom."""
        self.context.__exit__(None, None, None)

    def _unique(self, stem: str) -> str:
        """``stem`` with a suffix unique to this call."""
        return f"{stem} {secrets.token_hex(4)}"

    def _created(self, response, statuses=(p.CREATED,)) -> dict:
        """The body of a set-up request that answered one of ``statuses``."""
        if response.status_code not in statuses:
            raise AssertionError(
                f"{response.request.method} {response.request.url.path}: "
                f"{response.status_code} {response.text}"
            )
        return response.json()

    def _login(self, email: str, password: str) -> dict:
        """Bearer headers of the account."""
        body = self._created(
            self.client.post(c.LOGIN_ROUTE, json={"email": email, "password": password}),
            (p.OK,),
        )
        return {"Authorization": f"Bearer {body['access_token']}"}

    def _project(self) -> int:
        """The id of a new project with a free prefix."""
        for _ in range(p.PREFIX_TRIES):
            prefix = "".join(
                secrets.choice(string.ascii_uppercase) for _ in range(p.PREFIX_LETTERS)
            )
            response = self.client.post(
                c.PROJECTS_ROUTE,
                headers=self.admin,
                json={"name": self._unique("Project"), "prefix": prefix},
            )
            if response.status_code == p.CREATED:
                return response.json()["id"]
            if p.TAKEN_PREFIX not in response.text:
                break
        raise AssertionError(f"project not created: {response.status_code} {response.text}")

    def _reader(self) -> dict:
        """Headers of a new user whose only group grants view on requirements and baselines
        in the project."""
        policy = self._created(
            self.client.post(
                c.POLICIES_ROUTE,
                headers=self.admin,
                json={"name": self._unique("Policy"), "rules": p.READER_RULES},
            )
        )
        group = self._created(
            self.client.post(
                c.GROUPS_ROUTE,
                headers=self.admin,
                json={"name": self._unique("Group"), "policy_ids": [policy["id"]]},
            )
        )
        self._created(
            self.client.post(
                c.GRANTS_ROUTE.format(group_id=group["id"]),
                headers=self.admin,
                json={"project_id": self.project},
            )
        )
        email = f"reader-{secrets.token_hex(4)}@example.com"
        user = self._created(
            self.client.post(
                c.USERS_ROUTE,
                headers=self.admin,
                json={
                    "email": email,
                    "full_name": p.READER_NAME,
                    "password": p.READER_PASSWORD,
                    "role": c.READER_ROLE,
                },
            ),
            p.USER_CREATED,
        )
        self._created(
            self.client.post(
                c.MEMBERS_ROUTE.format(group_id=group["id"]),
                headers=self.admin,
                json={"user_id": user["id"]},
            )
        )
        return self._login(email, p.READER_PASSWORD)

    def bud_a_reader_sees_only_the_records_they_may_read_now(self):
        """The reader gets the requirement's record, no document record, the captured
        document count and not the document's title."""
        response = self.client.get(
            c.BASELINE_ROUTE.format(baseline_id=self.baseline), headers=self.reader
        )
        self.assertEqual(
            response.status_code, p.OK, "the reader opens the baseline", abort_on_fail=True
        )
        snapshot = response.json()["snapshot"]
        self.assertEqual(
            [record["id"] for record in snapshot["requirements"]["records"]],
            [self.requirement["id"]],
            "the requirement's record is shown",
        )
        self.assertEqual(
            snapshot["documents"]["records"], p.NO_RECORDS, "no document record is shown"
        )
        self.assertEqual(
            snapshot["documents"]["count"],
            p.CAPTURED_DOCUMENTS,
            "the captured document count is kept",
        )
        self.assertNotIn(
            member=self.document["title"],
            container=snapshot["documents"]["titles"],
            msg="the document's title is not shown",
        )

    def bud_the_list_carries_counts_and_ids_without_records(self):
        """The project's baseline list gives the reader the requirement's public id and no
        records."""
        response = self.client.get(
            c.BASELINES_ROUTE, headers=self.reader, params={"project_id": self.project}
        )
        self.assertEqual(
            response.status_code, p.OK, "the reader lists the baselines", abort_on_fail=True
        )
        listed = [item for item in response.json() if item["id"] == self.baseline]
        self.assertEqual(
            len(listed), p.LISTED_ONCE, "the baseline is listed once", abort_on_fail=True
        )
        requirements = listed[0]["snapshot"]["requirements"]
        self.assertNotIn(
            member="records", container=requirements, msg="the list carries no records"
        )
        self.assertEqual(
            requirements["ids"],
            [self.requirement["req_id"]],
            "the list carries the requirement's public id",
        )
