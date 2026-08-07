"""Repository entry point for the paper submission GUI."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


PACKAGED_SCRIPT_FLAG = "--run-repository-script"
PACKAGED_SCRIPT_TARGETS = {
    "update": Path("engineering/src/update.py"),
    "validate": Path("engineering/src/validate.py"),
}


def _repository_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT_DIR = _repository_root()
ENGINEERING_DIR = ROOT_DIR / "engineering"
if str(ENGINEERING_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_DIR))


def _run_packaged_repository_script() -> bool:
    """Dispatch trusted repository scripts through the packaged interpreter."""
    if not getattr(sys, "frozen", False) or len(sys.argv) < 3:
        return False
    if sys.argv[1] != PACKAGED_SCRIPT_FLAG:
        return False

    target_name = sys.argv[2]
    relative_path = PACKAGED_SCRIPT_TARGETS.get(target_name)
    if relative_path is None:
        raise SystemExit(f"Unsupported repository script: {target_name}")

    script_path = (ROOT_DIR / relative_path).resolve()
    if not script_path.is_file():
        raise SystemExit(f"Repository script not found: {script_path}")

    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.argv = [str(script_path), *sys.argv[3:]]
    runpy.run_path(str(script_path), run_name="__main__")
    return True


def check_dependencies() -> bool:
    """Check the GUI dependency provided by the Python runtime."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Tkinter support is required.")
        return False
    return True


def main() -> None:
    """Start the GUI against the repository containing this entry point."""
    if _run_packaged_repository_script():
        return

    if not check_dependencies():
        raise SystemExit(1)

    if not (ENGINEERING_DIR / "config").is_dir():
        raise SystemExit(
            "The engineering/config directory was not found. Keep the entry point "
            "in the repository root."
        )

    try:
        from src.submit_gui import main as gui_main
    except ImportError as exc:
        raise SystemExit(f"Unable to import the submission GUI: {exc}") from exc

    os.chdir(ROOT_DIR)
    gui_main()


if __name__ == "__main__":
    main()
