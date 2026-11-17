"""
* @file     ${tests/api/user_identity_picture.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a person's current picture accompanies their identity wherever it is read.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the identity pictures.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class UserIdentityPictureBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_directory_and_mentions_carry_each_picture(self):
        values = self.parameters
        world = self.bloom.bloom_new_identity_world()
        people = self.bloom.bloom_api_call("GET", "/api/users", world.admin).body
        pictures = {
            person["id"]: self.bloom.bloom_picture_of(person["profile_picture_url"])
            for person in people
        }
        self.assertEqual(
            (len(set(pictures.values())), None in pictures.values()),
            (3, False),
            msg=values.MSG_IDP_DIRECTORY,
            abort_on_fail=False,
        )
        mentionable = self.bloom.bloom_api_call(
            "GET", "/api/users/mentionable", world.member, params={"project_id": world.project}
        )
        self.assertEqual(
            (
                mentionable.status,
                len(mentionable.body),
                all(
                    self.bloom.bloom_picture_of(person["profile_picture_url"])
                    == pictures[person["id"]]
                    for person in mentionable.body
                ),
            ),
            (values.STATUS_OK, 2, True),
            msg=values.MSG_IDP_MENTIONS,
            abort_on_fail=False,
        )
        refused = (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND)
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/users", world.member).status,
                self.bloom.bloom_api_call(
                    "GET",
                    "/api/users/mentionable",
                    world.member,
                    params={"project_id": world.hidden},
                ).status
                in refused,
                self.bloom.bloom_api_call(
                    "GET",
                    "/api/users/mentionable",
                    world.outsider,
                    params={"project_id": world.project},
                ).status
                in refused,
                self.bloom.bloom_api_call("GET", "/api/users").status,
            ),
            (values.STATUS_FORBIDDEN, True, True, values.STATUS_UNAUTHORIZED),
            msg=values.MSG_IDP_GUARDS,
            abort_on_fail=False,
        )

    def bud_the_roster_and_the_audit_show_the_same_picture(self):
        values = self.parameters
        world = self.bloom.bloom_new_identity_world()
        options = self.bloom.bloom_api_call(
            "GET", "/api/groups/assignment-options", world.admin
        ).body["users"]
        pictures = {person["id"]: person["profile_picture_url"] for person in options}
        roster = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{world.project}/members", world.admin
        ).body
        actor = self.bloom.bloom_api_call(
            "GET", "/api/audit", world.admin, params={"action": "identity.read"}
        ).body["items"][0]
        self.assertEqual(
            (roster[0]["profile_picture_url"], actor["actor_profile_picture_url"]),
            (pictures[roster[0]["user_id"]], pictures[actor["actor_user_id"]]),
            msg=values.MSG_IDP_ROSTER,
            abort_on_fail=False,
        )

    def bud_a_comment_carries_its_author_and_picture(self):
        values = self.parameters
        world = self.bloom.bloom_new_identity_world()
        path = f"/api/artefacts/requirement/{world.requirement}/comments"
        me = self.bloom.bloom_api_call("GET", "/api/auth/me", world.member).body
        forged = self.bloom.bloom_api_call(
            "POST", path, world.member, json={"body": "Review note", "author_user_id": 999}
        )
        self.assertEqual(
            forged.status,
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_IDP_AUTHOR_FIELD,
            abort_on_fail=False,
            method="POST",
            endpoint=path,
        )
        created = self.bloom.bloom_api_call(
            "POST", path, world.member, json={"body": "Review note"}
        )
        self.assertEqual(
            (
                created.status,
                created.body["author_user_id"],
                created.body["author_profile_picture_url"],
            ),
            (values.STATUS_CREATED, me["id"], me["profile_picture_url"]),
            msg=values.MSG_IDP_COMMENT,
            abort_on_fail=False,
            method="POST",
            endpoint=path,
        )
        renamed = self.bloom.bloom_api_call(
            "PUT", "/api/auth/me", world.member, json={"full_name": "Changed Name"}
        ).status
        stored = self.bloom.bloom_api_call("GET", path, world.admin).body[0]
        self.assertEqual(
            (
                renamed,
                stored["author_user_id"],
                stored["author_profile_picture_url"],
                self.bloom.bloom_api_call("GET", path, world.outsider).status
                in (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND),
            ),
            (values.STATUS_OK, me["id"], me["profile_picture_url"], True),
            msg=values.MSG_IDP_COMMENT_KEPT,
            abort_on_fail=False,
        )
        removed = self.bloom.bloom_api_call("DELETE", "/api/auth/me/picture", world.member).status
        self.assertEqual(
            (
                removed,
                self.bloom.bloom_api_call("GET", path, world.admin).body[0][
                    "author_profile_picture_url"
                ],
            ),
            (values.STATUS_OK, None),
            msg=values.MSG_IDP_COMMENT_REMOVED,
            abort_on_fail=False,
        )

    def bud_the_directory_follows_a_replaced_and_a_removed_picture(self):
        values = self.parameters
        world = self.bloom.bloom_new_identity_world()
        own = self.bloom.bloom_api_call("GET", "/api/auth/me", world.member).body["id"]
        listed = lambda: next(
            person
            for person in self.bloom.bloom_api_call("GET", "/api/users", world.admin).body
            if person["id"] == own
        )["profile_picture_url"]
        previous = listed()
        self.bloom.bloom_api_put_picture(
            world.member, self.bloom.bloom_picture("red", size=(16, 16))
        )
        replaced = listed()
        self.assertEqual(
            (replaced != previous, replaced is not None),
            (True, True),
            msg=values.MSG_IDP_REPLACED,
            abort_on_fail=False,
        )
        removed = self.bloom.bloom_api_call("DELETE", "/api/auth/me/picture", world.member).status
        self.assertEqual(
            (removed, listed()),
            (values.STATUS_OK, None),
            msg=values.MSG_IDP_REMOVED,
            abort_on_fail=False,
        )

    def bud_an_access_request_shows_its_requester(self):
        values = self.parameters
        world = self.bloom.bloom_new_identity_world()
        person = self.bloom.bloom_api_call("GET", "/api/auth/me", world.member).body
        request = self.bloom.bloom_api_call("GET", "/api/access-requests", world.admin).body[0]
        self.assertEqual(
            (
                request["requester_name"],
                request["requester_profile_picture_url"],
                self.bloom.bloom_api_call("GET", "/api/access-requests", world.member).status,
                self.bloom.bloom_api_call("GET", "/api/access-requests", world.outsider).status,
            ),
            (
                person["full_name"],
                person["profile_picture_url"],
                values.STATUS_FORBIDDEN,
                values.STATUS_FORBIDDEN,
            ),
            msg=values.MSG_IDP_REQUEST,
            abort_on_fail=False,
        )
        removed = self.bloom.bloom_api_call("DELETE", "/api/auth/me/picture", world.member).status
        self.assertEqual(
            (
                removed,
                self.bloom.bloom_api_call("GET", "/api/access-requests", world.admin).body[0][
                    "requester_profile_picture_url"
                ],
            ),
            (values.STATUS_OK, None),
            msg=values.MSG_IDP_REQUEST_REMOVED,
            abort_on_fail=False,
        )

    def bud_activity_and_notifications_name_the_real_actor(self):
        values = self.parameters
        world = self.bloom.bloom_new_identity_world()
        person = self.bloom.bloom_api_call("GET", "/api/auth/me", world.member).body
        base = f"/api/artefacts/requirement/{world.requirement}"
        self.bloom.bloom_api_call(
            "POST", base + "/comments", world.member, json={"body": "Review note"}
        )
        event = self.bloom.bloom_api_call("GET", base + "/activity", world.admin).body[0]
        notice = self.bloom.bloom_api_call("GET", "/api/notifications", world.admin).body["items"][
            0
        ]
        self.assertEqual(
            (
                (event["actor_user_id"], event["actor_name"], event["actor_profile_picture_url"]),
                (notice["actor_user_id"], notice["actor_profile_picture_url"]),
            ),
            (
                (person["id"], person["full_name"], person["profile_picture_url"]),
                (person["id"], person["profile_picture_url"]),
            ),
            msg=values.MSG_IDP_ACTIVITY,
            abort_on_fail=False,
        )
        read_path = f"/api/notifications/{notice['id']}/read"
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/notifications", world.outsider).body[
                    "items"
                ],
                self.bloom.bloom_api_call("POST", read_path, world.outsider).status,
                self.bloom.bloom_api_call("GET", base + "/activity", world.outsider).status
                in (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND),
            ),
            ([], values.STATUS_NOT_FOUND, True),
            msg=values.MSG_IDP_NOTICE_GUARD,
            abort_on_fail=False,
        )
        self.bloom.bloom_api_call(
            "PUT", "/api/auth/me", world.member, json={"full_name": "Changed Actor"}
        )
        self.assertEqual(
            self.bloom.bloom_api_call("GET", base + "/activity", world.admin).body[0]["actor_name"],
            "Changed Actor",
            msg=values.MSG_IDP_ACTOR_RENAMED,
            abort_on_fail=False,
        )
        self.bloom.bloom_api_call("DELETE", "/api/auth/me/picture", world.member)
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", base + "/activity", world.admin).body[0][
                    "actor_profile_picture_url"
                ],
                self.bloom.bloom_api_call("GET", "/api/notifications", world.admin).body["items"][
                    0
                ]["actor_profile_picture_url"],
                self.bloom.bloom_api_call("POST", read_path, world.admin).body[
                    "actor_profile_picture_url"
                ],
            ),
            (None, None, None),
            msg=values.MSG_IDP_ACTOR_REMOVED,
            abort_on_fail=False,
        )
