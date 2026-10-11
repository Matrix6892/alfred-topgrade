#!/bin/sh
# Alfred has a small PATH; find Python without triggering an Xcode install prompt.
set -eu
workflow_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${TOPGRADE_PYTHON:-}" ]; then
    python_bin=$TOPGRADE_PYTHON
elif [ -x /opt/homebrew/bin/python3 ]; then
    python_bin=/opt/homebrew/bin/python3
elif [ -x /usr/local/bin/python3 ]; then
    python_bin=/usr/local/bin/python3
elif /usr/bin/xcrun --find python3 >/dev/null 2>&1; then
    python_bin=/usr/bin/python3
else
    /usr/bin/osascript -e 'display alert "Python 3 is required" message "Install Python 3.9 or newer (for example: brew install python), then try again." as critical'
    exit 1
fi
exec "$python_bin" "$workflow_dir/launch.py" "$@"
