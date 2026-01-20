import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.convert import ReadmeGenerator

class DummyPaper:
    pass


def test_newlines_converted_to_br():
    rg = ReadmeGenerator.__new__(ReadmeGenerator)

    class DummyConfig:
        def get_tag_field(self, name, key):
            return name

    rg.config = DummyConfig()

    p = DummyPaper()
    p.summary_motivation = "line1\nline2"
    p.summary_innovation = ""
    p.summary_method = ""
    p.summary_conclusion = ""
    p.summary_limitation = ""
    p.notes = "note1\nnote2"

    html = rg._generate_summary_cell(p)

    # ensure newlines in summary and notes were converted to <br>
    assert "line1<br>line2" in html
    assert "note1<br>note2" in html
    # ensure there are no raw newline characters in the returned html
    assert "\n" not in html
