"""
* @file     ${tests/logic/BLOOM_notifications.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Notifications reach the assignee who can see the artefact, are private to their user and can be marked read.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests notifications with an administrator and a reviewer in one project; each step starts from a new database.
"""

from tests.logic.notifications import NotificationsBase


class NotificationsTest(NotificationsBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    NotificationsTest().run()
