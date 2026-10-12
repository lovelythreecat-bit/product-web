"""Offline manifest verification and live read-only DB inventory export."""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def absolute(value, *, exists=True):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute_path_required")
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("links_not_allowed")
    if exists and not path.exists():
        raise ValueError("path_missing")
    return path


def child(root, name):
    if not isinstance(name, str) or "\\" in name or ":" in name:
        raise ValueError("invalid_relative_path")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("invalid_relative_path")
    path = absolute(root / relative, exists=False)
    if path == root or not path.is_relative_to(root):
        raise ValueError("path_outside_root")
    return path


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def inventory(session):
    from sqlalchemy import text

    rows = session.execute(
        text(
            "SELECT internal_path,sha256,actual_bytes,state,'private' kind FROM files "
            "UNION ALL SELECT c.internal_path,c.sha256,c.actual_bytes,p.state,'public' kind "
            "FROM public_case_copies c JOIN public_cases p ON p.id=c.case_id"
        )
    ).mappings()
    result = []
    for row in rows:
        row = dict(row)
        if not re.fullmatch(r"[a-f0-9]{32}/[a-f0-9]{32}", row["internal_path"]):
            raise ValueError("invalid_storage_identity")
        row["path"] = row.pop("internal_path") + ".blob"
        # Cleanup can have removed bytes before its DB completion receipt.
        row["required"] = row["state"] in {"durable", "published"}
        result.append(row)
    return sorted(result, key=lambda row: (row["kind"], row["path"]))


def verify(root, entries):
    root = absolute(root)
    differences = []
    seen = set()
    for entry in entries:
        name = entry["path"]
        if name in seen:
            raise ValueError("duplicate_manifest_path")
        seen.add(name)
        path = child(root, name)
        if not path.is_file():
            if entry.get("required", True):
                differences.append({"code": "missing_file", "path": name})
            continue
        if (
            path.stat().st_size != entry["actual_bytes"]
            or digest(path) != entry["sha256"]
        ):
            differences.append({"code": "file_hash_mismatch", "path": name})
    return differences


def file_manifest(root):
    root = absolute(root)
    entries = []
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            absolute(Path(base) / name)
        for name in sorted(files):
            path = Path(base) / name
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "actual_bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
    return sorted(entries, key=lambda item: item["path"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--inventory", required=True)
    args = parser.parse_args()
    try:
        entries = json.loads(absolute(args.inventory).read_text(encoding="utf-8"))
        differences = verify(args.root, entries)
        print(json.dumps({"ok": not differences, "differences": differences}))
        return 2 if differences else 0
    except (OSError, ValueError, KeyError, TypeError):
        print('{"ok":false,"code":"storage_verification_failed"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())
