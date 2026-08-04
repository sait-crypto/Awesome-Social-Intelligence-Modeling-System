import unittest
from unittest.mock import patch

from src.submit_gui import PaperSubmissionGUI


class UrlFieldTests(unittest.TestCase):
    def setUp(self):
        self.gui = PaperSubmissionGUI.__new__(PaperSubmissionGUI)

    @patch('src.submit_gui.messagebox')
    @patch('src.submit_gui.webbrowser.open', return_value=True)
    def test_opens_https_url_in_default_browser(self, browser_open, messagebox_mock):
        result = self.gui._open_url_in_browser('  https://example.com/paper?id=1  ')

        self.assertTrue(result)
        browser_open.assert_called_once_with('https://example.com/paper?id=1', new=2)
        messagebox_mock.showwarning.assert_not_called()
        messagebox_mock.showerror.assert_not_called()

    @patch('src.submit_gui.messagebox')
    @patch('src.submit_gui.webbrowser.open')
    def test_rejects_non_http_url(self, browser_open, messagebox_mock):
        result = self.gui._open_url_in_browser('javascript:alert(1)')

        self.assertFalse(result)
        browser_open.assert_not_called()
        messagebox_mock.showwarning.assert_called_once()

    @patch('src.submit_gui.messagebox')
    @patch('src.submit_gui.webbrowser.open')
    def test_rejects_url_without_host(self, browser_open, messagebox_mock):
        result = self.gui._open_url_in_browser('https:///missing-host')

        self.assertFalse(result)
        browser_open.assert_not_called()
        messagebox_mock.showwarning.assert_called_once()

    @patch('src.submit_gui.messagebox')
    @patch('src.submit_gui.webbrowser.open', return_value=False)
    def test_reports_browser_launch_failure(self, browser_open, messagebox_mock):
        result = self.gui._open_url_in_browser('http://localhost:8000')

        self.assertFalse(result)
        browser_open.assert_called_once_with('http://localhost:8000', new=2)
        messagebox_mock.showerror.assert_called_once()


if __name__ == '__main__':
    unittest.main()
