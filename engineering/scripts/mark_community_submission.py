"""Mark pull-request submission records with explicit community provenance."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PREFIX = "community:"


def community_value(value: object, submitter: str) -> str:
    label = " ".join(str(value or "").split()).strip()
    if label.casefold().startswith(PREFIX):
        label = label[len(PREFIX) :].strip()
    if not label:
        label = f"@{submitter.lstrip('@').strip()}" if submitter.strip() else "unknown"
    return f"{PREFIX}{label}"


def mark_json(path: Path, submitter: str) -> int:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and isinstance(data.get("papers"), list):
        papers = data["papers"]
    elif isinstance(data, list):
        papers = data
    elif isinstance(data, dict):
        papers = [data]
    else:
        raise ValueError(f"Unsupported JSON submission structure: {path}")

    changed = 0
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        marked = community_value(paper.get("contributor"), submitter)
        if paper.get("contributor") != marked:
            paper["contributor"] = marked
            changed += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def mark_csv(path: Path, submitter: str) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        raise ValueError(f"CSV submission must contain two header rows: {path}")
    try:
        contributor_index = rows[1].index("contributor")
    except ValueError as error:
        raise ValueError(f"CSV submission has no contributor field: {path}") from error

    changed = 0
    for row in rows[2:]:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) <= contributor_index:
            row.extend([""] * (contributor_index + 1 - len(row)))
        marked = community_value(row[contributor_index], submitter)
        if row[contributor_index] != marked:
            row[contributor_index] = marked
            changed += 1

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(rows)
    return changed


def mark_file(path: Path, submitter: str) -> int:
    if path.suffix.casefold() == ".json":
        return mark_json(path, submitter)
    if path.suffix.casefold() == ".csv":
        return mark_csv(path, submitter)
    raise ValueError(f"Unsupported submission file type: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--submitter", required=True)
    args = parser.parse_args()

    existing = [path for path in args.paths if path.is_file()]
    if not existing:
        raise FileNotFoundError("No submission file was found to mark.")
    changed = sum(mark_file(path, args.submitter) for path in existing)
    print(f"Community provenance normalized in {len(existing)} file(s); {changed} record(s) changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
