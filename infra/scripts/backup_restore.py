"""Guarded MySQL/files backup and isolated restore; never stops or deletes a service.

The operator supplies D12 approval and external writer/storage fencing evidence.
MySQL must remain super_read_only for the entire capture. A manifest is written last.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from verify_storage import absolute, child, digest, file_manifest, inventory, verify

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402


def document(path):
    return json.loads(absolute(path).read_text(encoding="utf-8-sig"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.flush()
        os.fsync(output.fileno())


def fresh_target(value, owned_root, owner, purpose):
    root, target = absolute(owned_root), absolute(value, exists=False)
    marker = document(root / ".operations-owner.json")
    if (
        marker.get("owner") != str(UUID(owner))
        or marker.get("purpose") != purpose
        or target == root
        or not target.is_relative_to(root)
        or target.exists()
        or not target.parent.is_dir()
    ):
        raise ValueError("target_not_fresh_owned_child")
    if purpose == "isolated-restore" and marker.get("network_isolated") is not True:
        raise ValueError("isolation_required")
    return target


def client_command(client, defaults_file, url, *, dump=False):
    executable, defaults = absolute(client), absolute(defaults_file)
    if not executable.is_file() or not defaults.is_file():
        raise ValueError("client_or_credentials_missing")
    if (
        url.drivername != "mysql+pymysql"
        or not url.host
        or not url.username
        or not re.fullmatch(r"[A-Za-z0-9_]+", url.database or "")
    ):
        raise ValueError("invalid_database_target")
    command = [
        str(executable),
        "--defaults-file=" + str(defaults),
        "--host=" + url.host,
        "--port=" + str(url.port or 3306),
        "--user=" + url.username,
        "--protocol=TCP",
    ]
    if dump:
        command += [
            "--single-transaction",
            "--quick",
            "--skip-lock-tables",
            "--skip-add-locks",
            "--skip-add-drop-table",
            "--no-tablespaces",
            "--set-gtid-purged=OFF",
            "--hex-blob",
            "--triggers",
            "--skip-comments",
        ]
    else:
        command += ["--binary-mode", "--local-infile=0"]
    command.append(url.database)
    return command


def run_client(command, *, source=None):
    # Never use a shell or print passwords, client stderr, SQL or dump contents.
    result = subprocess.run(
        command,
        stdin=source,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        timeout=86400,
    )
    if result.returncode:
        raise ValueError("database_client_failed")


def proof_valid(proof, storage, url):
    now = datetime.now(timezone.utc)
    cutoff = datetime.fromisoformat(proof["cutoff"])
    expiry = datetime.fromisoformat(proof["fenced_until"])
    if (
        proof.get("d12_approved") is not True
        or not proof.get("approval_ref")
        or not proof.get("writer_fence_ref")
        or not proof.get("storage_snapshot_ref")
        or proof.get("writers_quiesced") is not True
        or absolute(proof["storage_root"]) != storage
        or proof.get("database") != url.database
        or proof.get("host") != url.host
        or proof.get("port") != (url.port or 3306)
        or cutoff.tzinfo is None
        or expiry.tzinfo is None
        or not cutoff <= now < expiry
    ):
        raise ValueError("consistent_snapshot_proof_required")


def assert_fenced(connection, proof):
    row = connection.execute(
        text("SELECT @@GLOBAL.super_read_only, @@server_uuid, VERSION()")
    ).one()
    if row[0] != 1 or row[1] != proof["server_uuid"] or not row[2].startswith("8.4."):
        raise ValueError("database_fence_or_identity_mismatch")
    return row[2]


def backup(args):
    storage, release = absolute(args.storage_root), absolute(args.release_root)
    if storage == release or storage.is_relative_to(release) or release.is_relative_to(storage):
        raise ValueError("storage_must_be_independent_of_release")
    target = fresh_target(args.destination, args.owned_root, args.owner, "backup")
    if (
        target.is_relative_to(storage)
        or storage.is_relative_to(target)
        or target.is_relative_to(release)
        or release.is_relative_to(target)
    ):
        raise ValueError("backup_overlaps_storage")
    manifest_path = absolute(args.manifest, exists=False)
    if manifest_path != target / "manifest.json":
        raise ValueError("manifest_must_be_destination_manifest_json")
    proof = document(args.proof)
    url = make_url(os.environ["OPS_DATABASE_URL"])
    proof_valid(proof, storage, url)
    command = client_command(args.client, args.defaults_file, url, dump=True)
    engine = create_engine(url, echo=False, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            db_version = assert_fenced(connection, proof)
            non_transactional = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=:db "
                    "AND table_type='BASE TABLE' AND engine <> 'InnoDB'"
                ),
                {"db": url.database},
            ).scalar_one()
            if non_transactional:
                raise ValueError("non_transactional_tables")
            entries = inventory(connection)
            if verify(storage, entries):
                raise ValueError("storage_database_mismatch")
            heads = list(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )
            if heads != [proof["migration_head"]]:
                raise ValueError("migration_head_mismatch")
            versions = {
                "release_sha": proof["release_sha"],
                "migration_heads": heads,
                "mysql": db_version,
            }
            if not re.fullmatch(r"[a-f0-9]{40}", versions["release_sha"]):
                raise ValueError("release_sha_required")
            for name in (
                "backend/uv.lock",
                "frontend/pnpm-lock.yaml",
                "infra/compose.staging.yaml",
            ):
                versions[name] = digest(child(release, name))
            before = file_manifest(storage)
            target.mkdir()
            dump = target / "database.sql"
            run_client(command[:-1] + ["--result-file=" + str(dump), command[-1]])
            if not dump.is_file() or dump.stat().st_size == 0:
                raise ValueError("empty_database_snapshot")
            shutil.copytree(storage, target / "storage")
            if (
                file_manifest(storage) != before
                or file_manifest(target / "storage") != before
                or inventory(connection) != entries
            ):
                raise ValueError("capture_changed_during_backup")
            assert_fenced(connection, proof)
            if document(args.proof) != proof:
                raise ValueError("consistency_proof_changed")
            proof_valid(document(args.proof), storage, url)
            write_new(target / "inventory.json", entries)
            write_new(target / "consistency.json", proof)
            payload = {
                "format": 1,
                "status": "complete",
                "cutoff": proof["cutoff"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "owner": str(UUID(args.owner)),
                "versions": versions,
                "restore_requires_isolation": True,
                "public_access": "disabled_on_restore",
                "files": file_manifest(target),
            }
            for entry in payload["files"]:
                with child(target, entry["path"]).open("r+b") as captured:
                    os.fsync(captured.fileno())
            write_new(manifest_path, payload)
        return {"ok": True, "manifest_sha256": digest(manifest_path)}
    finally:
        engine.dispose()


def restore(args):
    manifest_path = absolute(args.manifest)
    if digest(manifest_path) != args.manifest_sha256:
        raise ValueError("untrusted_manifest_hash")
    data, source = document(manifest_path), manifest_path.parent
    if (
        data.get("format") != 1
        or data.get("status") != "complete"
        or data.get("restore_requires_isolation") is not True
    ):
        raise ValueError("invalid_backup_manifest")
    entries = data["files"]
    if verify(source, entries):
        raise ValueError("backup_hash_mismatch")
    paths = {entry["path"] for entry in entries}
    if not {"database.sql", "inventory.json", "consistency.json"}.issubset(paths):
        raise ValueError("backup_missing_required_artifact")
    if verify(source / "storage", document(source / "inventory.json")):
        raise ValueError("backup_inventory_mismatch")
    target = fresh_target(args.target, args.owned_root, args.owner, "isolated-restore")
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("restore_overlaps_backup")
    url = make_url(os.environ["OPS_RESTORE_DATABASE_URL"])
    if url.database != "restore_" + UUID(args.owner).hex:
        raise ValueError("isolated_database_name_required")
    proof = document(args.proof)
    if proof.get("server_uuid") == document(source / "consistency.json").get("server_uuid"):
        raise ValueError("restore_requires_separate_database_server")
    if (
        proof.get("d12_approved") is not True
        or not proof.get("approval_ref")
        or proof.get("network_isolated") is not True
        or proof.get("host") != url.host
        or proof.get("port") != (url.port or 3306)
        or proof.get("database") != url.database
        or proof.get("owner") != str(UUID(args.owner))
        or datetime.fromisoformat(proof["expires_at"]) <= datetime.now(timezone.utc)
    ):
        raise ValueError("isolated_database_proof_required")
    command = client_command(args.client, args.defaults_file, url)
    engine = create_engine(url.set(database=None), echo=False, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            identity = connection.execute(text("SELECT @@server_uuid, VERSION()")).one()
            if identity[0] != proof["server_uuid"] or not identity[1].startswith("8.4."):
                raise ValueError("restore_server_identity_mismatch")
            if connection.execute(
                text("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name=:db"),
                {"db": url.database},
            ).scalar_one():
                raise ValueError("existing_database_refused")
            target.mkdir()
            write_new(target / ".restore-incomplete.json", {"owner": args.owner})
            for entry in entries:
                destination = child(target, entry["path"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                with (
                    child(source, entry["path"]).open("rb") as src,
                    destination.open("xb") as dst,
                ):
                    shutil.copyfileobj(src, dst)
            if verify(target, entries):
                raise ValueError("restore_copy_hash_mismatch")
            (target / "storage").mkdir(exist_ok=True)
            write_new(
                target / "storage" / ".restore-isolated.json",
                {
                    "owner": args.owner,
                    "public_access": "disabled",
                    "reason": "Reconcile post-cutoff withdrawals before explicit release",
                },
            )
            connection.exec_driver_sql(f"CREATE DATABASE `{url.database}` CHARACTER SET utf8mb4")
            connection.commit()
        with (target / "database.sql").open("rb") as snapshot:
            run_client(command, source=snapshot)
        restored = create_engine(url, echo=False, connect_args={"connect_timeout": 5})
        try:
            with restored.connect() as connection:
                heads = list(
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
                )
                if heads != data["versions"]["migration_heads"]:
                    raise ValueError("restored_version_mismatch")
                if verify(target / "storage", inventory(connection)):
                    raise ValueError("restored_database_file_mismatch")
        finally:
            restored.dispose()
        write_new(
            target / "restore-result.json",
            {
                "status": "isolated",
                "owner": args.owner,
                "cutoff": data["cutoff"],
                "manifest_sha256": args.manifest_sha256,
                "public_access": "disabled",
                "service_start": "forbidden_pending_reconciliation",
            },
        )
        return {"ok": True, "status": "isolated", "public_access": "disabled"}
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    for name in ("owned-root", "owner", "manifest", "proof", "client", "defaults-file"):
        parser.add_argument("--" + name, required=True)
    for name in (
        "destination",
        "storage-root",
        "release-root",
        "target",
        "manifest-sha256",
    ):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    try:
        result = backup(args) if args.action == "backup" else restore(args)
        print(json.dumps(result))
        return 0
    except Exception:
        print('{"ok":false,"code":"backup_restore_refused_or_failed"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())
