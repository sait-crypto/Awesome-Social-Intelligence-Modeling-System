import unittest
from unittest.mock import MagicMock

from src.core.database_model import Paper
from src.submit_logic import SubmitLogic


class ZoteroBuildModeTests(unittest.TestCase):
    def setUp(self):
        self.logic = SubmitLogic.__new__(SubmitLogic)
        self.logic.papers = []
        self.logic.settings = {'database': {'max_categories_per_paper': '4'}}
        self.logic.config = MagicMock()
        self.logic.config.get_system_tags.return_value = [
            {'variable': 'uid'},
            {'variable': 'submission_time'},
            {'variable': 'invalid_fields'},
            {'variable': 'is_placeholder'},
            {'variable': 'zotero_item_ref'},
        ]
        self.logic.config.get_active_categories.return_value = [
            {'unique_name': 'Hierarchy A', 'name': 'A', 'order': 1},
            {'unique_name': 'Hierarchy B', 'name': 'B', 'order': 2},
        ]
        self.logic.update_utils = MagicMock()
        self.logic.update_utils.normalize_category_value.side_effect = lambda value, _config: value

    def test_reuses_same_metadata_and_only_appends_hierarchy_category(self):
        existing = Paper(
            uid='existing-id',
            doi='10.1000/build',
            title='Build Paper',
            authors='Alice',
            category='Hierarchy A',
            citation_key='old-key',
            summary_motivation='Existing summary',
            analogy_summary='Existing analogy',
            contributor='someone',
            related_papers='related-existing',
            pipeline_image='figures/existing.png',
            paper_file='assets/existing.pdf',
            zotero_item_ref='1:OLDREF',
        )
        source = Paper(
            uid='source-id',
            doi='10.1000/build',
            title='Build Paper',
            authors='Alice',
            category='Zotero Tag',
            citation_key='new-key',
            summary_motivation='New summary',
            analogy_summary='New analogy',
            contributor='another person',
            related_papers='related-source',
            pipeline_image='figures/source.png',
            paper_file='assets/source.pdf',
            zotero_item_ref='1:NEWREF',
        )
        self.logic.papers = [existing]

        result = self.logic.add_zotero_papers_in_build_mode([source], 'Hierarchy B')

        self.assertEqual(len(self.logic.papers), 1)
        self.assertEqual(existing.category, 'Hierarchy A|Hierarchy B')
        self.assertEqual(existing.uid, 'existing-id')
        self.assertEqual(existing.pipeline_image, 'figures/existing.png')
        self.assertEqual(existing.paper_file, 'assets/existing.pdf')
        self.assertEqual(existing.zotero_item_ref, '1:OLDREF')
        self.assertEqual(existing.contributor, 'someone')
        self.assertEqual(existing.summary_motivation, 'Existing summary')
        self.assertEqual(result['categorized'], 1)
        self.assertEqual(result['indices'], [0])

    def test_different_paper_metadata_creates_entry_with_hierarchy_category(self):
        self.logic.papers = [Paper(doi='10.1000/build', title='Build Paper', authors='Alice')]
        source = Paper(
            doi='10.1000/build',
            title='Build Paper',
            authors='Bob',
            category='Zotero Tag',
        )

        result = self.logic.add_zotero_papers_in_build_mode([source], 'Hierarchy B')

        self.assertEqual(len(self.logic.papers), 2)
        self.assertEqual(source.category, 'Hierarchy B')
        self.assertEqual(source.contributor, 'me')
        self.assertTrue(source.uid)
        self.assertEqual(result['created'], 1)
        self.assertEqual(result['indices'], [1])

    def test_fill_override_ignores_zotero_category_and_appends_hierarchy(self):
        target = Paper(title='Build Paper', category='Hierarchy A')
        source = Paper(
            title='Build Paper',
            category='Zotero Tag',
            authors='Alice',
            contributor='Zotero Person',
        )
        self.logic.papers = [target]

        conflicts, updates = self.logic.get_zotero_fill_updates(
            source,
            0,
            category_override='Hierarchy B',
        )

        self.assertNotIn('category', conflicts)
        self.assertIn(('authors', 'Alice'), updates)
        self.assertIn(('category', 'Hierarchy A|Hierarchy B'), updates)
        self.assertIn(('contributor', 'me'), updates)
        self.assertNotIn(('contributor', 'Zotero Person'), updates)
        self.assertNotIn(('category', 'Zotero Tag'), updates)


if __name__ == '__main__':
    unittest.main()
