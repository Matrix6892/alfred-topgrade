import hashlib
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from install import BUNDLE_ID, install, package_files
from scripts.build import build


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.preferences = self.root / "Alfred.alfredpreferences"
        self.preferences.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_fresh_install_and_other_workflow_preserved(self):
        other = self.preferences / "workflows/user.workflow.other"
        other.mkdir(parents=True)
        (other / "notes.txt").write_text("user changes")
        destination, backup = install(self.preferences)
        self.assertIsNone(backup)
        self.assertEqual(set(p.name for p in destination.iterdir()), set(package_files()))
        self.assertEqual((other / "notes.txt").read_text(), "user changes")

    def test_upgrade_finds_imported_folder_and_keeps_full_backup(self):
        imported = self.preferences / "workflows/user.workflow.IMPORTED-UUID"
        imported.mkdir(parents=True)
        with (imported / "info.plist").open("wb") as output:
            plistlib.dump({"bundleid": BUNDLE_ID}, output)
        (imported / "custom.txt").write_text("local customization")
        destination, backup = install(self.preferences)
        self.assertEqual(destination, imported.resolve())
        self.assertEqual((backup / "custom.txt").read_text(), "local customization")
        self.assertTrue((destination / "session.py").is_file())

    def test_dry_run_does_not_create_files(self):
        install(self.preferences, True)
        self.assertEqual(list(self.preferences.iterdir()), [])

    def test_unknown_destination_is_not_overwritten(self):
        occupied = self.preferences / "workflows/user.workflow.local.topgrade-ghostty"
        occupied.mkdir(parents=True)
        (occupied / "important.txt").write_text("keep")
        with self.assertRaises(RuntimeError):
            install(self.preferences)
        self.assertEqual((occupied / "important.txt").read_text(), "keep")

    def test_missing_preferences_are_not_created(self):
        missing = self.root / "Missing.alfredpreferences"
        with self.assertRaises(RuntimeError):
            install(missing)
        self.assertFalse(missing.exists())

    def test_package_is_complete_and_reproducible(self):
        first = build(self.root / "one.alfredworkflow")
        second = build(self.root / "two.alfredworkflow")
        self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
        with ZipFile(first) as archive:
            self.assertEqual(set(archive.namelist()), set(package_files()))
            self.assertIsNone(archive.testzip())
            info = plistlib.loads(archive.read("info.plist"))
            self.assertEqual(info["bundleid"], BUNDLE_ID)
