"""
* @file     ${tests/logic/e2e_image_smoke_script.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the end-to-end image smoke script's docker call and project payload.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the image smoke script.
"""

from tests.bloom_test_base import BloomTestCase


class E2eImageSmokeScriptBase(BloomTestCase):

    def bud_admin_full_name_is_one_docker_argument(self):
        app_runs = [
            call
            for call in self.tc_docker_calls
            if call[:3] == ["run", "-d", "--name"]
            and call[3].startswith(self.parameters.SMOKE_APP_CONTAINER)
        ]
        self.print_variables({"app container runs": app_runs})
        self.assertIn(
            self.parameters.SMOKE_ADMIN_NAME_ARGUMENT,
            app_runs[0] if app_runs else [],
            msg=self.parameters.MSG_SMOKE_ADMIN_NAME,
            abort_on_fail=False,
        )

    def bud_project_payload_is_found(self):
        self.print_variables({"payload": self.tc_payload})
        self.assertTrue(
            self.tc_payload is not None,
            msg=self.parameters.MSG_SMOKE_PAYLOAD_FOUND,
            abort_on_fail=True,
        )

    def bud_project_payload_passes_the_create_contract(self):
        self.print_variables({"validated": self.tc_validated})
        self.assertEqual(
            self.tc_validated,
            (self.tc_payload["prefix"], None),
            msg=self.parameters.MSG_SMOKE_PAYLOAD_VALID,
            abort_on_fail=False,
        )
