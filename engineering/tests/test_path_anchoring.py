import importlib.util
import os
import unittest
from pathlib import Path


class PathAnchoringTests(unittest.TestCase):
    def test_review_tool_relative_config_is_anchored_to_its_app_directory(self):
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / 'AI_assistant_review_tools' / 'utils' / 'file_utils.py'
        spec = importlib.util.spec_from_file_location('review_tool_file_utils_for_test', module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        resolved = module.ConfigManager._resolve_app_path('config.ini', 'config.ini')

        self.assertEqual(
            resolved,
            os.path.normpath(str(repo_root / 'AI_assistant_review_tools' / 'config.ini')),
        )


if __name__ == '__main__':
    unittest.main()
