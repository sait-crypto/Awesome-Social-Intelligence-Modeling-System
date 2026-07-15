import unittest

from src.process_zotero_meta import ZoteroProcessor


class ZoteroNoteImportTests(unittest.TestCase):
    META = {
        'itemType': 'conferencePaper',
        'title': 'Zotero Paper',
        'notes': [
            {'note': '<p>Structured note</p>'},
            '<div>Plain note</div>',
        ],
    }

    def test_note_content_is_imported_when_enabled(self):
        papers = ZoteroProcessor(import_notes=True).process_meta_data(self.META)

        self.assertEqual(papers[0].notes, 'Structured note\nPlain note')

    def test_note_content_is_ignored_when_disabled(self):
        papers = ZoteroProcessor(import_notes=False).process_meta_data(self.META)

        self.assertEqual(papers[0].notes, '')


if __name__ == '__main__':
    unittest.main()
