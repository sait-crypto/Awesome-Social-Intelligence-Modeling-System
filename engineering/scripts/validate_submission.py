"""Validate paper submission files and their referenced assets.

Submission JSON uses the normalized ``meta``/``papers`` object and stores every
``type=[]`` field as a JSON array. Submission CSV uses the two-header-row schema
and stores the same fields as ``|``-separated cells.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config_loader import get_config_instance
from src.core.database_model import Paper, is_duplicate_paper
from src.core.update_file_utils import UpdateFileUtils, get_update_file_utils


SUBMISSION_PATH_KEYS = ("update_csv", "update_json")
MAX_SUBMISSION_BYTES = 5 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 50 * 1024 * 1024


def _configure_output() -> None:
    """Avoid Windows console encoding failures while printing paper titles."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


_configure_output()


def _ordered_tags(config: Any) -> list[dict[str, Any]]:
    return sorted(config.get_active_tags(), key=lambda tag: tag.get("order", 0))


def _schema_fields(config: Any) -> tuple[list[str], set[str], set[str]]:
    tags = _ordered_tags(config)
    ordered = [str(tag.get("variable") or "").strip() for tag in tags]
    ordered = [field for field in ordered if field]
    arrays = {
        str(tag.get("variable") or "").strip()
        for tag in tags
        if str(tag.get("type") or "").endswith("[]")
    }
    booleans = {
        str(tag.get("variable") or "").strip()
        for tag in tags
        if str(tag.get("type") or "") == "bool"
    }
    return ordered, arrays, booleans


def _array_field_limit(config: Any, field: str) -> int | None:
    setting_names = {
        "category": "max_categories_per_paper",
        "pipeline_image": "max_pipeline_images_per_paper",
    }
    setting_name = setting_names.get(field)
    if not setting_name:
        return None
    try:
        return max(1, int(config.settings.get("database", {}).get(setting_name, 4)))
    except (TypeError, ValueError):
        return 4


def _read_csv_rows(path: Path) -> list[list[str]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "cp1252", "latin-1"):
        try:
            with path.open("r", encoding=encoding, errors="strict", newline="") as handle:
                return list(csv.reader(handle))
        except (OSError, UnicodeError, csv.Error) as error:
            last_error = error
    raise ValueError(f"cannot read CSV: {last_error}")


