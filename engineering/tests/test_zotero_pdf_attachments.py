import os
import sqlite3
import tempfile
import unittest

from src.submit_logic import SubmitLogic


class ZoteroPdfAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.logic = SubmitLogic.__new__(SubmitLogic)
        self.logic.settings = {'zotero': {}}
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, 'zotero.sqlite')
        open(self.db_path, 'wb').close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_pdf(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as handle:
            handle.write(b'%PDF-1.4\n')

    def test_resolves_zotero_storage_attachment(self):
        pdf_path = os.path.join(self.temp_dir.name, 'storage', 'ATTKEY', 'paper.pdf')
        self._write_pdf(pdf_path)

        resolved, error = self.logic._resolve_zotero_attachment_path(
            self.db_path, 'ATTKEY', 'storage:paper.pdf'
        )

        self.assertEqual(resolved, os.path.normpath(pdf_path))
        self.assertEqual(error, '')

    def test_resolves_absolute_linked_attachment(self):
        pdf_path = os.path.join(self.temp_dir.name, 'linked.pdf')
        self._write_pdf(pdf_path)

        resolved, error = self.logic._resolve_zotero_attachment_path(
            self.db_path, 'ATTKEY', pdf_path
        )

        self.assertEqual(resolved, os.path.normpath(pdf_path))
        self.assertEqual(error, '')

    def test_resolves_relative_linked_attachment_from_configured_base(self):
        linked_base = os.path.join(self.temp_dir.name, 'linked-base')
        pdf_path = os.path.join(linked_base, 'folder', 'paper.pdf')
        self._write_pdf(pdf_path)
        self.logic.settings = {'zotero': {'linked_attachment_base_dir': linked_base}}

        resolved, error = self.logic._resolve_zotero_attachment_path(
            self.db_path, 'ATTKEY', 'attachments:folder/paper.pdf'
        )

        self.assertEqual(resolved, os.path.normpath(pdf_path))
        self.assertEqual(error, '')

    def test_query_returns_available_and_unavailable_pdf_separately(self):
        conn = sqlite3.connect(':memory:')
        conn.executescript(
            """
            CREATE TABLE items (itemID INTEGER PRIMARY KEY, key TEXT);
            CREATE TABLE itemAttachments (
                itemID INTEGER,
                parentItemID INTEGER,
                linkMode INTEGER,
                contentType TEXT,
                path TEXT
            );
            CREATE TABLE deletedItems (itemID INTEGER);
            INSERT INTO items VALUES (2, 'GOODKEY');
            INSERT INTO items VALUES (3, 'MISSINGKEY');
            INSERT INTO itemAttachments VALUES (2, 1, 1, 'application/pdf', 'storage:good.pdf');
            INSERT INTO itemAttachments VALUES (3, 1, 1, 'application/pdf', 'storage:missing.pdf');
            """
        )
        pdf_path = os.path.join(self.temp_dir.name, 'storage', 'GOODKEY', 'good.pdf')
        self._write_pdf(pdf_path)

        available, unavailable = self.logic._query_zotero_pdf_attachments(conn, 1, self.db_path)

        self.assertEqual([item['key'] for item in available], ['GOODKEY'])
        self.assertEqual([item['key'] for item in unavailable], ['MISSINGKEY'])
        self.assertEqual(available[0]['path'], os.path.normpath(pdf_path))


if __name__ == '__main__':
    unittest.main()
