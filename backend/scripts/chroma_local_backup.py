"""Local-only cold backups of an existing Chroma bind mount. Python 3.12+.

Run on the Docker host. No network storage, model loading or app settings.
Restore always creates a new directory; never replaces the live database.
"""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

FORMAT = "chroma-local-backup-v1"


def docker(*args):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=90, check=True
    )
    return result.stdout


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect_container(container):
    info = json.loads(docker("inspect", container))[0]
    mounts = [m for m in info["Mounts"] if m["Destination"] == "/data"]
    if len(mounts) != 1 or mounts[0]["Type"] != "bind":
        raise ValueError("expected_one_bind_mount_at_/data")
    source = Path(mounts[0]["Source"]).resolve(strict=True)
    if not source.is_dir() or source == Path("/"):
        raise ValueError("invalid_data_directory")
    if info["State"]["Status"] not in {"running", "exited", "created"}:
        raise ValueError("container_must_be_running_or_stopped")
    return info, source


@contextmanager
def lock(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / ".backup.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def verify(snapshot):
    metadata = json.loads((snapshot / "metadata.json").read_text())
    if metadata.get("format") != FORMAT:
        raise ValueError("unknown_backup_format")
    archive = snapshot / "data.tar.gz"
    if checksum(archive) != metadata["sha256"]:
        raise ValueError("backup_checksum_mismatch")
    # Scan the complete gzip stream and reject paths/links that could escape restore.
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            path = Path(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError("unsafe_archive_member")
            if member.isfile():
                with tar.extractfile(member) as stream:
                    while stream.read(1024 * 1024):
                        pass
    return metadata


def backup(container, destination, keep=7):
    if keep < 1:
        raise ValueError("keep_must_be_positive")
    info, source = inspect_container(container)
    destination = destination.resolve()
    if (
        destination == source
        or source in destination.parents
        or destination in source.parents
    ):
        raise ValueError("backup_and_data_directories_must_be_separate")
    with lock(destination):
        # Recheck: another backup may have finished before the lock was acquired.
        info, checked_source = inspect_container(container)
        if checked_source != source:
            raise ValueError("mount_changed")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        final = destination / f"snapshot-{stamp}-{uuid.uuid4().hex[:8]}"
        temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=destination))
        was_running = info["State"]["Running"]
        try:
            try:
                if was_running:
                    docker("stop", "--time", "60", container)
                state = json.loads(docker("inspect", container))[0]["State"]
                if state["Running"]:
                    raise ValueError("container_still_running")
                # Do not accept a forced kill as a clean cold backup.
                if was_running and state["ExitCode"] in {137, 143}:
                    raise ValueError("container_did_not_exit_cleanly")
                # Chroma creates this file even for an initialized empty database.
                if not (source / "chroma.sqlite3").is_file():
                    raise ValueError("chroma_database_missing_check_mount")
                archive = temporary / "data.tar.gz"
                with tarfile.open(archive, "w:gz") as tar:
                    for path in sorted(source.iterdir()):
                        tar.add(path, arcname=path.name)
            finally:
                # A failure during stop/archive must not leave an initially running
                # service intentionally stopped. Start failure is reported to caller.
                if was_running:
                    docker("start", container)
            metadata = {
                "format": FORMAT,
                "created_at": stamp,
                "container": info["Name"],
                "image_id": info["Image"],
                "image_reference": info["Config"]["Image"],
                "source": str(source),
                "sha256": checksum(archive),
                "archive_bytes": archive.stat().st_size,
            }
            (temporary / "metadata.json").write_text(json.dumps(metadata, indent=2))
            verify(temporary)
            temporary.rename(final)
            # Only prune this tool's own complete snapshots, after successful backup.
            owned = []
            for path in destination.glob("snapshot-*"):
                if path.is_symlink() or not path.is_dir():
                    continue
                try:
                    meta = json.loads((path / "metadata.json").read_text())
                    if (
                        meta.get("format") == FORMAT
                        and meta.get("source") == str(source)
                        and meta.get("container") == info["Name"]
                    ):
                        owned.append(path)
                except (OSError, ValueError):
                    continue
            for path in sorted(owned, key=lambda p: (p == final, p.name), reverse=True)[
                keep:
            ]:
                shutil.rmtree(path)
            return {"snapshot": str(final), **metadata}
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)


def restore(snapshot, target):
    metadata = verify(snapshot)
    if target.exists() or target.is_symlink():
        raise ValueError("restore_target_must_not_exist")
    target.mkdir(parents=True, mode=0o700)
    # Python's data filter rejects traversal and special files. verify rejects links.
    with tarfile.open(snapshot / "data.tar.gz", "r:gz") as tar:
        tar.extractall(target, filter="data")
    return {
        "restored_to": str(target),
        "image_id": metadata["image_id"],
        "activated": False,
    }


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup")
    create.add_argument("--container", required=True)
    create.add_argument("--backup-dir", type=Path, required=True)
    create.add_argument("--keep", type=int, default=7)
    check = commands.add_parser("verify")
    check.add_argument("snapshot", type=Path)
    recover = commands.add_parser("restore")
    recover.add_argument("snapshot", type=Path)
    recover.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            result = backup(args.container, args.backup_dir, args.keep)
        elif args.command == "verify":
            result = verify(args.snapshot)
        else:
            result = restore(args.snapshot, args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": (
                        str(exc) if type(exc) is ValueError else type(exc).__name__
                    ),
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
