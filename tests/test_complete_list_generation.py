import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.convert import ReadmeGenerator


class CompleteListGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.database_path = self.root / "complete.json"
        self.output_path = self.root / "COMPLETE_LIST.md"
        self.metadata_path = self.root / "paper_metadata.json"

        self.generator = ReadmeGenerator()
        self.generator.complete_list_database_path = str(self.database_path)
        self.generator.complete_list_output_path = str(self.output_path)
        self.generator.paper_metadata_path = str(self.metadata_path)
        self.metadata_path.write_text(
            json.dumps(
                {
                    "paper_title": "Sample Paper",
                    "authors": "Alice; Bob",
                    "affiliations": "Sample University",
                    "venue": "ACL",
                    "year": "2026",
                    "paper_url": "https://example.com/sample",
                    "bibtex_type": "article",
                    "bibtex_key": "sample2026",
                    "bibtex_author": "Alice and Bob",
                    "bibtex_note": "Preprint",
                    "repository_url": "https://github.com/example/repo",
                }
            ),
            encoding="utf-8",
        )

    def _write_papers(self, papers):
        self.database_path.write_text(
            json.dumps({"papers": papers}, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_generates_compact_rows_from_independent_database(self):
        self._write_papers(
            [
                {
                    "title": "Older Paper",
                    "authors": "Author Must Not Appear",
                    "date": "2024-01-01",
                    "conference": "Venue A",
                    "paper_url": "https://example.com/paper",
                    "project_url": "https://github.com/example/project",
                    "doi": "10.1000/older",
                    "summary_motivation": "Summary Must Not Appear",
                },
                {
                    "title": "Newest | Hidden Detailed Entry",
                    "date": "2025-01-01",
                    "conference": "Venue | B",
                    "paper_url": "https://example.com/newest",
                    "show_in_readme": False,
                },
            ]
        )

        content = self.generator.generate_complete_list_content()

        self.assertIn("This compact index contains 2 papers", content)
        self.assertIn("Newest \\| Hidden Detailed Entry", content)
        self.assertIn("Venue \\| B", content)
        self.assertIn("[Paper](https://example.com/paper)", content)
        self.assertIn("[Project](https://github.com/example/project)", content)
        self.assertIn("[DOI](https://doi.org/10.1000/older)", content)
        self.assertNotIn("Author Must Not Appear", content)
        self.assertNotIn("Summary Must Not Appear", content)
        self.assertLess(content.index("Newest"), content.index("Older Paper"))

    def test_preserves_all_titled_database_rows(self):
        self._write_papers(
            [
                {"title": "Canonical", "doi": "10.1000/same"},
                {"title": "Canonical", "doi": "10.1000/other"},
                {"title": "Different title", "doi": "10.1000/same"},
                {"title": "Conflict", "conflict_marker": True},
                {"title": ""},
            ]
        )

        content = self.generator.generate_complete_list_content()

        self.assertIn("This compact index contains 4 papers", content)
        self.assertEqual(content.count("Canonical"), 2)
        self.assertIn("Different title", content)
        self.assertIn("Conflict", content)

    def test_writes_output_and_reports_missing_database(self):
        self._write_papers([])
        self.assertTrue(self.generator.update_complete_list_file())
        self.assertTrue(self.output_path.exists())

        self.generator.complete_list_database_path = str(self.root / "missing.json")
        self.assertEqual(self.generator.generate_complete_list_content(), "")
        self.assertFalse(self.generator.update_complete_list_file())

    def test_normal_readme_update_also_updates_complete_list(self):
        readme_path = self.root / "README.md"
        readme_path.write_text(
            "<!-- PAPER_INTRO_START -->\nold intro\n<!-- PAPER_INTRO_END -->\n"
            "<!-- PAPER_CITATION_TOP_START -->\nold top citation\n<!-- PAPER_CITATION_TOP_END -->\n"
            "## Full paper list (old)\nold table\n=====List End====="
            "\n<!-- PAPER_CITATION_BOTTOM_START -->\nold bottom citation\n"
            "<!-- PAPER_CITATION_BOTTOM_END -->\n",
            encoding="utf-8",
        )
        self.generator.config = SimpleNamespace(project_root=self.root)

        with (
            patch.object(self.generator, "generate_readme_tables", return_value="new table"),
            patch.object(self.generator, "_generate_quick_links", return_value="quick links"),
            patch.object(self.generator, "_load_display_papers", return_value=(True, [])),
            patch.object(self.generator, "update_complete_list_file", return_value=True) as update_complete,
        ):
            self.assertTrue(self.generator.update_readme_file())

        update_complete.assert_called_once_with()
        updated = readme_path.read_text(encoding="utf-8")
        self.assertIn("## Full paper list (0 papers)", updated)
        self.assertIn("quick links", updated)
        self.assertIn("new table", updated)
        self.assertIn("[Sample Paper](https://example.com/sample)", updated)
        self.assertEqual(updated.count("@article{sample2026,"), 2)
        self.assertNotIn("old intro", updated)
        self.assertNotIn("old top citation", updated)
        self.assertNotIn("old bottom citation", updated)

    def test_readme_update_fails_safely_when_metadata_marker_is_missing(self):
        readme_path = self.root / "README.md"
        original = "## Full paper list (old)\nold table\n=====List End=====\n"
        readme_path.write_text(original, encoding="utf-8")
        self.generator.config = SimpleNamespace(project_root=self.root)

        with (
            patch.object(self.generator, "generate_readme_tables", return_value="new table"),
            patch.object(self.generator, "_generate_quick_links", return_value="quick links"),
            patch.object(self.generator, "_load_display_papers", return_value=(True, [])),
        ):
            self.assertFalse(self.generator.update_readme_file())

        self.assertEqual(readme_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
