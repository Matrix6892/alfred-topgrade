import os
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflow"))
from launch import choose_backend, ghostty_available
from session import find_topgrade


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def ghostty(self, version):
        app = self.root / "Ghostty.app"
        (app / "Contents").mkdir(parents=True, exist_ok=True)
        with (app / "Contents/Info.plist").open("wb") as output:
            plistlib.dump({"CFBundleShortVersionString": version}, output)
        return app

    def executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o700)
        return path

    def test_missing_ghostty_falls_back_to_terminal(self):
        self.assertEqual(choose_backend(self.root, applications=[]), "terminal")

    def test_old_ghostty_falls_back_to_terminal(self):
        self.assertFalse(ghostty_available([self.ghostty("1.2.3")]))
        self.assertEqual(choose_backend(self.root, [self.root / "Ghostty.app"]), "terminal")

    def test_supported_ghostty_is_preferred(self):
        self.assertEqual(choose_backend(self.root, [self.ghostty("1.3.1")]), "ghostty")

    def test_live_terminal_session_is_kept_when_ghostty_is_installed(self):
        (self.root / "backend").write_text("terminal")
        with patch("launch.request", return_value={"phase": "idle"}):
            self.assertEqual(choose_backend(self.root, [self.ghostty("1.3.1")]), "terminal")

    def test_forced_terminal_and_invalid_preference(self):
        self.assertEqual(choose_backend(self.root, [self.ghostty("1.3.1")], "terminal"), "terminal")
        with self.assertRaises(ValueError):
            choose_backend(self.root, [], "typo")

    def test_user_wrapper_has_priority_over_path(self):
        wrapper = self.executable(self.root / ".local/bin/topgrade")
        self.executable(self.root / "brew/bin/topgrade")
        self.assertEqual(find_topgrade({"PATH": str(self.root / "brew/bin")}, self.root), wrapper)

    def test_plain_homebrew_path_and_explicit_override(self):
        binary = self.executable(self.root / "bin/topgrade")
        self.assertEqual(find_topgrade({"PATH": str(binary.parent)}, self.root), binary)
        self.assertEqual(find_topgrade({"TOPGRADE_BINARY": str(binary)}, self.root), binary)
        with self.assertRaises(RuntimeError):
            find_topgrade({"TOPGRADE_BINARY": "/does/not/exist"}, self.root)
