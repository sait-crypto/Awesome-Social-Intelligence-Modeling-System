import os
import unittest
from unittest.mock import MagicMock, patch

from src.submit_gui import PaperSubmissionGUI


class WindowsFileRevealTests(unittest.TestCase):
    def test_windows_shell_receives_normalized_absolute_file_path(self):
        gui = PaperSubmissionGUI.__new__(PaperSubmissionGUI)
        source_path = os.path.join('C:\\', 'folder with spaces', 'paper.pdf')
        gui._resolve_existing_path = lambda _path: source_path
        gui._reveal_windows_file = MagicMock()

        with (
            patch('src.submit_gui.sys.platform', 'win32'),
            patch('src.submit_gui.os.path.isfile', return_value=True),
        ):
            gui._reveal_in_file_manager('paper.pdf', select_file=True)

        expected_path = os.path.normpath(os.path.abspath(source_path))
        gui._reveal_windows_file.assert_called_once_with(expected_path)


if __name__ == '__main__':
    unittest.main()
