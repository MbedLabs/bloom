"""
* @file     ${tests/api/requirement_description.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the requirement description through the requirements API.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement description.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class RequirementDescriptionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_requirements_are_created(self):
        statuses = [answer.status for answer in (self.from_body, self.tagged, self.untagged)]
        self.print_variables({"statuses": statuses})
        self._equal(
            statuses,
            [self.parameters.STATUS_CREATED] * len(statuses),
            self.parameters.MSG_DESCRIPTION_CREATED,
        )

    def bud_editor_content_on_create_becomes_the_description(self):
        from_body = self._text_of(self.from_body.body)
        self.print_variables({"created": from_body})
        self._equal(
            from_body,
            self.parameters.DESCRIPTION_FROM_BODY,
            self.parameters.MSG_DESCRIPTION_FROM_BODY,
        )

    def bud_detail_holds_the_description(self):
        detail = self._text_of(
            self.bloom.bloom_api_call("GET", self._path_of(self.from_body), self.admin).body
        )
        self.print_variables({"detail": detail})
        self._equal(
            detail,
            self.parameters.DESCRIPTION_FROM_BODY,
            self.parameters.MSG_DESCRIPTION_DETAIL,
        )

    def bud_editor_content_on_edit_follows_the_description(self):
        answer = self.bloom.bloom_api_call(
            "PATCH",
            self._path_of(self.from_body),
            self.admin,
            json={"content_html": self.parameters.DESCRIPTION_EDIT_HTML},
        )
        edited = (answer.status, *self._text_of(answer.body))
        self.print_variables({"edited": edited})
        self._equal(
            edited,
            (self.parameters.STATUS_OK, *self.parameters.DESCRIPTION_AFTER_EDIT),
            self.parameters.MSG_DESCRIPTION_EDIT,
        )

    def bud_tag_in_a_new_description_creates_a_link(self):
        tagged_links = self._links_of(self.tagged)
        self.print_variables({"links": tagged_links})
        self._equal(
            tagged_links,
            [self.expected_link],
            self.parameters.MSG_DESCRIPTION_TAG_CREATE,
        )

    def bud_tag_added_on_edit_creates_a_link(self):
        untagged_links = self._links_of(self.untagged)
        retagged = self.bloom.bloom_api_call(
            "PATCH",
            self._path_of(self.untagged),
            self.admin,
            json={"description": f"Now follows #{self.spec.get('doc_id')}."},
        )
        retagged_links = (retagged.status, self._links_of(self.untagged))
        self.print_variables({"before": untagged_links, "after": retagged_links})
        self._equal(untagged_links, [], self.parameters.MSG_DESCRIPTION_NO_TAG)
        self._equal(
            retagged_links,
            (self.parameters.STATUS_OK, [self.expected_link]),
            self.parameters.MSG_DESCRIPTION_TAG_EDIT,
        )

    def _path_of(self, requirement):
        """Return the API path of the created requirement."""
        path = self.parameters.ARTEFACT_PATHS[self.parameters.REQUIREMENT_KIND]
        return f"{path}/{requirement.body.get('id')}"

    def _text_of(self, body):
        """Return the description and editor content fields of an answer body."""
        return tuple((body or {}).get(name) for name in self.parameters.DESCRIPTION_TEXT_FIELDS)

    def _links_of(self, requirement):
        """List the links whose source is the created requirement."""
        listed = self.bloom.bloom_api_call(
            "GET",
            "/api/links",
            self.admin,
            params={
                "project_id": self.project_id,
                "source_type": "REQ",
                "source_id": (requirement.body or {}).get("id"),
            },
        )
        return [
            (link["target_type"], link["target_id"], link["role"]) for link in listed.body or []
        ]

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
