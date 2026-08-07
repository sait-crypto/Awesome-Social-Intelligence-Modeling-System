"""Stage submission PDFs for one workflow run and remove them afterwards.

The source files come from the untrusted pull-request asset checkout. Only PDFs
explicitly referenced by a submitted paper are copied into the trusted working
tree. A manifest records every copied path so cleanup can be exact.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config_loader import get_config_instance
from src.core.database_model import Paper
from src.core.update_file_utils import get_update_file_utils


AI_FIELDS = (
    "title_translation",
    "analogy_summary",
    "summary_motivation",
    "summary_innovation",
    "summary_method",
    "summary_conclusion",
    "summary_limitation",
    "summary_citable_paragraph",
)
MAX_PDF_BYTES = 50 * 1024 * 1024


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def paper_needs_ai(paper: Paper, deprecation_mark: str) -> bool:
    return any(
        not str(getattr(paper, field, "") or "").strip()
        or deprecation_mark in str(getattr(paper, field, "") or "")
        for field in AI_FIELDS
    )


def _relative_asset_parts(reference: str, configured_assets: Path) -> tuple[str, ...]:
    raw = str(reference or "").strip().replace("\\", "/")
    if not raw:
        raise ValueError("A paper that needs AI-generated fields has no paper_file value.")
    if Path(raw).is_absolute():
        raise ValueError(
            f"Absolute paper_file paths cannot be used in GitHub Actions: {reference}. "
            "Save the entry again so it uses an engineering/assets/... path."
        )

    parts = tuple(part for part in raw.split("/") if part not in ("", "."))
    if ".." in parts:
        raise ValueError(f"Unsafe paper_file path: {reference}")

    configured_parts = tuple(part for part in configured_assets.as_posix().split("/") if part)
    candidates = (configured_parts, ("engineering", "assets"), ("assets",))
    lower_parts = tuple(part.lower() for part in parts)
    for prefix in candidates:
        lower_prefix = tuple(part.lower() for part in prefix)
        if lower_prefix and lower_parts[: len(lower_prefix)] == lower_prefix:
            remainder = parts[len(prefix) :]
            if remainder:
                return remainder

    raise ValueError(
        f"paper_file must point inside the configured assets directory: {reference}"
    )


def _validate_pdf(path: Path) -> None:
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"The submitted paper file must use the .pdf extension: {path.name}")
    size = path.stat().st_size
    if size > MAX_PDF_BYTES:
        raise ValueError(f"The submitted PDF exceeds the 50 MiB limit: {path.name}")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ValueError(f"The submitted file is not a valid PDF container: {path.name}")


def stage_submission_pdfs(
    papers: Iterable[Paper],
    *,
    project_root: Path,
    assets_dir: Path,
    pr_assets_dir: Path,
    manifest_path: Path,
    deprecation_mark: str = "[Deprecated]",
) -> list[Path]:
    project_root = project_root.resolve()
    assets_root = (project_root / assets_dir).resolve() if not assets_dir.is_absolute() else assets_dir.resolve()
    pr_assets_root = pr_assets_dir.resolve()
    staged: list[Path] = []
    seen: set[Path] = set()
    papers_needing_ai = [
        paper
        for paper in papers
        if str(getattr(paper, "title", "") or "").strip()
        and paper_needs_ai(paper, deprecation_mark)
    ]

    if papers_needing_ai and not pr_assets_root.is_dir():
        print(
            "Warning: no pull-request PDF assets were supplied; "
            "AI generation will use metadata only."
        )

    for paper in papers_needing_ai:

        try:
            parts = _relative_asset_parts(getattr(paper, "paper_file", ""), assets_dir)
        except ValueError as error:
            print(f"Warning: {error} AI generation will use metadata only.")
            continue
        source = pr_assets_root.joinpath(*parts).resolve()
        destination = assets_root.joinpath(*parts).resolve()

        if not _is_within(source, pr_assets_root) or not _is_within(destination, assets_root):
            print(
                f"Warning: unsafe paper_file path for '{paper.title}'; "
                "AI generation will use metadata only."
            )
            continue
        if not source.is_file():
            print(
                "Warning: referenced PDF was not included in the pull request: "
                f"{getattr(paper, 'paper_file', '')}. AI generation will use metadata only."
            )
            continue
        try:
            _validate_pdf(source)
        except (OSError, ValueError) as error:
            print(f"Warning: {error} AI generation will use metadata only.")
            continue

        if destination in seen:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        staged.append(destination)
        seen.add(destination)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "project_root": str(project_root),
                "assets_root": str(assets_root),
                "staged_files": [str(path) for path in staged],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return staged


def cleanup_submission_pdfs(manifest_path: Path) -> list[Path]:
    if not manifest_path.is_file():
        return []

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets_root = Path(str(data.get("assets_root", ""))).resolve()
    removed: list[Path] = []
    for raw_path in data.get("staged_files", []):
        path = Path(str(raw_path)).resolve()
        if path.suffix.lower() != ".pdf" or not _is_within(path, assets_root):
            raise ValueError(f"Refusing to clean an unexpected path from the PDF manifest: {path}")
        if path.is_file():
            path.unlink()
            removed.append(path)
        parent = path.parent
        if parent != assets_root and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()

    manifest_path.unlink(missing_ok=True)
    return removed


def _configured_submission_papers() -> list[Paper]:
    config = get_config_instance()
    update_utils = get_update_file_utils()
    papers: list[Paper] = []
    for key in ("update_csv", "update_json"):
        path = str(config.settings.get("paths", {}).get(key, "") or "").strip()
        if not path or not os.path.isfile(path) or os.path.getsize(path) == 0:
            continue
        success, loaded = update_utils.read_data(path)
        if not success:
            raise RuntimeError(f"Failed to read submission file: {path}")
        papers.extend(loaded)
    return papers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("stage", "cleanup"))
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest).resolve()

    if args.command == "cleanup":
        removed = cleanup_submission_pdfs(manifest_path)
        print(f"Removed {len(removed)} temporary submission PDF(s).")
        return 0

    config = get_config_instance()
    paths = config.settings.get("paths", {})
    staged = stage_submission_pdfs(
        _configured_submission_papers(),
        project_root=Path(config.project_root),
        assets_dir=Path(paths.get("assets_dir", "engineering/assets")),
        pr_assets_dir=Path(os.environ["PR_ASSETS_DIR"]),
        manifest_path=manifest_path,
        deprecation_mark=str(config.settings.get("database", {}).get("value_deprecation_mark", "[Deprecated]")),
    )
    print(f"Staged {len(staged)} temporary submission PDF(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
