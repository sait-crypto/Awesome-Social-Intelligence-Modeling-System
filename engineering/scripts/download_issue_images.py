"""Download bounded GitHub issue image attachments into paper asset folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 10 * 1024 * 1024
MAX_IMAGES = 3


def allowed_url(url: str, *, redirect: bool = False) -> bool:
    parsed = urlparse(str(url or ""))
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.casefold()
    if host == "github.com":
        return parsed.path.startswith("/user-attachments/assets/")
    if host == "user-images.githubusercontent.com":
        return True
    return redirect and host.endswith(".githubusercontent.com")


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


def download(url: str) -> bytes:
    if not allowed_url(url):
        raise ValueError("Only GitHub issue image attachments are accepted.")
    request = urllib.request.Request(url, headers={"User-Agent": "SIM-survey-intake/1.0"})
    opener = urllib.request.build_opener(SafeRedirectHandler())
    with opener.open(request, timeout=30) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_BYTES:
            raise ValueError("Pipeline image exceeds the 10 MiB limit.")
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("Pipeline image exceeds the 10 MiB limit.")
    return content


def materialize_images(submission_path: Path, project_root: Path = PROJECT_ROOT) -> list[Path]:
    data = json.loads(submission_path.read_text(encoding="utf-8-sig"))
    papers = data.get("papers") if isinstance(data, dict) else None
    if not isinstance(papers, list):
        raise ValueError("Submission JSON must contain a papers array.")

    created: list[Path] = []
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
        local_references: list[str] = []
        for reference in references:
            content = download(str(reference))
            suffix = image_extension(content)
            digest = hashlib.sha256(content).hexdigest()[:10]
            relative = Path("engineering") / "assets" / uid / f"community-pipeline-{digest}{suffix}"
            destination = project_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            created.append(destination)
            local_references.append(relative.as_posix())
        paper["pipeline_image"] = local_references

    submission_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", nargs="?", type=Path, default=PROJECT_ROOT / "submit_template.json")
    args = parser.parse_args()
    created = materialize_images(args.submission)
    print(f"Materialized {len(created)} GitHub issue image attachment(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
