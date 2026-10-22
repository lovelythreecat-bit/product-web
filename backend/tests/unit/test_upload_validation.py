"""Actual decoders and physical disk boundaries; no mocked file validators."""

import asyncio
import io
import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.storage.capacity import StorageError
from app.storage.local_store import LocalStore
from app.storage.validation import validate_content, validate_name

FIXTURES = Path(__file__).resolve().parents[3] / "contracts/fixtures/agents"


def test_magic_mime_path_size(tmp_path):
    store = LocalStore(tmp_path)
    data = (FIXTURES / "TEST_ONLY-orange.png").read_bytes()
    staged = asyncio.run(store.stage(io.BytesIO(data), uuid4(), 138))
    assert staged.actual_bytes == 138
    assert (
        validate_content(store.staged_path(staged), "杯子.png", "image/png", ["image/png"])
        == "image/png"
    )
    assert list(tmp_path.rglob("*.blob")) == []
    key = store.commit(staged)
    with store.read(key) as stream:
        assert stream.read() == data
    assert list(tmp_path.rglob("*.part")) == []
    assert len(list(tmp_path.rglob("*.journal"))) == 1
    store.acknowledge(staged)
    assert list(tmp_path.rglob("*.journal")) == []
    with pytest.raises(HTTPException):
        asyncio.run(store.stage(io.BytesIO(data), uuid4(), 137))
    assert list(tmp_path.rglob("*.part")) == []


@pytest.mark.parametrize(
    "name",
    [
        "../a.png",
        "x\\a.png",
        "C:a.png",
        "a\x00.png",
        "/a.png",
        "a.png\r\nX-Header: x",
        "..",
        "a.png ",
    ],
)
def test_unsafe_display_names_rejected(name):
    with pytest.raises(HTTPException):
        validate_name(name)


def test_complete_video_decoding_and_truncated_container_rejection(tmp_path):
    data = (FIXTURES / "TEST_ONLY-orange.mp4").read_bytes()
    path = tmp_path / "video.part"
    path.write_bytes(data)
    assert validate_content(path, "video.mp4", "video/mp4", ["video/mp4"]) == "video/mp4"
    path.write_bytes(data[:-20])
    with pytest.raises(HTTPException):
        validate_content(path, "video.mp4", "video/mp4", ["video/mp4"])


def full_hd_video(tmp_path, width, height, seconds):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("FFmpeg is required for actual full-HD video validation")
    path = tmp_path / "full-hd.mp4"
    subprocess.run(
        [ffmpeg, "-v", "error", "-f", "lavfi", "-i",
         f"color=c=white:s={width}x{height}:r=30:d={seconds}", "-an",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35",
         "-threads", "1", "-pix_fmt", "yuv420p", "-y", str(path)],
        capture_output=True, check=True, timeout=30,
    )
    return path


@pytest.mark.parametrize("width,height,seconds", [(1080, 1920, 5), (1920, 1080, 30)])
def test_supported_full_hd_video_is_completely_decoded(tmp_path, width, height, seconds):
    path = full_hd_video(tmp_path, width, height, seconds)
    assert validate_content(path, "video.mp4", "video/mp4", ["video/mp4"]) == "video/mp4"


def test_video_above_the_decoded_pixel_budget_is_still_rejected(tmp_path):
    path = full_hd_video(tmp_path, 1920, 1080, 35)
    with pytest.raises(HTTPException):
        validate_content(path, "video.mp4", "video/mp4", ["video/mp4"])


def test_empty_oversized_and_broken_stream_cleanup(tmp_path):
    store = LocalStore(tmp_path)

    class Broken:
        def read(self, count):
            raise OSError("TEST_ONLY disk source failure")

    for stream in (io.BytesIO(b""), io.BytesIO(b"x" * 10), Broken()):
        with pytest.raises((HTTPException, OSError)):
            asyncio.run(store.stage(stream, uuid4(), 9))
        assert not [p for p in tmp_path.rglob("*") if p.is_file()]


def test_disk_exhaustion_and_atomic_rename_failure(tmp_path, monkeypatch):
    store = LocalStore(tmp_path)
    monkeypatch.setattr(store, "free_bytes", lambda: 2)
    with pytest.raises(StorageError):
        asyncio.run(store.stage(io.BytesIO(b"abc"), uuid4(), 3))
    monkeypatch.undo()
    staged = asyncio.run(store.stage(io.BytesIO(b"abc"), uuid4(), 3))
    original = os.replace

    def fail_publish(src, dst):
        if str(dst).endswith(".blob"):
            raise OSError("TEST_ONLY publish failure")
        return original(src, dst)

    monkeypatch.setattr(os, "replace", fail_publish)
    with pytest.raises(OSError):
        store.commit(staged)
    assert not list(tmp_path.rglob("*.blob"))
    assert store.staged_path(staged).read_bytes() == b"abc"
    assert len(list(tmp_path.rglob("*.journal"))) == 1
    store.discard(staged)
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]


def test_symlink_and_internal_path_escape(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    store = LocalStore(root)
    for key in ("../outside", str(outside), "a/" + "../" * 3):
        with pytest.raises(HTTPException):
            store.read(key)
    owner = uuid4()
    link = root / owner.hex
    # Windows test host supports junctions without developer-mode symlink privilege.
    if os.name == "nt":
        import subprocess

        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True, check=False
        )
        assert result.returncode == 0
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(HTTPException):
            asyncio.run(store.stage(io.BytesIO(b"abc"), owner, 3))
        assert not list(outside.iterdir())
    finally:
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()


def test_oversized_decoded_image_is_rejected_before_allocation(tmp_path):
    import struct
    import zlib

    path = tmp_path / "huge.png"

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", 100000, 100000, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IEND", b""))
    with pytest.raises(HTTPException):
        validate_content(path, "huge.png", "image/png", ["image/png"])


def test_decoder_timeout_fails_closed(tmp_path, monkeypatch):
    import subprocess

    path = tmp_path / "valid.png"
    path.write_bytes((FIXTURES / "TEST_ONLY-orange.png").read_bytes())

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("TEST_ONLY_decoder", 15)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(HTTPException):
        validate_content(path, "valid.png", "image/png", ["image/png"])
