"""Isolated untrusted media decoder. No application DB/network configuration is used."""

import ctypes
import json
import os
import sys
from pathlib import Path


def restrict_resources():
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
        return None
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("ProcessTime", ctypes.c_int64),
            ("JobTime", ctypes.c_int64),
            ("Flags", wintypes.DWORD),
            ("MinWorkingSet", ctypes.c_size_t),
            ("MaxWorkingSet", ctypes.c_size_t),
            ("ActiveProcesses", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("Priority", wintypes.DWORD),
            ("Scheduling", wintypes.DWORD),
        ]

    class IOCounts(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_uint64)
            for name in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("Basic", BasicLimits),
            ("IO", IOCounts),
            ("ProcessMemory", ctypes.c_size_t),
            ("JobMemory", ctypes.c_size_t),
            ("PeakProcess", ctypes.c_size_t),
            ("PeakJob", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    job = kernel.CreateJobObjectW(None, None)
    limits = ExtendedLimits()
    limits.Basic.Flags = 0x100 | 0x2  # PROCESS_MEMORY | PROCESS_TIME
    limits.Basic.ProcessTime = 12 * 10_000_000
    limits.ProcessMemory = 768 * 1024 * 1024
    if (
        not job
        or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
        or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess())
    ):
        raise RuntimeError("Decoder resource boundary unavailable")
    return job  # Keep the handle alive for the lifetime of this process.


def main():
    _job = restrict_resources()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.storage.validation import decode_content

    payload = json.loads(sys.stdin.read())
    mime = decode_content(
        Path(payload["path"]), payload["name"], payload["mime"], payload["allowed"]
    )
    sys.stdout.write(mime)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Never return decoder paths, media metadata, native-library logs or exception text.
        raise SystemExit(1) from None
