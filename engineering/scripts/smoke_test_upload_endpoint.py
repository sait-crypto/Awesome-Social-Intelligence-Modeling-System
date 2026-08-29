"""Exercise the configured public submission upload service end to end."""

from __future__ import annotations

import json
import os
import urllib.request
import uuid
from urllib.parse import urlparse


PNG_FIXTURE = b"\x89PNG\r\n\x1a\nSIM-upload-smoke-test"
MAX_RESPONSE_BYTES = 1024 * 1024


def main() -> int:
    endpoint = os.environ.get("SIM_UPLOAD_ENDPOINT", "").strip().rstrip("/")
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme != "https" or not parsed_endpoint.hostname or parsed_endpoint.path not in {"", "/"}:
        raise ValueError("SIM_UPLOAD_ENDPOINT must be a valid HTTPS origin.")

    request = urllib.request.Request(
        f"{endpoint}/v1/files",
        data=PNG_FIXTURE,
        method="POST",
        headers={
            "Origin": "https://sait-crypto.github.io",
            "Content-Type": "image/png",
            "X-SIM-Submission": str(uuid.uuid4()),
            "X-SIM-File-Kind": "pipeline",
            "X-SIM-File-Index": "0",
            "X-SIM-File-Name": "deployment-smoke-test.png",
            "User-Agent": "SIM-survey-deployment-smoke-test/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if response.status != 201 or len(payload) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"Upload service returned unexpected status {response.status}.")
    result = json.loads(payload)
    reference = str(result.get("reference") or "")
    parsed_reference = urlparse(reference)
    if (
        parsed_reference.scheme != "https"
        or parsed_reference.netloc != parsed_endpoint.netloc
        or not parsed_reference.path.startswith("/v1/files/")
    ):
        raise RuntimeError("Upload service returned an invalid download reference.")

    download = urllib.request.Request(reference, headers={"User-Agent": "SIM-survey-deployment-smoke-test/1.0"})
    with urllib.request.urlopen(download, timeout=30) as response:
        restored = response.read(len(PNG_FIXTURE) + 1)
        if response.status != 200:
            raise RuntimeError(f"Signed download returned unexpected status {response.status}.")
    if restored != PNG_FIXTURE:
        raise RuntimeError("Signed download content does not match the uploaded file.")
    print("Verified direct submission upload and signed download.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
