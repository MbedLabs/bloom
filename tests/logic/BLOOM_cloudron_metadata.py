"""
* @file     ${tests/logic/BLOOM_cloudron_metadata.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The Cloudron package names the product and carries the product's release.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the manifest, description, version catalog and changelog.
"""

from tests.logic.cloudron_metadata import CloudronMetadataBase


class CloudronMetadataTest(CloudronMetadataBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_version = self.bloom.bloom_project_version()
        self.tc_manifest = self.bloom.bloom_read_repo_json(self.parameters.CLOUDRON_MANIFEST)
        self.tc_description = self.bloom.bloom_read_repo_text(self.parameters.CLOUDRON_DESCRIPTION)
        self.tc_catalog = self.bloom.bloom_read_repo_json(self.parameters.CLOUDRON_CATALOG)
        self.tc_changelog = self.bloom.bloom_read_repo_text(self.parameters.CLOUDRON_CHANGELOG)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CloudronMetadataTest().run()
