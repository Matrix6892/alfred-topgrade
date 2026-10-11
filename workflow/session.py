#!/usr/bin/python3
"""Own one Topgrade terminal; accept fixed requests, never arbitrary shell text."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import tempfile
import shutil

STATE_DIR = Path(os.environ.get("TOPGRADE_STATE_DIR", str(Path.home() / "Library/Caches/topgrade-alfred"))).expanduser()


def find_topgrade(environ=None, home=None):
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    override = environ.get("TOPGRADE_BINARY")
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_absolute() or not os.access(candidate, os.X_OK) or not candidate.is_file():
            raise RuntimeError("TOPGRADE_BINARY must be the absolute path to an executable")
        return candidate
    candidates = [home / ".local/bin/topgrade"]
    resolved = shutil.which("topgrade", path=environ.get("PATH", ""))
    if resolved:
        candidates.append(Path(resolved))
    candidates += [Path("/opt/homebrew/bin/topgrade"), Path("/usr/local/bin/topgrade")]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("Topgrade was not found. Install it with brew install topgrade, then try again.")


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=path.name + ".", delete=False) as output:
        output.write(json.dumps(value, ensure_ascii=False) + "\n")
        temporary = Path(output.name)
    temporary.replace(path)


def request(directory, command, retry_startup=False):
    deadline = time.monotonic() + (8 if retry_startup else 0)
    while True:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(2)
        try:
            client.connect(str(directory / "control.sock"))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            client.close()
            if time.monotonic() >= deadline:
                raise RuntimeError("The Topgrade session is not ready or has exited. Close its terminal and try again.")
            time.sleep(0.1)
    # No retry after sending: a lost acknowledgement must not repeat an update.
    with client:
        client.sendall((command + "\n").encode())
        response = client.makefile("r").readline(4096)
        return json.loads(response)


class Session:
    def __init__(self, directory, executable, initial=None):
        self.directory = directory
        self.executable = executable
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.closed = threading.Event()
        self.pending = initial
        self.state = {"phase": "queued" if initial else "idle", "pid": os.getpid(), "run_count": 0,
                      "mode": initial, "last_exit": None, "last_version": None}
        if initial:
            self.wake.set()
        self.child = None

    def save(self):
        atomic_json(self.directory / "state.json", self.state)

    def accept(self, command):
        with self.lock:
            if command == "status":
                return dict(self.state)
            if command not in ("update", "check"):
                return {"outcome": "invalid"}
            if self.state["phase"] != "idle":
                return {"outcome": "busy", "phase": self.state["phase"]}
            self.pending = command
            self.state.update(phase="queued", mode=command)
            self.save()
            self.wake.set()
            return {"outcome": "accepted", "phase": "queued"}

    def listen(self, server):
        while not self.closed.is_set():
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with connection:
                connection.settimeout(1)
                try:
                    command = connection.makefile("r").readline(32).strip()
                    response = self.accept(command)
                    connection.sendall((json.dumps(response) + "\n").encode())
                except (OSError, UnicodeError):
                    continue

    def run(self):
        while not self.closed.is_set():
            self.wake.wait()
            self.wake.clear()
            with self.lock:
                mode = self.pending
                self.pending = None
                self.state.update(phase="running", mode=mode,
                                  run_count=self.state["run_count"] + 1)
                self.save()
            print("\033]0;Topgrade — " + ("check" if mode == "check" else "updating") + "\007", end="", flush=True)
            print("\n── Topgrade: " + ("version check" if mode == "check" else "update") + " ──", flush=True)
            version = None
            try:
                if mode == "check":
                    self.child = subprocess.Popen([str(self.executable), "--version"],
                                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    version, _ = self.child.communicate()
                    print(version, end="", flush=True)
                else:
                    # Inherit the controlling terminal so sudo and prompts work.
                    self.child = subprocess.Popen([str(self.executable)])
                    self.child.wait()
                exit_code = self.child.returncode
            except OSError as error:
                print("Could not start Topgrade: " + str(error), flush=True)
                exit_code = 127
            self.child = None
            with self.lock:
                self.state.update(phase="idle", last_exit=exit_code,
                                  last_version=version.strip() if version else None)
                self.save()
            print("\033]0;Topgrade — idle\007", end="", flush=True)
            print("\nFinished (exit code %s). Run topgrade in Alfred to update here again.\n"
                  "You can keep this terminal open or close it.\n" % exit_code, flush=True)


def serve(directory, executable, initial=None):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    # OS-owned lock prevents a second supervisor even after stale files/crashes.
    with (directory / "supervisor.lock").open("a") as process_lock:
        fcntl.flock(process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        address = directory / "control.sock"
        address.unlink(missing_ok=True)
        session = Session(directory, executable, initial)
        print("\033]0;Topgrade — idle\007", end="", flush=True)
        print("Topgrade session. Run topgrade in Alfred to update.\n", flush=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(address))
        os.chmod(address, 0o600)
        server.listen(8)
        server.settimeout(0.2)
        session.save()
        threading.Thread(target=session.listen, args=(server,), daemon=True).start()

        def stop(_signal, _frame):
            raise SystemExit(0)

        def interrupt(_signal, _frame):
            if session.child is not None and session.child.poll() is None:
                session.child.send_signal(signal.SIGINT)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGHUP, stop)
        signal.signal(signal.SIGINT, interrupt)
        try:
            session.run()
        finally:
            session.closed.set()
            server.close()
            if session.child is not None and session.child.poll() is None:
                session.child.terminate()
                try:
                    session.child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    session.child.kill()
                    session.child.wait()
            address.unlink(missing_ok=True)
            with session.lock:
                session.state["phase"] = "closed"
                session.save()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=STATE_DIR)
    parser.add_argument("--topgrade", type=Path)
    parser.add_argument("action", choices=("serve", "request", "status", "probe"))
    parser.add_argument("mode", nargs="?", choices=("update", "check"), default="update")
    args = parser.parse_args()
    try:
        if args.action == "serve":
            # Restoring a saved Ghostty tab must never start updates by itself,
            # even if an older saved command includes a legacy initial mode.
            serve(args.state_dir, args.topgrade or find_topgrade())
        else:
            result = request(args.state_dir, "status" if args.action in ("status", "probe") else args.mode, args.action != "probe")
            if args.action == "request":
                atomic_json(args.state_dir / "last-request.json", result)
            print(json.dumps(result))
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
