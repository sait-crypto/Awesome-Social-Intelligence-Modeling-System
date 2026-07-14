import unittest

from src.convert import ReadmeGenerator
from src.core.database_model import Paper


class ReadmeCompactionTests(unittest.TestCase):
    def setUp(self):
        self.generator = ReadmeGenerator()
        self.generator.enable_markdown = True

    def test_long_readme_fields_use_independent_limits_without_tooltips(self):
        self.generator.max_analogy_summary_length = 5
        self.generator.summary_field_limits = {
            'summary_motivation': 8,
            'summary_innovation': 9,
            'summary_method': 10,
            'summary_conclusion': 11,
            'summary_limitation': 12,
        }
        self.generator.max_notes_length = 6
        paper = Paper(
            title='Compact Paper',
            analogy_summary='123456789',
            summary_motivation='ABCDEFGHIJKLMN',
            summary_innovation='ABCDEFGHIJKLMN',
            summary_method='ABCDEFGHIJKLMN',
            summary_conclusion='ABCDEFGHIJKLMN',
            summary_limitation='ABCDEFGHIJKLMN',
            notes='123456789',
        )

        self.assertEqual(self.generator._generate_analogy_cell(paper), '1234…')
        summary = self.generator._generate_summary_cell(paper)
        self.assertIn('ABCDEFG…', summary)
        self.assertIn('ABCDEFGH…', summary)
        self.assertIn('ABCDEFGHI…', summary)
        self.assertIn('ABCDEFGHIJ…', summary)
        self.assertIn('ABCDEFGHIJK…', summary)
        self.assertIn('12345…', summary)
        self.assertNotIn('<summary title=', summary)
        self.assertIn('<summary>**[summary]**</summary>', summary)
        self.assertIn('<summary>**[notes]**</summary>', summary)

    def test_zero_limit_keeps_full_value(self):
        self.assertEqual(self.generator._truncate_field('unchanged', 0), 'unchanged')

    def test_duplicate_paper_is_a_single_table_reference_row(self):
        paper = Paper(
            doi='10.1000/example',
            title='A Multi-Category Paper',
            authors='Alice',
            category='One|Two',
        )

        full_row = self.generator._generate_paper_or_reference_row(paper)
        reference_row = self.generator._generate_paper_or_reference_row(paper)

        self.assertIn('<a id="paper-entry-', full_row)
        self.assertIn('[↪ A Multi-Category Paper](#paper-entry-', reference_row)
        self.assertIn('<sub>Full entry</sub>', reference_row)
        self.assertEqual(reference_row.count('|'), 5)
        self.assertEqual(reference_row.count('\n'), 1)
        self.assertNotIn('<details>', reference_row)

    def test_empty_category_is_rendered_as_uncategorized(self):
        paper = Paper(title='Needs Classification', category='')
        grouped = self.generator._group_papers_by_category([paper])

        self.assertEqual(grouped['Uncategorized'], [paper])
        count, _ = self.generator._get_category_paper_count_and_anchor(
            'Uncategorized', [paper]
        )
        self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()
