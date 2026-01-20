import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.convert import ReadmeGenerator

class DummyPaper:
    pass


def test_title_hyphen_and_ellipsis_not_escaped():
    rg = ReadmeGenerator.__new__(ReadmeGenerator)

    class DummyConfig:
        def get_tag_field(self, name, key):
            return name

    rg.config = DummyConfig()
    rg.max_title_length = 300
    rg.max_authors_length = 200

    p = DummyPaper()
    p.title = "Event causality extraction via implicit cause-effect interactions"
    p.authors = "A. Author"
    p.date = "2025"
    p.paper_url = "https://example.com"
    p.conference = None
    p.project_url = None

    html = rg._generate_title_authors_cell(p)

    # hyphen should be present (not escaped as \-)
    assert "cause-effect" in html
    assert "\\-" not in html

    # and ellipsis should not be escaped if present
    p.title = "CAMEL: Capturing metaphorical alignment with context disentangling for multimodal emotion recognition..."
    html2 = rg._generate_title_authors_cell(p)
    assert "..." in html2
    assert "\\.\\.\\." not in html2
