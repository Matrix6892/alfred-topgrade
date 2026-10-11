# Runtime contract

The user runs `topgrade` in Alfred. One dedicated Ghostty tab, or one Terminal.app
window, owns the update process and remains available for later runs.

| State | Request | Result |
| --- | --- | --- |
| No managed terminal | update/check | Create one terminal, wait for readiness, request execution |
| Idle | update/check | Execute once in the same terminal |
| Queued/running | update/check | Ignore; no second execution and no later queued execution |
| Failed command, returned to idle | update/check | Allow a new execution; retain previous exit code |
| Closed terminal | update/check | Create another terminal |
| Restored terminal | startup | Start idle; never update automatically |
| Existing terminal, unresponsive process | update/check | Show an error asking the user to close it and retry |

`run.sh` finds Python even with Alfred's limited PATH. `launch.py` holds an OS file
lock across native terminal discovery/creation. It keeps the backend of a live
session; otherwise it prefers Ghostty 1.3.1+ and falls back to Terminal.app.
The two AppleScript files are separate so a machine without Ghostty can compile and
run the Terminal backend independently of Ghostty's scripting dictionary.

`session.py` runs inside the dedicated terminal and owns all execution state. Its
local socket accepts only `update`, `check`, `status`. An OS file lock permits only
one session process. A thread serializes requests under a lock while the main
thread executes the updater with the terminal's normal input/output. Acceptance
marks the session queued before acknowledging the request; busy requests cannot
become a second run after the first finishes. Requests are not retried after sending
because a lost acknowledgement could otherwise repeat an update.

Topgrade is found through `TOPGRADE_BINARY`, an existing `~/.local/bin/topgrade`
wrapper, the login PATH, then standard Apple Silicon/Intel Homebrew paths. Its
existing configuration is used as-is. Runtime state and the 0600 socket live in
`~/Library/Caches/topgrade-alfred/`. `TOPGRADE_STATE_DIR` provides an isolated location
for testing; keep its socket path under the Unix socket length limit (about 100 bytes
on macOS).

Ghostty surface IDs identify the managed terminal and the previously focused pane.
After restoration, an alive session can be rediscovered by its `Topgrade — …` title.
Ghostty selects new tabs itself; the integration restores the previous pane after
native creation settles. A brief first-creation focus change is possible. Reusing
the tab requires no keyboard input, application activation or focus change.

Terminal.app uses one dedicated window because its native scripting API does not
create tabs. Its saved terminal device identifies that window; a live session can
also be recovered by its `Topgrade — …` title. The title changes between running
and idle, so matching the original exact title would incorrectly lose the session.
The previous Terminal window is restored to the front after creation;
the initial creation may still bring Terminal.app forward. Reuse sends only a local
request and leaves window ordering alone.

Closing the terminal ends its session process and releases its socket/lock. Restored
windows launch an idle session; actual updates require a fresh Alfred request.
No service or login item is installed. Errors retain exit codes in `state.json`.

# Verification boundaries

Automated tests use fake updaters to cover duplicates, reuse, failure, cleanup,
idle restoration, portable selection, installation and archive reproducibility.
Native compile checks verify AppleScript grammar against installed dictionaries.
Real `--version` checks verify terminal creation/reuse without updating software.
A full application restart and a full interactive update are separate manual checks;
the test suite does not claim to exercise those user sessions.
