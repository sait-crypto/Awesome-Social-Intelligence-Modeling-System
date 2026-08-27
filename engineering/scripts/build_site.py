"""Build the static survey website from the repository's canonical data.

The website deliberately has no independent paper database.  Every build reads
the same survey CSV, taxonomy, and paper metadata used by the README generator,
then emits a self-contained directory suitable for GitHub Pages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SITE_SOURCE = PROJECT_ROOT / "site"
SURVEY_DATABASE = PROJECT_ROOT / "engineering" / "paper_database_for_survey.csv"
COMPLETE_DATABASE = PROJECT_ROOT / "engineering" / "paper_database_complete_list.csv"
CATEGORY_CONFIG = PROJECT_ROOT / "engineering" / "config" / "categories_config.py"
PAPER_METADATA = PROJECT_ROOT / "engineering" / "config" / "paper_metadata.json"

COMMUNITY_CONTRIBUTOR_PREFIX = "community:"
ANALOGY_SUMMARY_LIMIT = 180
ABSTRACT_EXCERPT_LIMIT = 360

COPIED_IMAGES = {
    PROJECT_ROOT / "engineering" / "assets" / "social-intelligence-modeling-overview.png": "social-intelligence-modeling-overview.png",
    PROJECT_ROOT / "engineering" / "assets" / "category_architecture.png": "category-architecture.png",
    PROJECT_ROOT / "community" / "wechat-group-qr.jpg": "wechat-group-qr.jpg",
}


def _load_categories_config() -> dict[str, Any]:
    namespace: dict[str, Any] = {"__name__": "site_categories_config"}
    source = CATEGORY_CONFIG.read_text(encoding="utf-8")
    exec(compile(source, str(CATEGORY_CONFIG), "exec"), namespace)
    return namespace["CATEGORIES_CONFIG"]


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read the repository's two-header-row CSV format."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        raise ValueError(f"Survey database is missing its two header rows: {path}")

    field_names = [value.strip() for value in rows[1]]
    records: list[dict[str, str]] = []
    for values in rows[2:]:
        if not any(str(value).strip() for value in values):
            continue
        padded = list(values) + [""] * max(0, len(field_names) - len(values))
        records.append({name: padded[index] for index, name in enumerate(field_names) if name})
    return records


def _is_truthy(value: Any, *, default: bool = False) -> bool:
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "y", "on"}


def _split_pipe(value: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in str(value or "").replace("；", "|").replace(";", "|").split("|"):
        cleaned = " ".join(item.split()).strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _compact_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _clean_analogy_summary(value: Any) -> str:
    text = str(value or "")
    text = re.split(r"(?:\\?\[翻译\]|【翻译】)", text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"\\?\[\s*AI\s+generated\s*\]", "", text, flags=re.I)
    return _compact_text(text, ANALOGY_SUMMARY_LIMIT)


def _community_contributor_label(value: Any) -> str:
    contributor = _compact_text(value, 120)
    if not contributor.casefold().startswith(COMMUNITY_CONTRIBUTOR_PREFIX):
        return ""
    return contributor[len(COMMUNITY_CONTRIBUTOR_PREFIX) :].strip() or "Community submitter"


def _extract_year(value: Any) -> int | None:
    match = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return int(match.group(0)) if match else None


def _paper_id(row: dict[str, str]) -> str:
    uid = str(row.get("uid") or "").strip()
    if uid:
        return uid
    identity = f"{row.get('doi', '')}|{row.get('title', '')}".casefold().encode("utf-8")
    return hashlib.sha1(identity).hexdigest()[:12]


def _doi_url(value: Any) -> str:
    doi = str(value or "").strip()
    if not doi:
        return ""
    if re.match(r"^https?://", doi, flags=re.I):
        return doi if re.match(r"^https?://(?:dx\.)?doi\.org/", doi, flags=re.I) else ""
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.I)
    return f"https://doi.org/{doi}" if doi else ""


def _normalize_categories(
    raw_value: Any,
    aliases: dict[str, str],
    active_by_casefold: dict[str, str],
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for category in _split_pipe(raw_value):
        key = category.casefold()
        mapped = aliases.get(key, category)
        canonical = active_by_casefold.get(mapped.casefold(), mapped)
        canonical_key = canonical.casefold()
        if canonical_key not in seen:
            normalized.append(canonical)
            seen.add(canonical_key)
    return normalized


def _category_depth(category_id: str, categories_by_id: dict[str, dict[str, Any]]) -> int:
    depth = 0
    seen = {category_id}
    parent = categories_by_id.get(category_id, {}).get("predecessor_category")
    while parent and parent not in seen:
        depth += 1
        seen.add(parent)
        parent = categories_by_id.get(parent, {}).get("predecessor_category")
    return depth


def _category_root(category_id: str, categories_by_id: dict[str, dict[str, Any]]) -> str:
    current = category_id
    seen = {current}
    parent = categories_by_id.get(current, {}).get("predecessor_category")
    while parent and parent not in seen:
        current = parent
        seen.add(parent)
        parent = categories_by_id.get(current, {}).get("predecessor_category")
    return current


def _sorted_counter(counter: Counter[Any]) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]).casefold()))
    ]


def build_site_data() -> dict[str, Any]:
    taxonomy = _load_categories_config()
    metadata = json.loads(PAPER_METADATA.read_text(encoding="utf-8"))
    category_records = [record for record in taxonomy["categories"] if record.get("enabled", True)]
    categories_by_id = {record["unique_name"]: record for record in category_records}
    active_by_casefold = {category_id.casefold(): category_id for category_id in categories_by_id}
    aliases = {
        str(rule.get("old_unique_name", "")).casefold(): str(rule.get("new_unique_name", ""))
        for rule in taxonomy.get("categories_change_list", [])
        if rule.get("old_unique_name") and rule.get("new_unique_name")
    }

    papers: list[dict[str, Any]] = []
    for row in _load_csv_rows(SURVEY_DATABASE):
        if not str(row.get("title") or "").strip():
            continue
        if not _is_truthy(row.get("show_in_readme"), default=True):
            continue
        if _is_truthy(row.get("conflict_marker")):
            continue

        categories = _normalize_categories(row.get("category"), aliases, active_by_casefold)
        roots = sorted(
            {_category_root(category, categories_by_id) for category in categories if category in categories_by_id},
            key=lambda value: categories_by_id.get(value, {}).get("order", 0),
        )
        contributor = _community_contributor_label(row.get("contributor"))
        is_community = bool(contributor)
        year = _extract_year(row.get("date"))
        analogy_summary = _clean_analogy_summary(row.get("analogy_summary"))

        papers.append(
            {
                "id": _paper_id(row),
                "title": _compact_text(row.get("title"), 500),
                "title_translation": _compact_text(row.get("title_translation"), 500),
                "authors": _compact_text(row.get("authors"), 1000),
                "date": _compact_text(row.get("date"), 40),
                "year": year,
                "conference": _compact_text(row.get("conference"), 160),
                "categories": categories,
                "stages": roots,
                "analogy_summary": analogy_summary,
                "abstract": _compact_text(row.get("abstract"), ABSTRACT_EXCERPT_LIMIT),
                "paper_url": str(row.get("paper_url") or "").strip(),
                "project_url": str(row.get("project_url") or "").strip(),
                "doi": _compact_text(row.get("doi"), 180),
                "contributor": contributor if is_community else "",
                "community_contribution": is_community,
            }
        )

    papers.sort(key=lambda paper: (paper.get("date") or "", paper["title"].casefold()), reverse=True)

    category_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    year_counts: Counter[int] = Counter()
    conference_counts: Counter[str] = Counter()
    for paper in papers:
        category_counts.update(set(paper["categories"]))
        stage_counts.update(set(paper["stages"]))
        if paper["year"]:
            year_counts[paper["year"]] += 1
        if paper["conference"]:
            conference_counts[paper["conference"]] += 1

    child_counts = Counter(
        record.get("predecessor_category") for record in category_records if record.get("predecessor_category")
    )
    categories = []
    for record in category_records:
        category_id = record["unique_name"]
        categories.append(
            {
                "id": category_id,
                "name": record.get("name_en") or record.get("name") or category_id,
                "parent": record.get("predecessor_category"),
                "description": _compact_text(record.get("description_en") or record.get("description"), 320),
                "order": record.get("order", 0),
                "depth": _category_depth(category_id, categories_by_id),
                "leaf": child_counts[category_id] == 0,
                "count": category_counts[category_id],
            }
        )
    categories.sort(key=lambda item: (item["depth"], item["order"], item["name"].casefold()))

    years = sorted(year_counts)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "meta": {
            "generated_at": generated_at,
            "source_revision": os.environ.get("GITHUB_SHA", "")[:12],
            "paper_title": metadata.get("paper_title", "Social Intelligence Modeling"),
            "authors": metadata.get("authors", ""),
            "affiliations": metadata.get("affiliations", ""),
            "paper_url": metadata.get("paper_url", ""),
            "repository_url": metadata.get("repository_url", ""),
            "year": metadata.get("year", ""),
        },
        "stats": {
            "paper_count": len(papers),
            "community_count": sum(1 for paper in papers if paper["community_contribution"]),
            "category_count": sum(1 for category in categories if category["count"] > 0),
            "conference_count": len(conference_counts),
            "year_start": years[0] if years else None,
            "year_end": years[-1] if years else None,
            "stages": _sorted_counter(stage_counts),
            "years": [{"name": year, "count": year_counts[year]} for year in sorted(year_counts)],
            "conferences": _sorted_counter(conference_counts),
            "categories": _sorted_counter(category_counts),
        },
        "categories": categories,
        "papers": papers,
    }


def build_complete_list_data() -> dict[str, Any]:
    """Export the repository's complete paper database as a compact web index."""
    papers: list[dict[str, Any]] = []
    for source_order, row in enumerate(_load_csv_rows(COMPLETE_DATABASE)):
        if not str(row.get("title") or "").strip():
            continue
        if not _is_truthy(row.get("show_in_readme"), default=True):
            continue

        contributor = _community_contributor_label(row.get("contributor"))
        papers.append(
            {
                "id": _paper_id(row),
                "source_order": source_order,
                "title": _compact_text(row.get("title"), 500),
                "authors": _compact_text(row.get("authors"), 1000),
                "date": _compact_text(row.get("date"), 40),
                "year": _extract_year(row.get("date")),
                "conference": _compact_text(row.get("conference"), 240),
                "paper_url": str(row.get("paper_url") or "").strip(),
                "project_url": str(row.get("project_url") or "").strip(),
                "doi": _compact_text(row.get("doi"), 180),
                "doi_url": _doi_url(row.get("doi")),
                "contributor": contributor,
                "community_contribution": bool(contributor),
            }
        )

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_revision": os.environ.get("GITHUB_SHA", "")[:12],
            "source": "engineering/paper_database_complete_list.csv",
        },
        "stats": {"paper_count": len(papers)},
        "papers": papers,
    }


