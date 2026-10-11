"""Validate decoded content, never trust client extensions, MIME or lengths."""

import json
import os
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path

import av
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

TYPES = {
    "PNG": ("image/png", {".png"}),
    "JPEG": ("image/jpeg", {".jpg", ".jpeg"}),
    "WEBP": ("image/webp", {".webp"}),
    "MP4": ("video/mp4", {".mp4"}),
}


class FileValidationError(HTTPException):
    def __init__(self, reason="format"):
        self.public_message = {
            "name": "文件名不能包含路径、控制字符或保留符号。",
            "size": "文件内容超过当前允许的大小。",
            "empty": "不能上传空文件。",
            "format": "文件格式不支持、内容损坏、与声明类型不符或超过安全解码限制。",
        }[reason]
        super().__init__(422)


def validate_name(name):
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 200
        or name != name.strip()
        or name in (".", "..")
        or re.search(r'[\x00-\x1f\x7f/\\:<>"|?*]', name)
        or name.endswith(".")
        or Path(name).is_absolute()
    ):
        raise FileValidationError("name")
    return name


def decode_content(path, display_name, declared_mime, allowed_types):
    validate_name(display_name)
    try:
        with path.open("rb") as source:
            head = source.read(16)
        if len(head) >= 12 and head[4:8] == b"ftyp":
            # Require a complete ISO-BMFF container, not a truncated signature.
            size, position = path.stat().st_size, 0
            with path.open("rb") as source:
                boxes = set()
                while position < size:
                    source.seek(position)
                    header = source.read(8)
                    if len(header) != 8:
                        raise ValueError()
                    length, kind = int.from_bytes(header[:4], "big"), header[4:]
                    minimum = 8
                    if length == 1:
                        extra = source.read(8)
                        if len(extra) != 8:
                            raise ValueError()
                        length, minimum = int.from_bytes(extra, "big"), 16
                    if length == 0:
                        length = size - position
                    if length < minimum or position + length > size:
                        raise ValueError()
                    boxes.add(kind)
                    position += length
                if not {b"ftyp", b"moov", b"mdat"} <= boxes:
                    raise ValueError()
            frames, total_pixels = 0, 0
            deadline = time.monotonic() + 10
            # Force local MOV demuxer; never enable external data references or protocols.
            with av.open(
                str(path),
                format="mov",
                options={
                    "enable_drefs": "0",
                    "use_absolute_path": "0",
                    "protocol_whitelist": "file",
                    "err_detect": "explode",
                },
            ) as container:
                if not container.streams.video or len(container.streams) > 4:
                    raise ValueError()
                for video in container.streams.video:
                    codec = video.codec_context
                    if not 0 < codec.width * codec.height <= 40_000_000:
                        raise ValueError()
                    codec.thread_count = 1
                    codec.options = {"max_pixels": "40000000"}
                for packet in container.demux():
                    if time.monotonic() > deadline:
                        raise ValueError()
                    for frame in packet.decode():
                        frames += 1
                        total_pixels += getattr(frame, "width", 0) * getattr(frame, "height", 0)
                        if total_pixels > 200_000_000:
                            raise ValueError()
                        # Decoder resource guard, independent from configurable business bytes.
                        if frames > 36000 or (
                            getattr(frame, "width", 0) * getattr(frame, "height", 0) > 40_000_000
                        ):
                            raise ValueError()
            if not frames:
                raise ValueError()
            kind = "MP4"
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as decoded:
                    kind = decoded.format
                    if kind not in TYPES or decoded.width * decoded.height > 40_000_000:
                        raise ValueError()
                    decoded.verify()
                with Image.open(path) as decoded:
                    if (
                        decoded.width * decoded.height * getattr(decoded, "n_frames", 1)
                        > 200_000_000
                    ):
                        raise ValueError()
                    for frame in range(getattr(decoded, "n_frames", 1)):
                        if frame >= 1000:
                            raise ValueError()
                        decoded.seek(frame)
                        decoded.load()
        mime, extensions = TYPES[kind]
        if (
            mime not in allowed_types
            or declared_mime != mime
            or Path(display_name).suffix.lower() not in extensions
        ):
            raise ValueError()
        return mime
    except (
        ValueError,
        OSError,
        SyntaxError,
        KeyError,
        av.FFmpegError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise FileValidationError() from None


def validate_content(path, display_name, declared_mime, allowed_types):
    """Full decoding in a bounded child, protecting the API process from native decoders."""
    validate_name(display_name)
    payload = json.dumps(
        {"path": str(path), "name": display_name, "mime": declared_mime, "allowed": allowed_types}
    )
    # Keep only OS/runtime essentials; application credentials are not inherited.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH"}
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("_decoder.py"))],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=False,
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        mime = result.stdout.strip()
        if result.returncode != 0 or mime not in allowed_types:
            raise FileValidationError()
        return mime
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        raise FileValidationError() from None
