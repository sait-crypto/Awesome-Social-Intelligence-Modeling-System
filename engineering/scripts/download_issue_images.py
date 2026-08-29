"""Download bounded GitHub issue image and PDF attachments for processing."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_IMAGES = 4
DOWNLOAD_RETRY_DELAYS = (1, 2, 4, 8, 12, 16, 20)


def allowed_url(url: str, *, redirect: bool = False) -> bool:
    parsed = urlparse(str(url or ""))
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.casefold()
    if redirect:
        return host.endswith(".githubusercontent.com")
    if host == "github.com":
        return parsed.path.startswith("/user-attachments/assets/")
    if host == "user-images.githubusercontent.com":
        return True
    configured = urlparse(os.environ.get("SIM_UPLOAD_ENDPOINT", "").strip().rstrip("/"))
    if configured.scheme != "https" or not configured.hostname:
        return False
    query = parse_qs(parsed.query)
    return (
        not parsed.username
        and not parsed.password
        and not parsed.fragment
        and host == configured.hostname.casefold()
        and parsed.port == configured.port
        and parsed.path.startswith(configured.path.rstrip("/") + "/v1/files/")
        and bool(query.get("expires", [""])[0])
        and bool(query.get("signature", [""])[0])
    )


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not allowed_url(newurl, redirect=True):
            raise ValueError("GitHub attachment redirected to an unapproved host.")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def image_extension(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("The GitHub attachment is not a supported PNG, JPEG, GIF, or WebP image.")


def _download_once(url: str, *, max_bytes: int, field_label: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "SIM-survey-intake/1.0"})
    opener = urllib.request.build_opener(SafeRedirectHandler())
    with opener.open(request, timeout=30) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_bytes:
            raise ValueError(f"{field_label} exceeds its size limit.")
        content = response.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"{field_label} exceeds its size limit.")
    return content


def download(url: str, *, max_bytes: int = MAX_BYTES, field_label: str = "Pipeline image") -> bytes:
    if not allowed_url(url):
        raise ValueError("Only approved GitHub or configured temporary-upload references are accepted.")
    for attempt in range(len(DOWNLOAD_RETRY_DELAYS) + 1):
        try:
            return _download_once(url, max_bytes=max_bytes, field_label=field_label)
        except urllib.error.HTTPError as error:
            retryable = error.code in {404, 429, 500, 502, 503, 504}
            if not retryable or attempt >= len(DOWNLOAD_RETRY_DELAYS):
                raise
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionError, TimeoutError):
            if attempt >= len(DOWNLOAD_RETRY_DELAYS):
                raise
        time.sleep(DOWNLOAD_RETRY_DELAYS[attempt])
    raise RuntimeError("Submission attachment download exhausted its retry policy.")


def materialize_images(
    submission_path: Path,
    project_root: Path = PROJECT_ROOT,
    *,
    pdf_bundle_dir: Path | None = None,
) -> list[Path]:
    data = json.loads(submission_path.read_text(encoding="utf-8-sig"))
    papers = data.get("papers") if isinstance(data, dict) else None
    if not isinstance(papers, list):
        raise ValueError("Submission JSON must contain a papers array.")

    prepared: list[dict[str, object]] = []
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        references = paper.get("pipeline_image", [])
        if not isinstance(references, list):
            raise ValueError("pipeline_image must be an array before attachment download.")
        if len(references) > MAX_IMAGES:
            raise ValueError(f"A submission may include at most {MAX_IMAGES} pipeline images.")

        uid = str(paper.get("uid") or "").strip().casefold()
        if not re.fullmatch(r"[a-f0-9]{8,40}", uid):
            raise ValueError("Paper UID is missing or unsafe for an asset directory.")
        downloaded_images: list[tuple[bytes, str]] = []
        for reference in references:
            content = download(str(reference))
            suffix = image_extension(content)
            downloaded_images.append((content, suffix))

        paper_reference = str(paper.get("paper_file") or "").strip()
        downloaded_pdf: bytes | None = None
        if paper_reference:
            downloaded_pdf = download(paper_reference, max_bytes=MAX_PDF_BYTES, field_label="Paper PDF")
            if not downloaded_pdf.startswith(b"%PDF-"):
                raise ValueError("The GitHub paper attachment is not a valid PDF container.")
        prepared.append({"paper": paper, "uid": uid, "images": downloaded_images, "pdf": downloaded_pdf})

    # Do not write a partial submission: every remote file is downloaded and
    # signature-checked before any repository or temporary-bundle file exists.
    created: list[Path] = []
    for item in prepared:
        paper = item["paper"]
        uid = str(item["uid"])
        local_references: list[str] = []
        for content, suffix in item["images"]:
            digest = hashlib.sha256(content).hexdigest()[:10]
            relative = Path("engineering") / "assets" / uid / f"community-pipeline-{digest}{suffix}"
            destination = project_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            created.append(destination)
            local_references.append(relative.as_posix())
        paper["pipeline_image"] = local_references

        content = item["pdf"]
        if isinstance(content, bytes):
            digest = hashlib.sha256(content).hexdigest()[:10]
            relative = Path("engineering") / "assets" / uid / f"community-paper-{digest}.pdf"
            destination = (pdf_bundle_dir / relative) if pdf_bundle_dir else (project_root / relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            created.append(destination)
            paper["paper_file"] = relative.as_posix()

    submission_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", nargs="?", type=Path, default=PROJECT_ROOT / "submit_template.json")
    parser.add_argument(
        "--pdf-bundle-dir",
        type=Path,
        help="Write paper PDFs into an ephemeral artifact tree instead of the repository workspace.",
    )
    args = parser.parse_args()
    created = materialize_images(args.submission, pdf_bundle_dir=args.pdf_bundle_dir)
    print(f"Downloaded and materialized {len(created)} submission attachment(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
