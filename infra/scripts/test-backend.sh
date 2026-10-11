#!/bin/sh
# Project-owned Linux runtime for hosts without WSL localhost forwarding.
set -eu
if [ ! -x /runtime/tools/bin/uv ]; then
  python -m pip install --disable-pip-version-check --root-user-action=ignore --timeout 30 --retries 1 --target /runtime/tools uv==0.12.19 &
  installer=$!
  trap 'kill "$installer" 2>/dev/null || true; exit 143' TERM INT
  wait "$installer"
  trap - TERM INT
fi
exec /runtime/tools/bin/uv run --frozen --project /workspace/backend pytest -o cache_dir=/runtime/pytest-cache "$@"
