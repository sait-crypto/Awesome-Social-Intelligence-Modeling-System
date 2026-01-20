import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.convert import ReadmeGenerator

class DummyPaper:
    pass


def test_summary_and_notes_present_and_order():
    rg = ReadmeGenerator.__new__(ReadmeGenerator)

    class DummyConfig:
        def get_tag_field(self, name, key):
            # return a readable display name
            return name

    rg.config = DummyConfig()

    p = DummyPaper()
    p.summary_motivation = "motivation text"
    p.summary_innovation = "innovation text"
    p.summary_method = "method text"
    p.summary_conclusion = "conclusion text"
    p.summary_limitation = "limitation text"
    p.notes = "these are notes"

    html = rg._generate_summary_cell(p)

    assert "**[summary]**" in html
    assert "**[notes]**" in html
    # notes should appear after summary
    assert html.find("**[summary]**") < html.find("**[notes]**")


def test_only_notes_shown():
    rg = ReadmeGenerator.__new__(ReadmeGenerator)

    class DummyConfig:
        def get_tag_field(self, name, key):
            return name

    rg.config = DummyConfig()

    p = DummyPaper()
    p.summary_motivation = ""
    p.summary_innovation = ""
    p.summary_method = ""
    p.summary_conclusion = ""
    p.summary_limitation = ""
    p.notes = "only notes here"

    html = rg._generate_summary_cell(p)
    assert "**[summary]**" not in html
    assert "**[notes]**" in html