def validate_json_structure(path: Path, config: Any) -> list[str]:
    """Validate the normalized on-disk JSON representation before conversion."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"invalid JSON: {error}"]

    if not isinstance(data, dict):
        return ["top level must be an object containing 'meta' and 'papers'"]

    meta = data.get("meta")
    papers = data.get("papers")
    if not isinstance(meta, dict):
        errors.append("'meta' must be an object")
    if not isinstance(papers, list):
        errors.append("'papers' must be an array")
        return errors

    ordered_fields, array_fields, boolean_fields = _schema_fields(config)
    known_fields = set(ordered_fields)

    if isinstance(meta, dict):
        column_ids = meta.get("column_ids")
        if not isinstance(column_ids, list) or not all(isinstance(item, str) for item in column_ids):
            errors.append("meta.column_ids must be an array of field-name strings")
        elif column_ids != ordered_fields:
            errors.append("meta.column_ids does not match the current active field order")

        paper_count = meta.get("paper_count")
        if not isinstance(paper_count, int) or isinstance(paper_count, bool):
            errors.append("meta.paper_count must be an integer")
        elif paper_count != len(papers):
            errors.append(
                f"meta.paper_count is {paper_count}, but papers contains {len(papers)} item(s)"
            )

    for index, item in enumerate(papers, start=1):
        prefix = f"item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        unknown = sorted(set(item) - known_fields)
        if unknown:
            errors.append(f"{prefix} contains unknown field(s): {', '.join(unknown)}")

        missing = [field for field in ordered_fields if field not in item]
        if missing:
            errors.append(f"{prefix} is missing field(s): {', '.join(missing)}")

        for field, value in item.items():
            if field not in known_fields:
                continue
            if field in array_fields:
                if not isinstance(value, list):
                    errors.append(f"{prefix}.{field} must be a JSON array")
                    continue
                if not all(isinstance(part, str) and part.strip() for part in value):
                    errors.append(f"{prefix}.{field} must contain only non-empty strings")
                normalized = [part.strip().casefold() for part in value if isinstance(part, str)]
                if len(normalized) != len(set(normalized)):
                    errors.append(f"{prefix}.{field} contains duplicate values")
                limit = _array_field_limit(config, field)
                if limit is not None and len(value) > limit:
                    errors.append(f"{prefix}.{field} contains more than {limit} values")
            elif field in boolean_fields:
                if not isinstance(value, bool):
                    errors.append(f"{prefix}.{field} must be a JSON Boolean")
            elif not isinstance(value, str):
                errors.append(f"{prefix}.{field} must be a string")

    return errors


def validate_csv_structure(path: Path, config: Any) -> list[str]:
    """Validate the normalized two-header-row CSV representation."""
    try:
        rows = _read_csv_rows(path)
    except ValueError as error:
        return [str(error)]

    if len(rows) < 2:
        return ["CSV must contain a display-name row and a field-name row"]

    ordered_fields, array_fields, boolean_fields = _schema_fields(config)
    display_header = rows[0]
    field_header = [cell.strip() for cell in rows[1]]
    errors: list[str] = []

    if field_header != ordered_fields:
        errors.append("the second CSV row does not match the current active field order")
    if len(display_header) != len(field_header):
        errors.append("the two CSV header rows have different column counts")
    if len(field_header) != len(set(field_header)):
        errors.append("the second CSV row contains duplicate field names")

    for row_number, row in enumerate(rows[2:], start=3):
        if not any(str(cell).strip() for cell in row):
            continue
        if len(row) != len(field_header):
            errors.append(
                f"row {row_number} has {len(row)} column(s); expected {len(field_header)}"
            )
            continue

        for field, value in zip(field_header, row):
            if field in array_fields:
                items = [part.strip() for part in value.split("|") if part.strip()]
                normalized = [part.casefold() for part in items]
                if len(normalized) != len(set(normalized)):
                    errors.append(f"row {row_number}.{field} contains duplicate values")
                limit = _array_field_limit(config, field)
                if limit is not None and len(items) > limit:
                    errors.append(f"row {row_number}.{field} contains more than {limit} values")
            elif field in boolean_fields and value.strip().casefold() not in {"true", "false"}:
                errors.append(f"row {row_number}.{field} must be true or false")

    return errors


def validate_submission_structure(path: Path, config: Any) -> list[str]:
    if path.suffix.lower() == ".json":
        return validate_json_structure(path, config)
    if path.suffix.lower() == ".csv":
        return validate_csv_structure(path, config)
    return [f"unsupported submission format: {path.suffix or '<none>'}"]


def get_original_content(source_path: Path, destination: Path, project_root: Path) -> bool:
    """Write the ``origin/main`` version of *source_path* to *destination*."""
    try:
        relative = source_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        print(f"Warning: path is outside the project root: {source_path}")
        return False

    try:
        with destination.open("wb") as handle:
            subprocess.check_call(
                ["git", "show", f"origin/main:{relative}"],
                cwd=project_root,
                stdout=handle,
                stderr=subprocess.DEVNULL,
            )
        return True
    except subprocess.CalledProcessError:
        print(f"Info: {relative} is not present on origin/main; treating it as a new file.")
        return False
    except OSError as error:
        print(f"Warning: cannot read the origin/main version of {relative}: {error}")
        return False


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _candidate_asset_roots(config: Any) -> list[Path]:
    paths = config.settings.get("paths", {}) or {}
    candidates = [
        paths.get("assets_dir"),
        paths.get("figure_dir"),
        os.environ.get("PR_ASSETS_DIR"),
        os.environ.get("PR_FIGURES_DIR"),
    ]
    roots: list[Path] = []
    for raw in candidates:
        if not raw:
            continue
        root = Path(str(raw))
        if not root.is_absolute():
            root = Path(config.project_root) / root
        root = root.resolve()
        if root not in roots:
            roots.append(root)
    return roots


def _relative_asset_parts(reference: str, configured_assets: Path) -> tuple[str, ...]:
    normalized = reference.replace("\\", "/").strip()
    parts = tuple(part for part in normalized.split("/") if part not in ("", "."))
    configured_parts = tuple(part for part in configured_assets.as_posix().split("/") if part)
    if configured_parts and len(parts) >= len(configured_parts):
        left = tuple(part.casefold() for part in parts[: len(configured_parts)])
        right = tuple(part.casefold() for part in configured_parts)
        if left == right:
            return parts[len(configured_parts) :]
    return parts


def _resolve_asset_reference(
    reference: str,
    *,
    uid: str,
    project_root: Path,
    configured_assets: Path,
    roots: Sequence[Path],
) -> Path | None:
    raw = str(reference or "").strip()
    if not raw or Path(raw).is_absolute():
        return None
    parts = _relative_asset_parts(raw, configured_assets)
    if not parts or ".." in parts:
        return None

    candidates = [project_root.joinpath(*parts), project_root / raw]
    for root in roots:
        candidates.append(root.joinpath(*parts))
        candidates.append(root / Path(raw).name)
        if uid:
            candidates.append(root / uid / Path(raw).name)

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file() and (
            _is_within(resolved, project_root)
            or any(_is_within(resolved, root) for root in roots)
        ):
            return resolved
    return None


def validate_paper_assets(
    paper: Paper,
    *,
    config: Any,
    roots: Sequence[Path] | None = None,
) -> list[str]:
    """Validate only assets referenced by this submission entry."""
    paths = config.settings.get("paths", {}) or {}
    project_root = Path(config.project_root).resolve()
    configured_assets = Path(str(paths.get("assets_dir", "engineering/assets")))
    if configured_assets.is_absolute():
        try:
            configured_assets = configured_assets.resolve().relative_to(project_root)
        except ValueError:
            configured_assets = Path(configured_assets.name)
    asset_roots = list(roots or _candidate_asset_roots(config))
    errors: list[str] = []

    field_specs = {
        "pipeline_image": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"},
        "paper_file": {".pdf"},
    }
    for field, allowed_suffixes in field_specs.items():
        raw_value = str(getattr(paper, field, "") or "").strip()
        references = [part.strip() for part in raw_value.split("|") if part.strip()]
        if field == "paper_file" and len(references) > 1:
            errors.append("paper_file accepts only one PDF")
        for reference in references:
            path_parts = Path(reference.replace("\\", "/")).parts
            if Path(reference).is_absolute() or ".." in path_parts:
                errors.append(f"{field} must use a safe project-relative path: {reference}")
                continue
            if Path(reference).suffix.casefold() not in allowed_suffixes:
                expected = "an image" if field == "pipeline_image" else "a PDF"
                errors.append(f"{field} must reference {expected}: {reference}")
                continue
            resolved = _resolve_asset_reference(
                reference,
                uid=str(getattr(paper, "uid", "") or "").strip(),
                project_root=project_root,
                configured_assets=configured_assets,
                roots=asset_roots,
            )
            if resolved is None:
                errors.append(f"{field} file was not found: {reference}")
                continue
            try:
                size = resolved.stat().st_size
                if field == "pipeline_image" and size > MAX_IMAGE_BYTES:
                    errors.append(f"pipeline_image exceeds the 10 MiB limit: {reference}")
                if field == "paper_file":
                    if size > MAX_PDF_BYTES:
                        errors.append(f"paper_file exceeds the 50 MiB limit: {reference}")
                    with resolved.open("rb") as handle:
                        if handle.read(5) != b"%PDF-":
                            errors.append(f"paper_file is not a valid PDF container: {reference}")
            except OSError as error:
                errors.append(f"cannot inspect {field} file {reference}: {error}")
    return errors


def validate_papers(
    papers: Sequence[Paper],
    original_papers: Sequence[Paper],
    source_name: str,
    *,
    config: Any | None = None,
    asset_roots: Sequence[Path] | None = None,
) -> tuple[int, int]:
    """Return ``(valid_new_count, error_count)`` for a loaded submission."""
    config = config or get_config_instance()
    valid_count = 0
    error_count = 0
    accepted: list[Paper] = []
    print(f"\n--- Validating {source_name} ({len(papers)} item(s)) ---")

    for index, paper in enumerate(papers, start=1):
        # Metadata validation must not try to copy or normalize PR-staged files.
        metadata_paper = copy.deepcopy(paper)
        metadata_paper.pipeline_image = ""
        metadata_paper.paper_file = ""
        is_valid, errors, _ = metadata_paper.validate_paper_fields(
            config,
            check_required=True,
            check_non_empty=True,
            no_normalize=True,
        )
        errors.extend(validate_paper_assets(paper, config=config, roots=asset_roots))

        title = str(paper.title or "<untitled>")[:60]
        if not is_valid or errors:
            print(f"ERROR [item {index}] validation failed: {title}")
            for error in errors:
                print(f"  - {error}")
            error_count += 1
            continue

        duplicate_in_file, _ = is_duplicate_paper(accepted, paper, complete_compare=False)
        if duplicate_in_file:
            print(f"ERROR [item {index}] duplicate paper in submission: {title}")
            error_count += 1
            continue

        unchanged, _ = is_duplicate_paper(original_papers, paper, complete_compare=True)
        if unchanged:
            print(f"SKIP  [item {index}] unchanged from origin/main: {title}")
            accepted.append(paper)
            continue

        print(f"OK    [item {index}] valid submission: {title}")
        accepted.append(paper)
        valid_count += 1

    return valid_count, error_count


def _nonempty_submission_paths(
    config: Any,
    explicit_path: str | None = None,
) -> list[Path]:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if not path.is_absolute():
            path = Path(config.project_root) / path
        path = path.resolve()
        return [path] if path.is_file() and path.stat().st_size > 0 else []

    paths = config.settings.get("paths", {}) or {}
    result: list[Path] = []
    for key in SUBMISSION_PATH_KEYS:
        raw = paths.get(key)
        if not raw:
            continue
        path = Path(str(raw))
        if path.is_file() and path.stat().st_size > 0:
            result.append(path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one normalized paper submission file")
    parser.add_argument(
        "--submission-file",
        help="validate this JSON/CSV file; by default use the configured submit_template file",
    )
    args = parser.parse_args(argv)

    config = get_config_instance()
    utils: UpdateFileUtils = get_update_file_utils()
    project_root = Path(config.project_root).resolve()
    submission_paths = _nonempty_submission_paths(config, args.submission_file)

    if not submission_paths:
        if args.submission_file:
            print(f"ERROR: submission file is missing or empty: {args.submission_file}")
        else:
            print("ERROR: no non-empty submit_template.csv or submit_template.json was found.")
        return 1
    if len(submission_paths) > 1:
        names = ", ".join(path.name for path in submission_paths)
        print(f"ERROR: submit exactly one update file; found: {names}")
        return 1

    submission_path = submission_paths[0]
    if submission_path.stat().st_size > MAX_SUBMISSION_BYTES:
        print(f"ERROR: {submission_path.name} exceeds the 5 MiB submission limit.")
        return 1
    structure_errors = validate_submission_structure(submission_path, config)
    if structure_errors:
        print(f"ERROR: {submission_path.name} does not use the normalized submission format:")
        for error in structure_errors:
            print(f"  - {error}")
        return 1

    success, current_papers = utils.read_data(str(submission_path))
    if not success:
        print(f"ERROR: failed to load {submission_path.name}")
        return 1

    original_papers: list[Paper] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        original_path = Path(temp_dir) / f"original{submission_path.suffix.lower()}"
        if get_original_content(submission_path, original_path, project_root):
            original_success, original_papers = utils.read_data(str(original_path))
            if not original_success:
                original_papers = []

        valid_count, error_count = validate_papers(
            current_papers,
            original_papers,
            submission_path.name,
            config=config,
        )

    print("-" * 60)
    if error_count:
        print(f"Validation failed: {error_count} invalid item(s) found.")
        return 1
    if valid_count < 1:
        print("Validation failed: no new or changed paper entries were found.")
        return 1

    print(f"Validation passed: {valid_count} new or changed paper(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
