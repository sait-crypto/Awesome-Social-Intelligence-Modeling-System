import unittest

from config.categories_config import CATEGORIES_CONFIG, validate_categories_config
from src.convert import ReadmeGenerator


class CategoryMigrationTests(unittest.TestCase):
    PAPER_TAXONOMY_PARENT = {
        "Perception": None,
        "Content-Level Perception": "Perception",
        "Hate Speech Analysis": "Content-Level Perception",
        "Misinformation Analysis": "Content-Level Perception",
        "Machine-Generated Content Detection": "Content-Level Perception",
        "Sentiment Analysis": "Content-Level Perception",
        "Discourse and Pragmatic Analysis": "Content-Level Perception",
        "User-Level Perception": "Perception",
        "User Stance Detection": "User-Level Perception",
        "Malicious User Detection": "User-Level Perception",
        "Understanding": None,
        "Structural and Discourse Modeling": "Understanding",
        "Event Extraction": "Structural and Discourse Modeling",
        "Topic Modeling": "Structural and Discourse Modeling",
        "Network and Propagation Understanding": "Understanding",
        "Meme and Multimodal Understanding": "Network and Propagation Understanding",
        "Social Popularity Prediction": "Network and Propagation Understanding",
        "Information Diffusion Analysis": "Network and Propagation Understanding",
        "User-Level Understanding": "Understanding",
        "User Profiling": "User-Level Understanding",
        "Community Detection and Analysis": "User-Level Understanding",
        "Generation": None,
        "Social Content Generation": "Generation",
        "Comment Generation": "Social Content Generation",
        "Social Summarization": "Social Content Generation",
        "Socially-Aware Dialogue Generation": "Generation",
        "Personalized Dialogue Generation": "Socially-Aware Dialogue Generation",
        "Empathetic Dialogue Generation": "Socially-Aware Dialogue Generation",
        "Strategic and Persuasive Dialogue Generation": "Socially-Aware Dialogue Generation",
        "Social Intervention": "Generation",
        "Misinformation Generation": "Social Intervention",
        "Counter-Hate Speech Generation": "Social Intervention",
        "Evidence-Grounded Rumor Refutation": "Social Intervention",
        "Content Moderation and Detoxification": "Social Intervention",
        "Simulation": None,
        "Modeling Method": "Simulation",
        "Mechanistic Models": "Modeling Method",
        "Graph-Based Models": "Modeling Method",
        "LLM-Empowered Agent-Based Modeling": "Modeling Method",
        "Simulation Scale": "Simulation",
        "Micro-Level Social Simulation": "Simulation Scale",
        "Individual-Oriented Simulation": "Micro-Level Social Simulation",
        "Group-Oriented Simulation": "Micro-Level Social Simulation",
        "Macro-Level Social Simulation": "Simulation Scale",
        "Macro Social Alignment": "Macro-Level Social Simulation",
        "Macro Social Phenomena Analysis": "Macro-Level Social Simulation",
        "Application Domain": "Simulation",
        "Sociology and Social Media": "Application Domain",
        "Economy and Politics": "Application Domain",
        "Psychology, Games, and Narrative": "Application Domain",
        "Embodied Intelligence": "Application Domain",
    }

    def setUp(self):
        self.generator = ReadmeGenerator()
        self.by_unique = {
            category["unique_name"]: category
            for category in CATEGORIES_CONFIG["categories"]
            if category.get("enabled", True)
        }

    def test_category_config_matches_paper_taxonomy(self):
        is_valid, errors = validate_categories_config()
        self.assertTrue(is_valid, "\n".join(errors))

        academic_names = set(self.by_unique) - {"Uncategorized", "Other"}
        self.assertEqual(academic_names, set(self.PAPER_TAXONOMY_PARENT))
        for unique_name, expected_parent in self.PAPER_TAXONOMY_PARENT.items():
            self.assertEqual(
                self.by_unique[unique_name].get("predecessor_category"),
                expected_parent,
                unique_name,
            )

    def test_simulation_uses_exactly_three_dimensions(self):
        children = {
            category["unique_name"]
            for category in self.by_unique.values()
            if category.get("predecessor_category") == "Simulation"
        }
        self.assertEqual(children, {"Modeling Method", "Simulation Scale", "Application Domain"})

    def test_simulation_scale_uses_paper_subsections(self):
        micro_children = {
            category["unique_name"]
            for category in self.by_unique.values()
            if category.get("predecessor_category") == "Micro-Level Social Simulation"
        }
        macro_children = {
            category["unique_name"]
            for category in self.by_unique.values()
            if category.get("predecessor_category") == "Macro-Level Social Simulation"
        }
        self.assertEqual(
            micro_children,
            {"Individual-Oriented Simulation", "Group-Oriented Simulation"},
        )
        self.assertEqual(
            macro_children,
            {"Macro Social Alignment", "Macro Social Phenomena Analysis"},
        )

    def test_legacy_simulation_subject_categories_map_to_new_scale_leaves(self):
        normalized = self.generator.update_utils.normalize_category_value(
            "Individual-Oriented Social Simulation|Group-Oriented Social Simulation",
            self.generator.config,
        )
        self.assertEqual(
            normalized,
            "Individual-Oriented Simulation|Group-Oriented Simulation",
        )

    def test_legacy_categories_normalize_directly_without_duplicates(self):
        value = (
            "Perception and Classification|Sarcasm Detection|Micro-Level Pragmatic Expressions|"
            "Simulation and Deduction|Social Simulation for Economy"
        )
        normalized = self.generator.update_utils.normalize_category_value(value, self.generator.config)
        self.assertEqual(
            normalized,
            "Perception|Discourse and Pragmatic Analysis|Simulation|Economy and Politics",
        )

    def test_database_has_no_unknown_categories_after_normalization(self):
        success, papers = self.generator._load_display_papers()
        self.assertTrue(success)
        self.assertGreater(len(papers), 0)

        unknown = set()
        for paper in papers:
            unknown.update(
                category
                for category in str(paper.category or "").split("|")
                if category and category not in self.by_unique
            )
        self.assertEqual(unknown, set())


if __name__ == "__main__":
    unittest.main()
