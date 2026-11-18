"""
* @file     ${tests/api/profile_picture.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests uploading, reading, replacing and removing an account picture.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the account picture.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProfilePictureBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_picture_is_stored_normalised_for_its_account(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        self.assertEqual(
            self.bloom.bloom_api_picture(first).status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_PIC_NONE,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/auth/me/picture",
        )
        uploaded = self.bloom.bloom_api_put_picture(first, self.bloom.bloom_picture())
        self.assertEqual(
            (
                uploaded.status,
                uploaded.body["has_profile_picture"],
                "profile_picture" in uploaded.body,
            ),
            (values.STATUS_OK, True, False),
            msg=values.MSG_PIC_UPLOADED,
            abort_on_fail=False,
            method="PUT",
            endpoint="/api/auth/me/picture",
        )
        stored = self.bloom.bloom_api_picture(first)
        self.assertEqual(
            (
                stored.status,
                stored.headers["content-type"],
                stored.headers["cache-control"],
                self.bloom.bloom_picture_facts(stored.content)[:2],
            ),
            (values.STATUS_OK, "image/png", "private, no-store", ((256, 128), False)),
            msg=values.MSG_PIC_STORED,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/auth/me/picture",
        )
        flagged, other = (
            self.bloom.bloom_api_call("GET", "/api/auth/me", first).body["has_profile_picture"],
            self.bloom.bloom_api_picture(second).status,
        )
        other_upload = self.bloom.bloom_api_put_picture(
            second, self.bloom.bloom_picture("green")
        ).status
        self.assertEqual(
            (
                flagged,
                other,
                other_upload,
                self.bloom.bloom_api_picture(first).content == stored.content,
            ),
            (True, values.STATUS_NOT_FOUND, values.STATUS_OK, True),
            msg=values.MSG_PIC_SCOPED,
            abort_on_fail=False,
        )
        replaced = self.bloom.bloom_api_put_picture(first, self.bloom.bloom_picture("blue")).status
        self.assertEqual(
            (replaced, self.bloom.bloom_api_picture(first).content != stored.content),
            (values.STATUS_OK, True),
            msg=values.MSG_PIC_REPLACED,
            abort_on_fail=False,
        )

    def bud_a_refused_upload_keeps_the_saved_picture(self):
        for what, data, mime, status in self.parameters.PIC_REJECTED:
            first, _ = self.bloom.bloom_new_picture_accounts()
            self.bloom.bloom_api_put_picture(first, self.bloom.bloom_picture())
            before = self.bloom.bloom_api_picture(first).content
            refused = self.bloom.bloom_api_put_picture(first, data, mime)
            self.assertEqual(
                (refused.status, self.bloom.bloom_api_picture(first).content == before),
                (status, True),
                msg=self.parameters.MSG_PIC_REJECTED.format(what=what, status=status),
                abort_on_fail=False,
                method="PUT",
                endpoint="/api/auth/me/picture",
            )

    def bud_a_picture_needs_a_signed_in_account_401(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        answers = (
            self.bloom.bloom_api_picture().status,
            self.bloom.bloom_api_put_picture({}, self.bloom.bloom_picture()).status,
            self.bloom.bloom_api_picture(method="DELETE").status,
        )
        self.assertEqual(
            answers,
            (values.STATUS_UNAUTHORIZED,) * 3,
            msg=values.MSG_PIC_ANONYMOUS,
            abort_on_fail=False,
        )

    def bud_removing_a_picture_is_account_scoped_and_repeatable(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        self.bloom.bloom_api_put_picture(first, self.bloom.bloom_picture())
        self.bloom.bloom_api_put_picture(second, self.bloom.bloom_picture("green"))
        before_first, before_second = (
            self.bloom.bloom_api_call("GET", "/api/auth/me", first).body,
            self.bloom.bloom_api_call("GET", "/api/auth/me", second).body,
        )
        second_picture = self.bloom.bloom_api_picture(second).content
        removed = self.bloom.bloom_api_call("DELETE", "/api/auth/me/picture", first)
        after_first = self.bloom.bloom_api_call("GET", "/api/auth/me", first).body
        kept = set(before_first) - {"has_profile_picture", "profile_picture_url", "updated_at"}
        self.assertEqual(
            (
                removed.status,
                removed.body["has_profile_picture"],
                "profile_picture" in removed.body,
                {key: after_first[key] for key in kept} == {key: before_first[key] for key in kept},
                self.bloom.bloom_api_picture(first).status,
            ),
            (values.STATUS_OK, False, False, True, values.STATUS_NOT_FOUND),
            msg=values.MSG_PIC_REMOVED,
            abort_on_fail=False,
            method="DELETE",
            endpoint="/api/auth/me/picture",
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/auth/me", second).body == before_second,
                self.bloom.bloom_api_picture(second).content == second_picture,
            ),
            (True, True),
            msg=values.MSG_PIC_OTHER_KEPT,
            abort_on_fail=False,
        )
        again = self.bloom.bloom_api_picture(first, method="DELETE").status
        self.assertEqual(
            (
                again,
                self.bloom.bloom_api_put_picture(first, self.bloom.bloom_picture("blue")).status,
                self.bloom.bloom_api_picture(first).status,
            ),
            (values.STATUS_OK, values.STATUS_OK, values.STATUS_OK),
            msg=values.MSG_PIC_REPEAT,
            abort_on_fail=False,
        )

    def bud_the_format_must_match_and_the_size_is_bounded(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        wrong_format = self.bloom.bloom_api_put_picture(
            first, self.bloom.bloom_picture(), "image/jpeg"
        ).status
        too_large = self.bloom.bloom_api_put_picture(
            first, self.bloom.bloom_picture(size=(4001, 4000), mode="1")
        ).status
        self.assertEqual(
            (wrong_format, too_large, self.bloom.bloom_api_picture(first).status),
            (values.STATUS_UNSUPPORTED_MEDIA, values.STATUS_UNPROCESSABLE, values.STATUS_NOT_FOUND),
            msg=values.MSG_PIC_FORMAT,
            abort_on_fail=False,
        )

    def bud_a_rotated_jpeg_is_stored_upright_without_exif(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        uploaded = self.bloom.bloom_api_put_picture(
            first, self.bloom.bloom_rotated_jpeg(), "image/jpeg"
        )
        size, _, exif = self.bloom.bloom_picture_facts(self.bloom.bloom_api_picture(first).content)
        self.assertEqual(
            (uploaded.status, size, exif),
            (values.STATUS_OK, (128, 256), False),
            msg=values.MSG_PIC_TURNED,
            abort_on_fail=False,
        )

    def bud_a_repeated_orientation_tag_is_read_once(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        uploaded = self.bloom.bloom_api_put_picture(
            first, self.bloom.bloom_jpeg_with_repeated("orientation"), "image/jpeg"
        )
        size, _, exif = self.bloom.bloom_picture_facts(self.bloom.bloom_api_picture(first).content)
        self.assertEqual(
            (uploaded.status, size, exif),
            (values.STATUS_OK, (128, 256), False),
            msg=values.MSG_PIC_FIRST_TAG,
            abort_on_fail=False,
        )

    def bud_a_repeated_image_count_is_refused_415(self):
        values = self.parameters
        first, second = self.bloom.bloom_new_picture_accounts()
        uploaded = self.bloom.bloom_api_put_picture(
            first, self.bloom.bloom_jpeg_with_repeated("image count"), "image/jpeg"
        )
        self.assertEqual(
            (uploaded.status, self.bloom.bloom_api_picture(first).status),
            (values.STATUS_UNSUPPORTED_MEDIA, values.STATUS_NOT_FOUND),
            msg=values.MSG_PIC_MPF,
            abort_on_fail=False,
        )
