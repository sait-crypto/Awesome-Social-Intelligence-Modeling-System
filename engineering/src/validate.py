"""Compatibility entry point for the contributor submission validator.

The desktop GUI and existing packaged executable invoke this path. GitHub
Actions invokes ``engineering/scripts/validate_submission.py`` directly. Keep
both routes on the same implementation so local validation matches CI.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.validate_submission import main


if __name__ == "__main__":
    raise SystemExit(main())