def _assert_safe_output(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved in {PROJECT_ROOT.resolve(), SITE_SOURCE.resolve(), Path(resolved.anchor)}:
        raise ValueError(f"Refusing to replace unsafe site output directory: {resolved}")
    return resolved


def build_site(output_dir: Path) -> dict[str, Any]:
    output = _assert_safe_output(output_dir)
    if not SITE_SOURCE.is_dir():
        raise FileNotFoundError(f"Static site source directory does not exist: {SITE_SOURCE}")

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SITE_SOURCE, output)

    data = build_site_data()
    complete_list_data = build_complete_list_data()
    data["stats"]["total_paper_count"] = complete_list_data["stats"]["paper_count"]
    data_dir = output / "assets" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "site-data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (data_dir / "complete-list-data.json").write_text(
        json.dumps(complete_list_data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    image_dir = output / "assets" / "img"
    image_dir.mkdir(parents=True, exist_ok=True)
    for source, destination_name in COPIED_IMAGES.items():
        if not source.is_file():
            raise FileNotFoundError(f"Required website image is missing: {source}")
        shutil.copy2(source, image_dir / destination_name)

    (output / ".nojekyll").write_text("", encoding="utf-8")
    required_files: Iterable[Path] = (
        output / "index.html",
        output / "complete-list.html",
        output / "assets" / "css" / "styles.css",
        output / "assets" / "css" / "forms.css",
        output / "assets" / "css" / "complete-list.css",
        output / "assets" / "css" / "image-slots.css",
        output / "assets" / "js" / "app.js",
        output / "assets" / "js" / "site-core.js",
        output / "assets" / "js" / "i18n.js",
        output / "assets" / "js" / "form-validation.js",
        output / "assets" / "js" / "image-slots.js",
        output / "assets" / "js" / "complete-list.js",
        data_dir / "image-slots.json",
        data_dir / "site-data.json",
        data_dir / "complete-list-data.json",
    )
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise RuntimeError("Website build is incomplete: " + ", ".join(missing))
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "site-dist",
        help="Directory that will contain the self-contained static site.",
    )
    args = parser.parse_args()
    data = build_site(args.output)
    print(
        "Built survey website with "
        f"{data['stats']['paper_count']} papers, "
        f"{data['stats']['category_count']} populated categories, and "
        f"{data['stats']['community_count']} community contributions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
