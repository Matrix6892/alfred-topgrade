"""Verify repeated requests using a fake updater; never runs real updates."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflow"))
import session


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tg-test-", dir="/tmp")
        self.directory = Path(self.temporary.name)
        self.executable = self.directory / "fake-topgrade"
        self.executable.write_text("#!/bin/sh\nprintf 'fake topgrade 1.0\\n'\n/bin/sleep 0.4\n")
        self.executable.chmod(0o700)
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        self.temporary.cleanup()

    def start(self, executable=None, initial="check"):
        process = subprocess.Popen([sys.executable, "-c",
            "from pathlib import Path; import session,sys; session.serve(Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3] or None)",
            str(self.directory), str(executable or self.executable), initial or ""],
            cwd=Path(__file__).resolve().parents[1] / "workflow", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.processes.append(process)
        return process

    def wait_phase(self, phase, count=None):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                state = session.request(self.directory, "status")
                if state["phase"] == phase and (count is None or state["run_count"] == count):
                    return state
            except (OSError, RuntimeError):
                pass
            time.sleep(0.01)
        self.fail("Session did not reach %s, run_count=%s" % (phase, count))

    def test_busy_duplicates_are_ignored_then_idle_reuses_session(self):
        process = self.start()
        self.wait_phase("running", 1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: session.request(self.directory, "check"), range(20)))
        self.assertTrue(all(response["outcome"] == "busy" for response in responses))
        state = self.wait_phase("idle", 1)
        self.assertEqual(state["last_exit"], 0)
        self.assertEqual(state["last_version"], "fake topgrade 1.0")
        self.assertEqual(session.request(self.directory, "check")["outcome"], "accepted")
        state = self.wait_phase("idle", 2)
        self.assertEqual(state["pid"], process.pid)

    def test_second_supervisor_cannot_replace_live_session(self):
        first = self.start()
        self.wait_phase("running")
        second = self.start()
        self.assertNotEqual(second.wait(timeout=5), 0)
        self.assertEqual(session.request(self.directory, "status")["pid"], first.pid)

    def test_launch_failure_leaves_session_reusable(self):
        self.start(self.directory / "missing-topgrade")
        state = self.wait_phase("idle", 1)
        self.assertEqual(state["last_exit"], 127)
        self.assertEqual(session.request(self.directory, "check")["outcome"], "accepted")
        self.assertEqual(self.wait_phase("idle", 2)["last_exit"], 127)

    def test_closed_session_cleans_socket_and_can_restart(self):
        first = self.start()
        self.wait_phase("running")
        first.terminate()
        first.wait(timeout=5)
        self.assertFalse((self.directory / "control.sock").exists())
        self.assertEqual(json.loads((self.directory / "state.json").read_text())["phase"], "closed")
        second = self.start()
        self.assertEqual(self.wait_phase("idle", 1)["pid"], second.pid)

    def test_unrecognized_requests_do_not_run_commands(self):
        self.start()
        self.wait_phase("idle", 1)
        self.assertEqual(session.request(self.directory, "echo anything")["outcome"], "invalid")
        self.assertEqual(session.request(self.directory, "status")["run_count"], 1)

    def test_update_requests_run_normal_command_without_check_arguments(self):
        arguments = self.directory / "arguments"
        self.executable.write_text("#!/bin/sh\nprintf '%s' \"$*\" > '" + str(arguments) + "'\nprintf 'fake topgrade 1.0\\n'\n")
        self.start()
        self.wait_phase("idle", 1)
        self.assertEqual(arguments.read_text(), "--version")
        self.assertEqual(session.request(self.directory, "update")["outcome"], "accepted")
        state = self.wait_phase("idle", 2)
        self.assertEqual(state["mode"], "update")
        self.assertEqual(arguments.read_text(), "")

    def test_updater_failure_is_recorded_and_allows_another_request(self):
        self.executable.write_text("#!/bin/sh\nprintf 'test failure\\n'\nexit 7\n")
        self.start()
        self.assertEqual(self.wait_phase("idle", 1)["last_exit"], 7)
        self.assertEqual(session.request(self.directory, "check")["outcome"], "accepted")
        self.assertEqual(self.wait_phase("idle", 2)["last_exit"], 7)

    def test_restored_session_waits_for_explicit_request(self):
        self.start(initial=None)
        self.wait_phase("idle", 0)
        self.assertEqual(session.request(self.directory, "check")["outcome"], "accepted")
        self.assertEqual(self.wait_phase("idle", 1)["last_exit"], 0)


if __name__ == "__main__":
    unittest.main()
