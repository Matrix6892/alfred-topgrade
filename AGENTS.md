# Project guide

This is a macOS Alfred workflow, distributed as source and a `.alfredworkflow` archive.
Keep runtime code in the Python standard library: the installed workflow must not
require pip, a virtual environment, Node.js, or repository-relative developer tools.

For runtime changes, read `docs/ARCHITECTURE.md`: it defines the session owner,
duplicate-request behavior, terminal fallback and focus guarantees.

For packaging changes, verify fresh installation, backup on replacement, unchanged
unrelated workflows and deterministic archive contents in `tests/test_install.py`.
Run `python3 -m unittest discover -s tests -v` and `python3 scripts/build.py`.
Compile `workflow/terminal.applescript` on macOS. Compile `workflow/ghostty.applescript`
when Ghostty 1.3.1+ is installed. These compile checks do not launch updates.

Keep instructions aligned in this order: English (`README.md`), Russian
(`docs/README.ru.md`), Simplified Chinese (`docs/README.zh-CN.md`). Update behavior,
requirements and limitations in all three when they change.

Run runtime checks using `topgradecheck` or a fake updater. Actual updates must be an
intentional user action. Work with isolated `TOPGRADE_STATE_DIR` when testing a second
session, and preserve live user workflows and terminal sessions.

For CI, use `node scripts/ci_monitor.cjs --help` and that wrapper's commands.
Before publishing, check tracked files for personal paths, tokens, settings, logs,
caches and preference backups. Release only the explicit runtime package manifest.
