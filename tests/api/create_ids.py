"""
* @file     ${tests/api/create_ids.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the public ids the server assigns when artefacts are created.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the assigned public ids.
"""

import re

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class CreateIdsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_creates_assign_public_ids(self):
        prefix = self.parameters.CREATE_ID_PREFIX
        for type_code, outcome in self.tc_created.items():
            public_id = str(outcome.public_id)
            self.print_variables(
                {"type": type_code, "status": outcome.status, "public id": public_id}
            )
            self.assertEqual(
                outcome.status,
                self.parameters.STATUS_CREATED,
                msg=self.parameters.MSG_CREATE_ID_CREATED,
                abort_on_fail=False,
            )
            self.assertRegex(
                public_id,
                self.tc_pattern,
                msg=self.parameters.MSG_CREATE_ID_PATTERN,
                abort_on_fail=False,
            )
            self.assertTrue(
                public_id.startswith(f"{prefix}-{type_code}-"),
                msg=self.parameters.MSG_CREATE_ID_PREFIX,
                expected=f"{prefix}-{type_code}-",
                actual=public_id,
                abort_on_fail=False,
            )
            self.assertRegex(
                public_id,
                "^" + re.escape(prefix) + "-" + re.escape(type_code) + r"-\d{3}$",
                msg=self.parameters.MSG_CREATE_ID_SHAPE,
                abort_on_fail=False,
            )
