import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.database_model import Paper
from src.update import UpdateProcessor


class UpdateInvalidPolicyTests(unittest.TestCase):
    def _run_update(self, allow_invalid: bool):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        submit_path = root / 'submit.json'
        submit_path.write_text('{"papers": []}', encoding='utf-8')

        settings = {
            'paths': {
                'database': str(root / 'core.csv'),
                'complete_list_database': str(root / 'complete.csv'),
                'update_json': str(submit_path),
                'backup_dir': str(root / 'backups'),
            },
            'database': {
                'default_contributor': 'anonymous',
                'remove_added_paper_in_template': 'false',
                'conflict_marker': '',
                'allow_invalid_entries_on_update': 'true' if allow_invalid else 'false',
            },
            'ai': {'enable_ai_generation': 'false', 'ai_generate_mark': '[AI generated]'},
        }
        config = SimpleNamespace(project_root=root, settings=settings)
        paper = Paper(title='Invalid Date Paper', date='not-a-date', invalid_fields='date')
        update_utils = MagicMock()
        update_utils.read_data.return_value = (True, [paper])

        core_manager = MagicMock()
        core_manager.database_path = str(root / 'core.csv')
        core_manager.add_papers.side_effect = lambda papers, _mode: (list(papers), [], [])
        complete_manager = MagicMock()
        complete_manager.database_path = str(root / 'complete.csv')
        complete_manager.add_papers.side_effect = lambda papers, _mode: (list(papers), [], [])

        with (
            patch('src.update.get_config_instance', return_value=config),
            patch('src.update.get_update_file_utils', return_value=update_utils),
            patch('src.update.DatabaseManager', side_effect=[core_manager, complete_manager]),
            patch.object(Paper, 'validate_paper_fields', return_value=(False, ['日期格式无效'], ['date'])),
        ):
            result = UpdateProcessor().process_updates()

        return result, core_manager, complete_manager, paper

    def test_invalid_entry_is_written_with_warning_when_enabled(self):
        result, core_manager, complete_manager, paper = self._run_update(True)

        self.assertEqual(core_manager.add_papers.call_args.args[0], [paper])
        self.assertEqual(complete_manager.add_papers.call_args.args[0], [paper])
        self.assertFalse(result['errors'])
        self.assertTrue(any('仅警告' in message for message in result['invalid_msg']))

    def test_invalid_entry_is_skipped_when_disabled(self):
        result, core_manager, complete_manager, _paper = self._run_update(False)

        complete_manager.add_papers.assert_not_called()
        core_manager.add_papers.assert_called_once_with([], 'mark')
        self.assertTrue(any('验证失败' in message for message in result['errors']))


if __name__ == '__main__':
    unittest.main()
