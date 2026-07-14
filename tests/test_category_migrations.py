import unittest

from config.categories_config import CATEGORIES_CONFIG, validate_categories_config
from src.convert import ReadmeGenerator


class CategoryMigrationTests(unittest.TestCase):
    REMOVED_CATEGORIES = {
        "Base Techniques",
        "Ethics and Safety",
        "Sarcasm Detection",
        "Humor Recognition",
        "Euphemism Recognition",
        "Metaphor Recognition",
        "Bragging Detection",
    }

    def setUp(self):
        self.generator = ReadmeGenerator()

    def test_category_config_and_migration_targets_are_valid(self):
        is_valid, errors = validate_categories_config()
        self.assertTrue(is_valid, "\n".join(errors))

        active = {
            category["unique_name"]
            for category in CATEGORIES_CONFIG["categories"]
            if category.get("enabled", True)
        }
        self.assertTrue(self.REMOVED_CATEGORIES.isdisjoint(active))
        self.assertIn("Micro-Level Pragmatic Expressions", active)

    def test_removed_categories_normalize_without_duplicates(self):
        value = "Base Techniques|Sarcasm Detection|Humor Recognition|Ethics and Safety"
        normalized = self.generator.update_utils.normalize_category_value(value, self.generator.config)
        self.assertEqual(normalized, "Other|Micro-Level Pragmatic Expressions")

    def test_database_has_no_unknown_categories_after_normalization(self):
        success, papers = self.generator._load_display_papers()
        self.assertTrue(success)
        self.assertEqual(len(papers), 195)

        active = {
            category["unique_name"]
            for category in CATEGORIES_CONFIG["categories"]
            if category.get("enabled", True)
        }
        unknown = set()
        for paper in papers:
            unknown.update(
                category
                for category in str(paper.category or "").split("|")
                if category
                if category not in active
            )
        self.assertEqual(unknown, set())

        grouped = self.generator._group_papers_by_category(papers)
        self.assertEqual(len(grouped["Micro-Level Pragmatic Expressions"]), 17)
        self.assertTrue(self.REMOVED_CATEGORIES.isdisjoint(grouped))


if __name__ == "__main__":
    unittest.main()
