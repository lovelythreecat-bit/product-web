"""Fail-closed entrypoint for the operator-enabled staging Compose profile."""

import json
import os
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath


def independent_roots(release, persistent):
    def parse(value):
        cls = PureWindowsPath if re.match(r"^[A-Za-z]:", value) else PurePosixPath
        path = cls(value)
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("absolute_deployment_roots_required")
        return path

    release, persistent = parse(release), parse(persistent)
    if (
        release == persistent
        or release.is_relative_to(persistent)
        or persistent.is_relative_to(release)
    ):
        raise ValueError("persistent_root_overlaps_release")


def main():
    try:
        if os.environ.get("APP_MODE") != "staging" or os.environ.get("APP_TEST_ONLY") != "false":
            raise ValueError("staging_only")
        independent_roots(os.environ["OPS_RELEASE_ROOT"], os.environ["OPS_PERSISTENT_ROOT"])
        approval = json.loads(Path("/run/d12/approval.json").read_text())
        if (
            approval.get("approved") is not True
            or not approval.get("approval_ref")
            or approval.get("release_root") != os.environ["OPS_RELEASE_ROOT"]
            or approval.get("persistent_root") != os.environ["OPS_PERSISTENT_ROOT"]
            or not all(
                approval.get(key)
                for key in ("environment", "rpo", "rto", "backup_schedule", "monitoring_ref")
            )
        ):
            raise ValueError("D12_approval_required")
        root = Path(os.environ["APP_STORAGE_ROOT"])
        if (
            not root.is_absolute()
            or not root.is_dir()
            or (root / ".restore-isolated.json").exists()
        ):
            raise ValueError("persistent_root_unavailable_or_isolated")
        if not sys.argv[1:]:
            raise ValueError("command_required")
    except Exception:
        print('{"code":"staging_start_refused"}', file=sys.stderr)
        return 1
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
