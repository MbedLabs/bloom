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
        insert = self.bloom.bloom_insert_link
        self.before = self.bloom.bloom_run_alembic("upgrade", self.parameters.LINK_BEFORE)
        project = self.bloom.bloom_seed_requirements(
            self.parameters.LINK_PREFIX, self.parameters.LINK_REQ_IDS
        )
        self.old_link = insert(
            project, *self.parameters.LINK_FORBIDDEN, self.parameters.LINK_OLD_ENDS
        ).id
        self.bloom.bloom_insert_legacy_requirement_link()
        self.upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.validated_after_upgrade = self.bloom.bloom_link_constraint_validated()
        self.kept_link = self.bloom.bloom_first_link_id()
        self.rejected = [
            insert(project, *triple, self.parameters.LINK_NEW_ENDS, keep=False).error
            for triple in self.parameters.LINK_REJECTED
        ]
        self.accepted = [
            insert(project, *triple, self.parameters.LINK_NEW_ENDS, keep=False).id
            for triple in self.parameters.LINK_ACCEPTED
        ]
        self.table_triples = self.bloom.bloom_read_allowed_link_triples()
        self.code_triples = self.bloom.bloom_code_link_triples()
        self.refused_check = self.bloom.bloom_check_link_rules()
        self.validated_after_refusal = self.bloom.bloom_link_constraint_validated()
        self.bloom.bloom_set_link_role(self.old_link, self.parameters.LINK_CORRECTED_ROLE)
        self.passed_check = self.bloom.bloom_check_link_rules()
        self.validated_after_pass = self.bloom.bloom_link_constraint_validated()
        self.link_counts = self.bloom.bloom_count_links()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    LinkRulesEnforcementTest().run()
