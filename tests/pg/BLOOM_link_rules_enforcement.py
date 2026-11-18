"""
* @file     ${tests/pg/BLOOM_link_rules_enforcement.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The link rule migration keeps old rows, refuses new forbidden triples and validates once the rows are clean.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the upgrade on a new PostgreSQL database holding one forbidden link and one legacy requirement link.
"""

from tests.pg.link_rules_enforcement import LinkRulesEnforcementBase


class LinkRulesEnforcementTest(LinkRulesEnforcementBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.before = self.bloom.bloom_run_alembic("upgrade", self.parameters.LINK_BEFORE)
        self.project = self.bloom.bloom_seed_requirements(
            self.parameters.LINK_PREFIX, self.parameters.LINK_REQ_IDS
        )
        self.old_link = self.bloom.bloom_insert_link(
            self.project, *self.parameters.LINK_FORBIDDEN, self.parameters.LINK_OLD_ENDS
        ).id
        self.bloom.bloom_insert_legacy_requirement_link()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    LinkRulesEnforcementTest().run()
