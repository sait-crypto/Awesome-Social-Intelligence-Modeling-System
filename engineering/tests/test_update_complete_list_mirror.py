import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.database_model import Paper
from src.update import UpdateProcessor


class CompleteListMirrorTests(unittest.TestCase):
    def test_submission_is_mirrored_before_ai_then_written_to_core(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            submit_path = root / "submit.json"
            submit_path.write_text('{"papers": []}', encoding="utf-8")
            core_path = root / "core.csv"
            complete_path = root / "complete.csv"

            settings = {
                "paths": {
                    "database": str(core_path),
                    "complete_list_database": str(complete_path),
                    "update_json": str(submit_path),
                    "backup_dir": str(root / "backups"),
                },
                "database": {
                    "default_contributor": "anonymous",
                    "remove_added_paper_in_template": "false",
                    "conflict_marker": "",
                },
                "ai": {"enable_ai_generation": "true", "ai_generate_mark": "[AI generated]"},
            }
            config = SimpleNamespace(project_root=root, settings=settings)
            source_paper = Paper(title="Mirrored Paper")
            update_utils = MagicMock()
            update_utils.read_data.return_value = (True, [source_paper])

            events = []
            core_manager = MagicMock()
            core_manager.database_path = str(core_path)
            complete_manager = MagicMock()
            complete_manager.database_path = str(complete_path)

            def add_complete(papers, conflict_resolution):
                events.append(("complete", papers[0].summary_motivation))
                return papers, [], []

            def add_core(papers, conflict_resolution):
                events.append(("core", papers[0].summary_motivation))
                return papers, [], []

            complete_manager.add_papers.side_effect = add_complete
            core_manager.add_papers.side_effect = add_core

            class FakeAIGenerator:
                def is_available(self):
                    return True

                def batch_enhance_papers(self, papers):
                    events.append(("ai", papers[0].summary_motivation))
                    papers[0].summary_motivation = "[AI generated] enhanced"
                    return papers, True

            fake_ai_module = types.ModuleType("src.ai_generator")
            fake_ai_module.AIGenerator = FakeAIGenerator

            with (
                patch("src.update.get_config_instance", return_value=config),
                patch("src.update.get_update_file_utils", return_value=update_utils),
                patch("src.update.DatabaseManager", side_effect=[core_manager, complete_manager]),
                patch.object(Paper, "validate_paper_fields", return_value=(True, [], [])),
                patch.dict(sys.modules, {"src.ai_generator": fake_ai_module}),
            ):
                result = UpdateProcessor().process_updates()

            self.assertEqual(
                events,
                [
                    ("complete", ""),
                    ("ai", ""),
                    ("core", "[AI generated] enhanced"),
                ],
            )
            self.assertEqual(result["complete_list_new_papers"], 1)
            self.assertEqual(result["new_papers"], 1)
            self.assertEqual(result["ai_generated"], 1)
            update_utils.persist_ai_generated_to_update_files.assert_called_once()

    def test_database_only_mode_does_not_mirror_any_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = {
                "paths": {
                    "database": str(root / "core.csv"),
                    "complete_list_database": str(root / "complete.csv"),
                    "backup_dir": str(root / "backups"),
                },
                "database": {
                    "default_contributor": "anonymous",
                    "remove_added_paper_in_template": "false",
                    "conflict_marker": "",
                },
                "ai": {"enable_ai_generation": "false", "ai_generate_mark": "[AI generated]"},
            }
            config = SimpleNamespace(project_root=root, settings=settings)
            core_manager = MagicMock()
            core_manager.database_path = str(root / "core.csv")
            core_manager.add_papers.return_value = ([], [], [])
            complete_manager = MagicMock()
            complete_manager.database_path = str(root / "complete.csv")

            with (
                patch("src.update.get_config_instance", return_value=config),
                patch("src.update.get_update_file_utils", return_value=MagicMock()),
                patch("src.update.DatabaseManager", side_effect=[core_manager, complete_manager]),
            ):
                UpdateProcessor().process_updates(update_mode="database-only")

            complete_manager.add_papers.assert_not_called()
            core_manager.add_papers.assert_called_once_with([], "mark")


if __name__ == "__main__":
    unittest.main()
