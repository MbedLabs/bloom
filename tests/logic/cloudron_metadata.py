"""
* @file     ${tests/logic/cloudron_metadata.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Cloudron package metadata against the product release.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the Cloudron metadata.
"""

import json
import re

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class CloudronMetadataBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_manifest_names_the_product(self):
        self.print_variables({"title": self.manifest["title"], "tagline": self.manifest["tagline"]})
        self.assertEqual(
            self.manifest["title"],
            self.parameters.CLOUDRON_TITLE,
            msg=self.parameters.MSG_CLOUDRON_TITLE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.manifest["tagline"],
            self.parameters.CLOUDRON_TAGLINE,
            msg=self.parameters.MSG_CLOUDRON_TAGLINE,
            abort_on_fail=False,
        )

    def bud_description_opens_with_the_positioning(self):
        first = self.description.strip().splitlines()[0]
        self.print_variables({"first line": first})
        self.assertEqual(
            first,
            self.parameters.CLOUDRON_POSITIONING,
            msg=self.parameters.MSG_CLOUDRON_POSITIONING,
            abort_on_fail=False,
        )

    def bud_wording_avoids_retired_words(self):
        manifest = json.dumps(self.manifest).lower()
        description = self.description.strip().lower()
        embedded, self_hosted = self.parameters.CLOUDRON_RETIRED_WORDS
        self.assertNotIn(
            embedded, manifest, msg=self.parameters.MSG_CLOUDRON_MANIFEST_WORD, abort_on_fail=False
        )
        for word in (embedded, self_hosted):
            self.assertNotIn(
                word,
                description,
                msg=self.parameters.MSG_CLOUDRON_DESCRIPTION_WORD,
                abort_on_fail=False,
            )

    def bud_manifest_carries_the_product_version(self):
        self.print_variables(
            {
                "product": self.version,
                "version": self.manifest["version"],
                "upstream": self.manifest["upstreamVersion"],
            }
        )
        self.assertEqual(
            self.manifest["version"],
            self.version,
            msg=self.parameters.MSG_CLOUDRON_VERSION,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.manifest["upstreamVersion"],
            self.version,
            msg=self.parameters.MSG_CLOUDRON_UPSTREAM,
            abort_on_fail=False,
        )

    def bud_catalog_entry_matches_the_release(self):
        catalog = self.bloom.bloom_read_repo_json(self.parameters.CLOUDRON_CATALOG)
        current = catalog["versions"].get(self.version, {})
        manifest = current.get("manifest", {})
        self.print_variables(
            {
                "product": self.version,
                "version": manifest.get("version"),
                "upstream": manifest.get("upstreamVersion"),
                "changelog": str(manifest.get("changelog"))[:60],
                "state": current.get("publishState"),
            }
        )
        self.assertEqual(
            manifest.get("version"),
            self.version,
            msg=self.parameters.MSG_CLOUDRON_CATALOG_VERSION,
            abort_on_fail=False,
        )
        self.assertEqual(
            manifest.get("upstreamVersion"),
            self.version,
            msg=self.parameters.MSG_CLOUDRON_CATALOG_UPSTREAM,
            abort_on_fail=False,
        )
        self.assertEqual(
            manifest.get("description"),
            self.description,
            msg=self.parameters.MSG_CLOUDRON_CATALOG_DESCRIPTION,
            abort_on_fail=False,
        )
        self.assertFalse(
            str(manifest.get("changelog")).startswith(self.parameters.CLOUDRON_FILE_CHANGELOG),
            msg=self.parameters.MSG_CLOUDRON_CATALOG_CHANGELOG,
            abort_on_fail=False,
        )
        self.assertIn(
            current.get("publishState"),
            self.parameters.CLOUDRON_PUBLISH_STATES,
            msg=self.parameters.MSG_CLOUDRON_PUBLISH_STATE,
            abort_on_fail=False,
        )

    def bud_changelog_names_the_version(self):
        headers = [line for line in self.changelog.splitlines() if line.startswith("[")]
        self.print_variables({"product": self.version, "headers": headers[:5]})
        self.assertTrue(
            f"[{self.version}]\n" in self.changelog,
            msg=self.parameters.MSG_CLOUDRON_CHANGELOG_VERSION,
            expected=f"[{self.version}]",
            actual=headers[:5],
            abort_on_fail=False,
        )

    def bud_changelog_opens_with_the_newest_version(self):
        top = self.changelog.splitlines()[0]
        match = re.match(self.parameters.CLOUDRON_HEADER, top)
        newest = tuple(int(part) for part in match.group(1).split(".")) if match else None
        product = tuple(int(part) for part in self.version.split("."))
        self.print_variables({"top": top, "newest": newest, "product": product})
        self.assertRegex(
            top,
            self.parameters.CLOUDRON_HEADER,
            msg=self.parameters.MSG_CLOUDRON_CHANGELOG_TOP,
            abort_on_fail=False,
        )
        self.assertTrue(
            newest is not None and newest >= product,
            msg=self.parameters.MSG_CLOUDRON_CHANGELOG_NEWEST,
            expected=f">= {product}",
            actual=newest,
            abort_on_fail=False,
        )
