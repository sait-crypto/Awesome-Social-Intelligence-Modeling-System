import csv
import tempfile
import unittest
from pathlib import Path

from scripts.verify_database_integrity import verify_database


HEADER = ["doi", "title", "authors"]


def write_database(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


class DatabaseIntegrityTests(unittest.TestCase):
    def test_allows_reordering_and_addition(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            before = root / "before.csv"
            after = root / "after.csv"
            first = {"doi": "10.1/alpha", "title": "Alpha", "authors": "A"}
            second = {"doi": "", "title": "Title Only", "authors": "B"}
            added = {"doi": "10.1/new", "title": "New", "authors": "C"}
            write_database(before, [first, second])
            write_database(after, [second, added, first])

            verify_database(before, after)

    def test_rejects_removed_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            before = root / "before.csv"
            after = root / "after.csv"
            write_database(before, [{"doi": "10.1/alpha", "title": "Alpha", "authors": "A"}])
            write_database(after, [{"doi": "10.1/beta", "title": "Beta", "authors": "B"}])

            with self.assertRaisesRegex(ValueError, "removed 1 existing paper identities"):
                verify_database(before, after)


if __name__ == "__main__":
    unittest.main()
