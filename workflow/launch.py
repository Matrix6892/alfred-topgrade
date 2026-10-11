#!/usr/bin/python3
"""Serialize all Alfred entry points, including the first tab creation."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import plistlib

from session import STATE_DIR, find_topgrade, request

def ghostty_available(applications=None):
    applications = applications if applications is not None else (
        Path("/Applications/Ghostty.app"), Path.home() / "Applications/Ghostty.app")
    for app in applications:
        try:
            with (app / "Contents/Info.plist").open("rb") as source:
                info = plistlib.load(source)
            version = tuple(int(part) for part in info["CFBundleShortVersionString"].split(".")[:3])
            if version >= (1, 3, 1):
                return True
        except (OSError, ValueError, KeyError, plistlib.InvalidFileException):
            continue
    return False


def choose_backend(directory, applications=None, preference="auto"):
    if preference not in ("auto", "ghostty", "terminal"):
        raise ValueError("TOPGRADE_TERMINAL must be auto, ghostty or terminal")
    try:
        request(directory, "status")
        existing = (directory / "backend").read_text().strip()
        if existing in ("ghostty", "terminal"):
            return existing
    except (OSError, RuntimeError, ValueError):
        pass
    if preference == "terminal":
        return "terminal"
    if ghostty_available(applications):
        return "ghostty"
    if preference == "ghostty":
        raise RuntimeError("Ghostty 1.3.1 or newer is required for TOPGRADE_TERMINAL=ghostty")
    return "terminal"


def main():
    os.umask(0o077)
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9 or newer is required")
    if sys.argv[1:] not in ([], ["--check"]):
        sys.exit("Unknown launch mode")
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE_DIR / "launch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        backend = choose_backend(STATE_DIR, preference=os.environ.get("TOPGRADE_TERMINAL", "auto"))
        binary = find_topgrade()
        (STATE_DIR / "backend").write_text(backend)
        workflow = Path(__file__).resolve().parent
        mode = "check" if sys.argv[1:] else "update"
        result = subprocess.run(["/usr/bin/osascript", str(workflow / (backend + ".applescript")),
                                 mode, sys.executable, str(STATE_DIR), str(binary)], cwd=workflow)
        return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
