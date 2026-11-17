"""
* @file     ${tests/api/mentionable_users.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests who can be mentioned in a project and what is disclosed about them.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the mention list.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class MentionableUsersBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_member_is_offered_the_project_members_and_administrators(self):
        answer = self.bloom.bloom_api_mentionable(self.world.grace, self.world.project)
        names = sorted(person["full_name"] for person in answer.body)
        self.print_variables({"offered": names})
        self.assertEqual(
            (answer.status, names),
            (self.parameters.STATUS_OK, self.parameters.MNT_OFFERED),
            msg=self.parameters.MSG_MNT_LIST,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/users/mentionable",
        )

    def bud_only_identity_and_picture_are_disclosed(self):
        people = self.bloom.bloom_api_mentionable(self.world.grace, self.world.project).body
        self.assertEqual(
            (
                all(set(person) == self.parameters.MNT_FIELDS for person in people),
                [person["profile_picture_url"] for person in people],
            ),
            (True, [None] * len(people)),
            msg=self.parameters.MSG_MNT_FIELDS,
            abort_on_fail=False,
        )

    def bud_people_outside_the_project_are_refused_403(self):
        for who, headers in (
            ("a user on no project", self.world.outsider),
            ("a member of another project", self.world.elsewhere),
        ):
            answer = self.bloom.bloom_api_mentionable(headers, self.world.project)
            self.assertEqual(
                answer.status,
                self.parameters.STATUS_FORBIDDEN,
                msg=self.parameters.MSG_MNT_REFUSED.format(who=who),
                abort_on_fail=False,
                method="GET",
                endpoint="/api/users/mentionable",
            )

    def bud_an_administrator_reads_any_project(self):
        answer = self.bloom.bloom_api_mentionable(self.world.admin, self.world.project)
        self.assertEqual(
            (answer.status, "Grace Hopper" in [person["full_name"] for person in answer.body]),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_MNT_ADMIN,
            abort_on_fail=False,
        )

    def bud_an_unknown_project_is_a_404(self):
        self.assertEqual(
            self.bloom.bloom_api_mentionable(self.world.admin, 999_999).status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_MNT_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_the_mention_list_is_its_own_route(self):
        self.assertNotEqual(
            self.bloom.bloom_api_mentionable(self.world.admin, self.world.project).status,
            self.parameters.STATUS_UNPROCESSABLE,
            msg=self.parameters.MSG_MNT_ROUTE,
            abort_on_fail=False,
        )
