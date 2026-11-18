"""
* @file     ${tests/logic/reqif_import.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the ReqIF parser and the ReqIF import.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the ReqIF parser and import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ReqifImportBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_every_object_is_parsed(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        self.assertEqual(
            set(parsed.objects),
            {"OBJ-1", "OBJ-2"},
            msg=self.parameters.MSG_RQI_OBJECTS,
            abort_on_fail=False,
        )

    def bud_the_title_comes_from_the_chapter_name(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        self.assertEqual(
            (
                self.bloom.bloom_reqif_attribute(parsed.objects["OBJ-1"], "title"),
                self.bloom.bloom_reqif_attribute(parsed.objects["OBJ-2"], "title"),
            ),
            ("System Requirements", "Login"),
            msg=self.parameters.MSG_RQI_TITLES,
            abort_on_fail=False,
        )

    def bud_the_body_is_kept_as_html_and_plain_text(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        login = parsed.objects["OBJ-2"]
        html = self.bloom.bloom_reqif_html(login) or ""
        self.print_variables({"html": html})
        self.assertEqual(
            (
                "<b>shall</b>" in html,
                "allow login" in html,
                self.bloom.bloom_reqif_attribute(login, "text"),
            ),
            (True, True, "The system shall allow login."),
            msg=self.parameters.MSG_RQI_BODY,
            abort_on_fail=False,
        )

    def bud_an_enumeration_reads_as_its_long_name(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        self.assertEqual(
            parsed.objects["OBJ-2"].attributes.get("priority"),
            "High",
            msg=self.parameters.MSG_RQI_ENUM,
            abort_on_fail=False,
        )

    def bud_the_foreign_id_is_read(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        self.assertEqual(
            self.bloom.bloom_reqif_attribute(parsed.objects["OBJ-2"], "foreign id"),
            "PRJ-042",
            msg=self.parameters.MSG_RQI_FOREIGN_ID,
            abort_on_fail=False,
        )

    def bud_objects_follow_the_specification_order(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        self.assertEqual(
            parsed.ordered_object_refs(),
            ["OBJ-1", "OBJ-2"],
            msg=self.parameters.MSG_RQI_ORDER,
            abort_on_fail=False,
        )

    def bud_the_relation_is_parsed_with_its_type_name(self):
        parsed, _ = self.bloom.bloom_parse_reqif(self.parameters.REQIF_SAMPLE)
        self.assertEqual(
            [
                (relation.source_ref, relation.target_ref, relation.type_name)
                for relation in parsed.relations
            ],
            [("OBJ-2", "OBJ-1", "Refines")],
            msg=self.parameters.MSG_RQI_RELATION,
            abort_on_fail=False,
        )

    def bud_a_reqifz_archive_is_opened(self):
        archive = self.bloom.bloom_reqif_archive([("export.reqif", self.parameters.REQIF_SAMPLE)])
        parsed, _ = self.bloom.bloom_parse_reqif(archive)
        self.assertEqual(
            set(parsed.objects),
            {"OBJ-1", "OBJ-2"},
            msg=self.parameters.MSG_RQI_ARCHIVE,
            abort_on_fail=False,
        )

    def bud_an_object_outside_the_hierarchy_is_kept(self):
        document = self.parameters.REQIF_SAMPLE.replace(*self.parameters.RQI_EXTRA_OBJECT)
        parsed, _ = self.bloom.bloom_parse_reqif(document)
        ordered = parsed.ordered_object_refs()
        self.assertEqual(
            ("OBJ-3" in ordered, len(ordered)),
            (True, 3),
            msg=self.parameters.MSG_RQI_OUTSIDE,
            abort_on_fail=False,
        )

    def bud_unreadable_documents_are_refused(self):
        for what, document in self.parameters.RQI_UNREADABLE:
            parsed, refusal = self.bloom.bloom_parse_reqif(document)
            self.assertEqual(
                (parsed, refusal is not None),
                (None, True),
                msg=self.parameters.MSG_RQI_UNREADABLE.format(what=what),
                abort_on_fail=False,
            )

    def bud_a_second_import_creates_nothing(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        self.bloom.bloom_add_user(values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE))
        project = self.bloom.bloom_create_project("PRJ")
        first, _ = self.bloom.bloom_try_import_reqif(project, values.REQIF_SAMPLE)
        self.assertEqual(
            (first.imported, first.links_created),
            (2, 1),
            msg=values.MSG_RQI_FIRST,
            abort_on_fail=False,
        )
        second, _ = self.bloom.bloom_try_import_reqif(project, values.REQIF_SAMPLE)
        self.assertEqual(
            (
                second.imported,
                second.skipped,
                second.links_created,
                len(self.bloom.bloom_requirement_rows(("id",), project)),
            ),
            (0, 2, 0, 2),
            msg=values.MSG_RQI_AGAIN,
            abort_on_fail=False,
        )

    def bud_a_missing_project_is_a_404(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        self.bloom.bloom_add_user(values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE))
        project = self.bloom.bloom_create_project("PRJ")
        _, refusal = self.bloom.bloom_try_import_reqif(999, values.REQIF_SAMPLE)
        self.assertEqual(
            refusal[0], values.STATUS_NOT_FOUND, msg=values.MSG_RQI_NO_PROJECT, abort_on_fail=False
        )

    def bud_an_upload_that_is_not_reqif_is_a_422(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        self.bloom.bloom_add_user(values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE))
        project = self.bloom.bloom_create_project("PRJ")
        _, refusal = self.bloom.bloom_try_import_reqif(project, b"not reqif")
        self.assertEqual(
            refusal[0],
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_RQI_NOT_REQIF,
            abort_on_fail=False,
        )

    def bud_relations_are_stored_as_links_of_their_role(self):
        for name, role in self.parameters.RQI_RELATION_ROLES:
            values = self.parameters
            self.bloom.bloom_new_database()
            self.bloom.bloom_add_user(
                values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE)
            )
            project = self.bloom.bloom_create_project("PRJ")
            document = values.REQIF_SAMPLE.replace(
                values.RQI_RELATION_NAME, f'LONG-NAME="{name}"'.encode()
            )
            result, _ = self.bloom.bloom_try_import_reqif(project, document)
            links = self.bloom.bloom_list_artefact_links()
            neighbors = (
                self.bloom.bloom_outgoing_requirement_neighbors(links[0].source_id, project)
                if links
                else None
            )
            self.assertEqual(
                (result.links_created, [link.role for link in links], neighbors),
                (1, [role], [(links[0].target_id, role)] if links else None),
                msg=values.MSG_RQI_ROLE.format(name=name, role=role),
                abort_on_fail=False,
            )

    def bud_an_unknown_relation_type_is_a_422(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        self.bloom.bloom_add_user(values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE))
        project = self.bloom.bloom_create_project("PRJ")
        document = values.REQIF_SAMPLE.replace(
            values.RQI_RELATION_NAME, b'LONG-NAME="Unknown Relation"'
        )
        _, refusal = self.bloom.bloom_try_import_reqif(project, document)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (
                refusal[0],
                "REL-1" in refusal[1],
                "Unknown Relation" in refusal[1],
                self.bloom.bloom_requirement_rows(("id",), project),
                self.bloom.bloom_list_artefact_links(),
            ),
            (values.STATUS_UNPROCESSABLE, True, True, [], []),
            msg=values.MSG_RQI_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_a_relation_with_a_removed_role_is_a_422(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        self.bloom.bloom_add_user(values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE))
        project = self.bloom.bloom_create_project("PRJ")
        _, refusal = self.bloom.bloom_try_import_reqif(
            project, values.REQIF_SAMPLE, without_link_rules=True
        )
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (
                refusal[0],
                "REL-1" in refusal[1],
                "Refines" in refusal[1],
                self.bloom.bloom_list_artefact_links(),
            ),
            (values.STATUS_UNPROCESSABLE, True, True, []),
            msg=values.MSG_RQI_REMOVED_ROLE,
            abort_on_fail=False,
        )

    def bud_a_legacy_link_is_kept_and_not_duplicated(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        self.bloom.bloom_add_user(values.TEXT_ADMIN, self.bloom.bloom_role(values.TEXT_ADMIN_ROLE))
        project = self.bloom.bloom_create_project("PRJ")
        parent, child = (
            self.bloom.bloom_add_sourced_requirement(project, *row)
            for row in values.RQI_LEGACY_ROWS
        )
        legacy = self.bloom.bloom_add_legacy_requirement_link(child, parent, "derived_from")
        document = values.REQIF_SAMPLE.replace(values.RQI_RELATION_NAME, b'LONG-NAME="Derives"')
        result, _ = self.bloom.bloom_try_import_reqif(project, document)
        self.assertEqual(
            (
                result.links_created,
                self.bloom.bloom_list_legacy_link_ids(),
                self.bloom.bloom_list_artefact_links(),
            ),
            (0, [legacy], []),
            msg=values.MSG_RQI_LEGACY,
            abort_on_fail=False,
        )
