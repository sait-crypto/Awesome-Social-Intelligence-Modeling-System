"""Fail safely when an automated paper update removes existing database identities."""

import argparse
import csv
import re
import sys
from pathlib import Path


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _identity(row: dict[str, str]) -> tuple[str, str] | None:
    doi = _normalize(row.get("doi", ""))
    if doi:
        return "doi", doi
    title = _normalize(row.get("title", ""))
    if title:
        return "title", title
    return None


def _read_database(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Database has no header: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"Database has no paper rows: {path}")
    return list(reader.fieldnames), rows


def verify_database(before_path: Path, after_path: Path) -> None:
    before_header, before_rows = _read_database(before_path)
    after_header, after_rows = _read_database(after_path)

    if before_header != after_header:
        raise ValueError(f"Database header changed unexpectedly: {after_path}")
    if len(after_rows) < len(before_rows):
        raise ValueError(
            f"Database row count decreased from {len(before_rows)} to {len(after_rows)}: {after_path}"
        )

    before_identities = {_identity(row) for row in before_rows}
    after_identities = {_identity(row) for row in after_rows}
    before_identities.discard(None)
    after_identities.discard(None)
    missing = sorted(before_identities - after_identities)
    if missing:
        preview = ", ".join(f"{kind}:{value}" for kind, value in missing[:5])
        raise ValueError(
            f"Automated update removed {len(missing)} existing paper identities from {after_path}: {preview}"
        )

    print(
        f"Database integrity passed: {after_path} "
        f"({len(before_rows)} -> {len(after_rows)} rows; no existing identities removed)."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", action="append", required=True, type=Path)
    parser.add_argument("--after", action="append", required=True, type=Path)
    args = parser.parse_args()

    if len(args.before) != len(args.after):
        parser.error("--before and --after must be supplied the same number of times")

    try:
        for before_path, after_path in zip(args.before, args.after):
            verify_database(before_path, after_path)
    except (OSError, ValueError) as error:
        print(f"Database integrity check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
