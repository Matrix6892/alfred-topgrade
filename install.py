#!/usr/bin/env python3
"""Install only this workflow; preserve other workflows and back up replacements."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import plistlib
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
BUNDLE_ID = "local.topgrade.ghostty"
FOLDER = "user.workflow.local.topgrade-ghostty"
WORKFLOW_FILES = ("info.plist", "icon.png", "run.sh", "launch.py", "session.py",
                  "ghostty.applescript", "terminal.applescript", "README.md")


def package_files():
    files = {name: ROOT / "workflow" / name for name in WORKFLOW_FILES}
    files.update({name: ROOT / name for name in ("LICENSE", "CREDITS.md")})
    for source in files.values():
        if not source.is_file():
            raise FileNotFoundError("Missing package source: " + str(source))
    return files


def default_preferences():
    base = Path.home() / "Library/Application Support/Alfred"
    preferences = base / "Alfred.alfredpreferences"
    try:
        current = json.loads((base / "prefs.json").read_text()).get("current")
        if current:
            preferences = Path(current).expanduser()
    except (OSError, ValueError):
        pass
    return preferences


def destination_for(preferences):
    workflows = preferences / "workflows"
    matches = []
    if workflows.exists():
        for folder in workflows.iterdir():
            info = folder / "info.plist"
            if not info.is_file():
                continue
            with info.open("rb") as source:
                try:
                    metadata = plistlib.load(source)
                except plistlib.InvalidFileException:
                    continue
            if metadata.get("bundleid") == BUNDLE_ID:
                matches.append(folder)
    if len(matches) > 1:
        raise RuntimeError("Multiple Topgrade workflows found. Remove duplicates in Alfred Preferences first.")
    destination = matches[0] if matches else workflows / FOLDER
    if not matches and destination.exists():
        raise RuntimeError("The destination is occupied by another workflow: " + str(destination))
    return destination


def install(preferences, dry_run=False):
    preferences = preferences.expanduser().resolve()
    if not preferences.is_dir() or preferences.suffix != ".alfredpreferences":
        raise RuntimeError("Alfred preferences were not found. Start Alfred once, or pass --preferences /path/to/Alfred.alfredpreferences")
    files = package_files()
    destination = destination_for(preferences)
    if dry_run:
        return destination, None
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".topgrade-install-", dir=destination.parent))
    backup = None
    try:
        for name, source in files.items():
            shutil.copy2(source, staged / name)
        if destination.exists():
            backup_root = preferences.parent / "Topgrade Workflow Backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = backup_root / stamp
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError:
            if backup:
                backup.rename(destination)
            raise
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return destination, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preferences", type=Path, default=default_preferences())
    parser.add_argument("--dry-run", action="store_true", help="Show the destination without writing files")
    args = parser.parse_args()
    try:
        destination, backup = install(args.preferences, args.dry_run)
    except (OSError, RuntimeError) as error:
        parser.exit(1, str(error) + "\n")
    print(("Would install: " if args.dry_run else "Installed: ") + str(destination))
    if backup:
        print("Previous workflow preserved: " + str(backup))
    print("In Alfred: topgrade (updates).")


if __name__ == "__main__":
    main()
