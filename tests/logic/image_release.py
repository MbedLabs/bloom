"""
* @file     ${tests/logic/image_release.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the release promotion script without a registry.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the image release promotion.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImageReleaseBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_an_older_release_does_not_move_floating_tags(self):
        aliases = self.parameters.IMR_FLOATING
        self.assertEqual(
            self.bloom.bloom_eligible_aliases(aliases, "refs/tags/v1.0.0", "v1.1.0"),
            aliases[:2],
            msg=self.parameters.MSG_IMR_OLDER,
            abort_on_fail=False,
        )

    def bud_the_current_release_can_promote_stable(self):
        self.assertEqual(
            self.bloom.bloom_eligible_aliases(["image:stable"], "refs/tags/v1.1.0", "v1.1.0"),
            ["image:stable"],
            msg=self.parameters.MSG_IMR_CURRENT,
            abort_on_fail=False,
        )

    def bud_a_stale_branch_run_does_not_promote_latest(self):
        self.assertEqual(
            self.bloom.bloom_eligible_aliases(["image:latest"], "refs/heads/main", "v1.1.0", False),
            [],
            msg=self.parameters.MSG_IMR_STALE,
            abort_on_fail=False,
        )

    def bud_a_prerelease_does_not_promote_stable(self):
        self.assertEqual(
            self.bloom.bloom_eligible_aliases(
                ["image:stable"], "refs/tags/v1.2.0-beta.1", "v1.1.0"
            ),
            [],
            msg=self.parameters.MSG_IMR_PRERELEASE,
            abort_on_fail=False,
        )

    def bud_a_version_conflict_aborts_before_any_alias_changes(self):
        values = self.parameters
        refusal, executed = self.bloom.bloom_promote(
            values.IMR_IMAGE, ["image:stable", "image:1.1.0"], lambda _: values.IMR_OTHER
        )
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            ("Refusing to overwrite" in (refusal or ""), executed),
            (True, []),
            msg=values.MSG_IMR_CONFLICT,
            abort_on_fail=False,
        )

    def bud_a_repeated_promotion_preserves_the_digest(self):
        values = self.parameters
        refusal, executed = self.bloom.bloom_promote(
            values.IMR_IMAGE, ["image:1.1.0", "image:stable"], lambda _: values.IMR_DIGEST
        )
        self.assertEqual(
            (refusal, len(executed), [call[-1] for call in executed]),
            (None, 2, [values.IMR_IMAGE, values.IMR_IMAGE]),
            msg=values.MSG_IMR_REPEAT,
            abort_on_fail=False,
        )

    def bud_a_digest_mismatch_after_promotion_fails(self):
        values = self.parameters
        refusal, _ = self.bloom.bloom_promote(
            values.IMR_IMAGE, ["image:stable"], lambda _: values.IMR_OTHER
        )
        self.assertIn(
            "Digest verification", refusal or "", msg=values.MSG_IMR_MISMATCH, abort_on_fail=False
        )

    def bud_a_well_formed_reference_is_inspected(self):
        values = self.parameters
        for reference in values.IMR_GOOD_REFERENCES:
            found, calls = self.bloom.bloom_digest(reference, stdout=values.IMR_DIGEST + "\n")
            self.assertEqual(
                (found, calls),
                (
                    values.IMR_DIGEST,
                    [
                        [
                            "docker",
                            "buildx",
                            "imagetools",
                            "inspect",
                            reference,
                            "--format",
                            "{{.Manifest.Digest}}",
                        ]
                    ],
                ),
                msg=values.MSG_IMR_GOOD.format(reference=reference),
                abort_on_fail=False,
            )

    def bud_a_malformed_reference_is_refused_before_docker(self):
        values = self.parameters
        for reference in values.IMR_BAD_REFERENCES:
            found, calls = self.bloom.bloom_digest(reference)
            self.assertEqual(
                ("Invalid image reference" in str(found), calls),
                (True, []),
                msg=values.MSG_IMR_BAD.format(reference=reference),
                abort_on_fail=False,
            )

    def bud_a_missing_image_reports_no_digest(self):
        found, _ = self.bloom.bloom_digest(
            "ghcr.io/mbedlabs/product:sha-" + "0" * 40,
            returncode=1,
            stderr="ERROR: manifest unknown",
        )
        self.assertEqual(found, None, msg=self.parameters.MSG_IMR_MISSING, abort_on_fail=False)

    def bud_every_workflow_reference_shape_is_promoted(self):
        values = self.parameters
        source = f"ghcr.io/mbedlabs/bloom:sha-{values.IMR_COMMIT}"
        found, executed, inspected = self.bloom.bloom_promote_workflow(
            values.IMR_DIGEST, source, values.IMR_WORKFLOW_ALIASES
        )
        self.assertEqual(
            (found, executed, inspected),
            (
                values.IMR_DIGEST,
                len(values.IMR_WORKFLOW_ALIASES),
                {source, *values.IMR_WORKFLOW_ALIASES},
            ),
            msg=values.MSG_IMR_WORKFLOW,
            abort_on_fail=False,
        )
