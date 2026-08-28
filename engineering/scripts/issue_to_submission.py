"""Convert an approved GitHub paper-suggestion issue into submission JSON.

Issue content is treated strictly as data.  The script never evaluates fields,
expands shell syntax, downloads URLs, or writes outside the requested output.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATEGORY_CONFIG = PROJECT_ROOT / "engineering" / "config" / "categories_config.py"
ENGINEERING_ROOT = PROJECT_ROOT / "engineering"
sys.path.insert(0, str(ENGINEERING_ROOT))

from config import tag_config
from src.utils import generate_paper_uid

SECTION_TO_FIELD = {
    "paper title": "title",
    "doi": "doi",
    "paper url": "paper_url",
    "project url": "project_url",
    "authors": "authors",
    "publication date": "date",
    "venue": "conference",
    "categories": "category",
    "abstract": "abstract",
    "why it belongs in this survey": "rationale",
    "citation key": "citation_key",
    "translated title": "title_translation",
    "analogy summary": "analogy_summary",
    "motivation": "summary_motivation",
    "innovation": "summary_innovation",
    "method": "summary_method",
    "conclusion / contribution": "summary_conclusion",
    "limitations / future work": "summary_limitation",
    "citable paragraph": "summary_citable_paragraph",
    "related papers": "related_papers",
    "additional notes": "notes",
    "contributor": "contributor",
    "pipeline image": "pipeline_image",
    "paper file": "paper_file",
}

REQUIRED_FIELDS = ("title", "doi", "paper_url", "authors", "date", "category", "abstract")
EMPTY_RESPONSES = {"", "_no response_", "no response", "n/a", "none"}


def _load_active_categories() -> tuple[dict[str, str], dict[str, str]]:
    namespace: dict[str, Any] = {"__name__": "issue_categories_config"}
    source = CATEGORY_CONFIG.read_text(encoding="utf-8")
    exec(compile(source, str(CATEGORY_CONFIG), "exec"), namespace)
    config = namespace["CATEGORIES_CONFIG"]
    active = {
        record["unique_name"].casefold(): record["unique_name"]
        for record in config["categories"]
        if record.get("enabled", True)
    }
    aliases = {
        str(rule["old_unique_name"]).casefold(): str(rule["new_unique_name"])
        for rule in config.get("categories_change_list", [])
        if rule.get("old_unique_name") and rule.get("new_unique_name")
    }
    return active, aliases


def _clean_section(value: str) -> str:
    lines = value.strip().splitlines()
    while lines and lines[0].strip().startswith("<!--"):
        lines.pop(0)
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        lines = lines[1:-1]
    cleaned = "\n".join(lines).strip()
    return "" if cleaned.casefold() in EMPTY_RESPONSES else cleaned


def parse_issue_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in str(body or "").replace("\r\n", "\n").split("\n"):
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip().casefold()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    result: dict[str, str] = {}
    for heading, field in SECTION_TO_FIELD.items():
        result[field] = _clean_section("\n".join(sections.get(heading, [])))
    return result


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_doi(value: str) -> str:
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).strip()


def _normalize_categories(value: str) -> list[str]:
    active, aliases = _load_active_categories()
    raw_items = re.split(r"\s*[|;；]\s*", value)
    normalized: list[str] = []
    seen: set[str] = set()
    invalid: list[str] = []
    for raw in raw_items:
        category = " ".join(raw.split()).strip()
        if not category:
            continue
        mapped = aliases.get(category.casefold(), category)
        canonical = active.get(mapped.casefold())
        if canonical is None:
            invalid.append(category)
            continue
        if canonical.casefold() not in seen:
            normalized.append(canonical)
            seen.add(canonical.casefold())

    if invalid:
        raise ValueError("Unknown survey categories: " + ", ".join(invalid))
    if not normalized:
        raise ValueError("At least one valid survey category is required.")
    if len(normalized) > 4:
        raise ValueError("A paper submission may contain at most four categories.")
    return normalized


def _schema() -> tuple[list[str], set[str], set[str]]:
    tags = [
        record
        for record in tag_config.TAGS_CONFIG.get("tags", [])
        if record.get("immutable", False) or record.get("enabled", False)
    ]
    tags.sort(key=lambda record: record.get("order", 0))
    ordered = [str(record.get("variable") or "").strip() for record in tags]
    ordered = [field for field in ordered if field]
    arrays = {
        str(record.get("variable") or "").strip()
        for record in tags
        if str(record.get("type") or "").endswith("[]")
    }
    booleans = {
        str(record.get("variable") or "").strip()
        for record in tags
        if str(record.get("type") or "") == "bool"
    }
    return ordered, arrays, booleans


def _normalize_list(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*[|;；]\s*", value) if part.strip()]


def _normalize_contributor(value: str, submitter: str) -> str:
    label = " ".join(str(value or "").split()).strip()
    if label.casefold().startswith("community:"):
        label = label.split(":", 1)[1].strip()
    if not label:
        label = f"@{submitter.lstrip('@').strip()}" if submitter.strip() else "unknown"
    return f"community:{label}"


def _is_accepted_attachment_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        return False
    host = parsed.hostname.casefold()
    if (host == "github.com" and parsed.path.startswith("/user-attachments/assets/")) or host == "user-images.githubusercontent.com":
        return True
    configured = urlparse(os.environ.get("SIM_UPLOAD_ENDPOINT", "").strip().rstrip("/"))
    if configured.scheme != "https" or not configured.hostname:
        return False
    prefix = configured.path.rstrip("/") + "/v1/files/"
    query = parse_qs(parsed.query)
    return (
        host == configured.hostname.casefold()
        and parsed.port == configured.port
        and parsed.path.startswith(prefix)
        and bool(query.get("expires", [""])[0])
        and bool(query.get("signature", [""])[0])
    )


def _normalize_pipeline_images(value: str) -> list[str]:
    urls = re.findall(r"https://[^\s)>]+", str(value or ""))
    accepted: list[str] = []
    for url in urls:
        cleaned = url.rstrip(".,")
        if _is_accepted_attachment_url(cleaned) and cleaned not in accepted:
            accepted.append(cleaned)
    return accepted[:4]


def _normalize_paper_file(value: str) -> str:
    urls = re.findall(r"https://[^\s)>]+", str(value or ""))
    for url in urls:
        cleaned = url.rstrip(".,")
        if _is_accepted_attachment_url(cleaned):
            return cleaned
    return ""


def build_submission(
    body: str,
    *,
    submitter: str,
    issue_number: str,
    issue_url: str,
) -> dict[str, Any]:
    fields = parse_issue_sections(body)
    missing = [field for field in REQUIRED_FIELDS if not fields.get(field)]
    if missing:
        raise ValueError("Issue submission is missing required fields: " + ", ".join(missing))

    fields["doi"] = _normalize_doi(fields["doi"])
    fields["category"] = _normalize_categories(fields["category"])
    if not _valid_http_url(fields["paper_url"]):
        raise ValueError("Paper URL must be an absolute http(s) URL.")
    if fields.get("project_url") and not _valid_http_url(fields["project_url"]):
        raise ValueError("Project URL must be an absolute http(s) URL when supplied.")

    contributor = _normalize_contributor(fields.pop("contributor", ""), submitter)
    provenance = f"Community submission from GitHub issue #{issue_number}"
    if issue_url:
        provenance += f" ({issue_url})"
    rationale = fields.pop("rationale", "")
    submitted_notes = fields.get("notes", "")
    fields["notes"] = provenance
    if rationale:
        fields["notes"] += f"\n\n[Inclusion rationale]\n{rationale}"
    if submitted_notes:
        fields["notes"] += f"\n\n[Submitter notes]\n{submitted_notes}"

    pipeline_images = _normalize_pipeline_images(fields.pop("pipeline_image", ""))
    paper_file = _normalize_paper_file(fields.pop("paper_file", ""))
    fields["related_papers"] = _normalize_list(fields.get("related_papers", ""))

    ordered_fields, array_fields, boolean_fields = _schema()
    paper: dict[str, Any] = {}
    for field in ordered_fields:
        if field in array_fields:
            paper[field] = []
        elif field in boolean_fields:
            paper[field] = False
        else:
            paper[field] = ""
    for field, value in fields.items():
        if field in paper:
            paper[field] = value
    paper.update(
        {
            "contributor": contributor,
            "pipeline_image": pipeline_images,
            "paper_file": paper_file,
            "show_in_readme": True,
            "status": "unread",
            "submission_time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "uid": generate_paper_uid(fields["title"], fields["doi"]),
            "conflict_marker": False,
            "invalid_fields": [],
            "is_placeholder": False,
        }
    )
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "column_ids": ordered_fields,
            "source": "github_issue",
            "source_issue": issue_number,
            "submitted_by": contributor,
            "paper_count": 1,
        },
        "papers": [paper],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-body-env", default="ISSUE_BODY")
    parser.add_argument("--submitter", default=os.environ.get("ISSUE_AUTHOR", ""))
    parser.add_argument("--issue-number", default=os.environ.get("ISSUE_NUMBER", ""))
    parser.add_argument("--issue-url", default=os.environ.get("ISSUE_URL", ""))
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "submit_template.json")
    args = parser.parse_args()

    body = os.environ.get(args.issue_body_env, "")
    if not body.strip():
        raise ValueError(f"Environment variable {args.issue_body_env} does not contain an issue body.")
    submission = build_submission(
        body,
        submitter=args.submitter,
        issue_number=args.issue_number,
        issue_url=args.issue_url,
    )
    args.output.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared one community paper submission from issue #{args.issue_number}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
