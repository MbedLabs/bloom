"""
* @file     ${tests/logic/notifications.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests in-app notifications: the service, the API and what sends them.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the in-app notifications.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class NotificationsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_notification_is_stored_for_another_user_only(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        created = self.bloom.bloom_notify(users.reviewer, users.admin, "Hello")
        skipped = self.bloom.bloom_notify(users.admin, users.admin, "Self")
        rows = self.bloom.bloom_list_notification_rows()
        self.assertEqual(
            (created is not None, [row.user_id for row in rows]),
            (True, [users.reviewer]),
            msg=values.MSG_NTF_CREATED,
            abort_on_fail=False,
        )
        self.assertEqual(skipped, None, msg=values.MSG_NTF_SELF, abort_on_fail=False)

    def bud_an_unchanged_assignee_is_not_notified(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        self.bloom.bloom_notify_same_assignee(users.project, users.reviewer, users.admin)
        self.assertEqual(
            self.bloom.bloom_list_notification_rows(),
            [],
            msg=values.MSG_NTF_SAME_ASSIGNEE,
            abort_on_fail=False,
        )

    def bud_creating_a_requirement_notifies_its_reviewer(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        self.bloom.bloom_create_requirement_as(
            users.admin,
            project_id=users.project,
            title="Login shall work",
            reviewer_id=users.reviewer,
        )
        rows = self.bloom.bloom_list_notification_rows()
        self.print_variables(
            {
                "notifications": [
                    (row.user_id, row.event_type, row.title, row.link_path) for row in rows
                ]
            }
        )
        self.assertEqual(
            [
                (
                    row.user_id,
                    row.event_type,
                    "reviewer" in row.title,
                    values.NTF_REQUIREMENT_LINK in (row.link_path or ""),
                )
                for row in rows
            ],
            [(users.reviewer, "assignment", True, True)],
            msg=values.MSG_NTF_REVIEWER,
            abort_on_fail=False,
        )

    def bud_a_new_approver_is_notified_once(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        requirement = self.bloom.bloom_create_requirement_as(
            users.admin, project_id=users.project, title="Base req"
        )
        self.bloom.bloom_update_requirement_as(users.admin, requirement, approver_id=users.reviewer)
        rows = self.bloom.bloom_list_notification_rows()
        self.assertEqual(
            [(row.event_type, "approver" in row.title) for row in rows],
            [("assignment", True)],
            msg=values.MSG_NTF_APPROVER,
            abort_on_fail=False,
        )
        self.bloom.bloom_update_requirement_as(
            users.admin, requirement, approver_id=users.reviewer, title="Renamed"
        )
        self.assertEqual(
            len(self.bloom.bloom_list_notification_rows()),
            1,
            msg=values.MSG_NTF_APPROVER_ONCE,
            abort_on_fail=False,
        )

    def bud_notifications_are_listed_counted_and_marked_read(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        for number in range(3):
            self.bloom.bloom_notify(users.reviewer, users.admin, f"N{number}")
        listed = self.bloom.bloom_list_notifications_as(users.reviewer)
        self.assertEqual(
            (listed.total, listed.unread, self.bloom.bloom_unread_count(users.reviewer)),
            (3, 3, 3),
            msg=values.MSG_NTF_LIST,
            abort_on_fail=False,
        )
        marked, _ = self.bloom.bloom_mark_read(users.reviewer, listed.items[0].id)
        self.assertEqual(
            (marked, self.bloom.bloom_unread_count(users.reviewer)),
            (True, 2),
            msg=values.MSG_NTF_MARK_ONE,
            abort_on_fail=False,
        )
        self.bloom.bloom_mark_all_read(users.reviewer)
        unread = self.bloom.bloom_list_notifications_as(users.reviewer, unread_only=True)
        self.assertEqual(
            (self.bloom.bloom_unread_count(users.reviewer), unread.items, unread.total),
            (0, [], 0),
            msg=values.MSG_NTF_MARK_ALL,
            abort_on_fail=False,
        )

    def bud_notifications_are_private_to_their_user_404(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        created = self.bloom.bloom_notify(users.reviewer, users.admin, "Private")
        listed = self.bloom.bloom_list_notifications_as(users.admin)
        _, refused = self.bloom.bloom_mark_read(users.admin, created)
        self.assertEqual(
            (listed.total, refused),
            (0, values.STATUS_NOT_FOUND),
            msg=values.MSG_NTF_PRIVATE,
            abort_on_fail=False,
        )

    def bud_a_comment_notifies_only_assignees_who_see_the_requirement(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        kept = self.bloom.bloom_add_external_assignee_requirement(
            users.project, "Internal", users.reviewer
        )
        self.bloom.bloom_set_requirement_assignees(kept.requirement, reviewer_id=users.admin)
        self.bloom.bloom_comment_on_requirement(users.admin, kept.requirement, "Please check")
        self.assertEqual(
            [row.user_id for row in self.bloom.bloom_list_notification_rows()],
            [users.reviewer],
            msg=values.MSG_NTF_VISIBLE_ASSIGNEE,
            abort_on_fail=False,
        )
        self.bloom.bloom_set_requirement_assignees(kept.requirement, approver_id=kept.external)
        self.bloom.bloom_comment_on_requirement(
            users.admin, kept.requirement, "Hidden approver receives nothing"
        )
        self.assertEqual(
            [row.user_id for row in self.bloom.bloom_list_notification_rows()],
            [users.reviewer],
            msg=values.MSG_NTF_HIDDEN_APPROVER,
            abort_on_fail=False,
        )

    def bud_hiding_a_requirement_from_its_reviewer_is_refused_409(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        kept = self.bloom.bloom_add_external_assignee_requirement(
            users.project, "Customer", users.reviewer
        )
        refused = self.bloom.bloom_update_requirement_as(
            users.admin, kept.requirement, req_origin="Internal"
        )
        self.print_variables({"refused": refused})
        self.assertEqual(
            refused,
            (values.STATUS_CONFLICT, values.NTF_HIDDEN_DETAIL),
            msg=values.MSG_NTF_HIDING_REFUSED,
            abort_on_fail=False,
        )

    def bud_a_kept_external_reviewer_cannot_sign(self):
        self.bloom.bloom_new_database()
        users = self.bloom.bloom_seed_notification_users()
        values = self.parameters
        kept = self.bloom.bloom_add_external_assignee_requirement(
            users.project, "Customer", users.reviewer
        )
        self.assertEqual(
            self.bloom.bloom_requirement_signers(users.admin, kept.requirement),
            (False, True),
            msg=values.MSG_NTF_CANNOT_SIGN,
            abort_on_fail=False,
        )
