# Shared RGB frame buffer between display child processes and the LEDsim viewer.
"""
Cross-process panel framebuffer for LEDsim.

Why not multiprocessing.SharedMemory?
  Concurrent SharedMemory.buf / memoryview access on Windows repeatedly caused
  0xC0000005 (STATUS_ACCESS_VIOLATION) in the LEDsim *viewer* process under
  high-rate SwapOnVSync (AnalogClock, Style-3 starry clock, games).

Design:
  • Frame lives in a normal temp file: [uint64 counter][RGB24 pixels]
  • Writer: write private .tmp → os.replace onto the frame path
  • Reader: open, read full snapshot, close
  • A named Win32 mutex serializes open/read vs replace so Windows does not
    return ERROR_ACCESS_DENIED (you cannot replace a file that is open without
    FILE_SHARE_DELETE, which Python's open() does not request)

Environment (set by LEDsim.py before starting children):
  LEDARCADE_SIM_FRAME  — path to the frame file (preferred)
  LEDARCADE_SIM_SHM    — legacy alias; also holds the frame path
  LEDARCADE_SIM_WIDTH  — panel width (cols)
  LEDARCADE_SIM_HEIGHT — panel height (rows)
  LEDARCADE_SIM_MUTEX  — named mutex (derived from frame path)
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import Optional, Tuple

# Env keys
SHARED_ENV_FRAME = "LEDARCADE_SIM_FRAME"
SHARED_ENV_NAME = "LEDARCADE_SIM_SHM"  # legacy; stores frame path
SHARED_ENV_WIDTH = "LEDARCADE_SIM_WIDTH"
SHARED_ENV_HEIGHT = "LEDARCADE_SIM_HEIGHT"
SHARED_ENV_MUTEX = "LEDARCADE_SIM_MUTEX"

# Layout: [uint64 frame_counter][width * height * 3 RGB bytes]
HEADER_FMT = "<Q"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

_local_lock = threading.Lock()
_width: int = 64
_height: int = 32
_frame_size: int = 0
_configured: bool = False
_frame_path: Optional[str] = None
_counter: int = 0
_mutex_handle = None
_mutex_warned = False

_WAIT_OBJECT_0 = 0x00000000
_WAIT_ABANDONED = 0x00000080
_MUTEX_WAIT_MS = 1000
_REPLACE_RETRIES = 8


class FrameBufferHandle:
    """Stand-in for SharedMemory so LEDsim cleanup stays simple."""

    def __init__(self, path: str):
        self.name = path
        self.path = path

    def close(self) -> None:
        pass

    def unlink(self) -> None:
        path = self.path
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        try:
            folder = os.path.dirname(path) or "."
            base = os.path.basename(path)
            for name in os.listdir(folder):
                if name.startswith(base) or name.startswith(f".{base}"):
                    if name.endswith(".tmp") or name == base:
                        try:
                            os.remove(os.path.join(folder, name))
                        except Exception:
                            pass
        except Exception:
            pass


def frame_nbytes(width: int, height: int) -> int:
    return HEADER_SIZE + (width * height * 3)


def configure(name: str, width: int, height: int) -> None:
    """Publish frame identity for this process and future children."""
    global _width, _height, _frame_size, _configured, _frame_path
    path = name
    if not os.path.isabs(path) and not os.path.dirname(path):
        path = os.path.join(tempfile.gettempdir(), f"ledsim_{path}.bin")
    _frame_path = path
    os.environ[SHARED_ENV_FRAME] = path
    os.environ[SHARED_ENV_NAME] = path
    os.environ[SHARED_ENV_WIDTH] = str(width)
    os.environ[SHARED_ENV_HEIGHT] = str(height)
    # Mutex name must be a valid Win32 object name (no path separators)
    safe = "".join(ch if ch.isalnum() else "_" for ch in os.path.basename(path))
    mutex_name = f"Local\\ledsim_frame_{safe}"
    os.environ[SHARED_ENV_MUTEX] = mutex_name
    _width = int(width)
    _height = int(height)
    _frame_size = _width * _height * 3
    _configured = True
    _ensure_mutex()


def get_config() -> Tuple[Optional[str], int, int]:
    path = _resolve_path()
    width = int(os.environ.get(SHARED_ENV_WIDTH, "64"))
    height = int(os.environ.get(SHARED_ENV_HEIGHT, "32"))
    return path, width, height


def _resolve_path() -> Optional[str]:
    global _frame_path, _width, _height, _frame_size
    if _frame_path:
        return _frame_path
    path = os.environ.get(SHARED_ENV_FRAME) or os.environ.get(SHARED_ENV_NAME)
    if path:
        _frame_path = path
        _width = int(os.environ.get(SHARED_ENV_WIDTH, "64"))
        _height = int(os.environ.get(SHARED_ENV_HEIGHT, "32"))
        _frame_size = _width * _height * 3
    return path


def _win32_kernel32():
    import ctypes
    from ctypes import wintypes

    k = ctypes.windll.kernel32
    if getattr(k, "_ledsim_file_protos", False):
        return k

    k.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateMutexW.restype = wintypes.HANDLE
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.ReleaseMutex.argtypes = [wintypes.HANDLE]
    k.ReleaseMutex.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    k.GetLastError.argtypes = []
    k.GetLastError.restype = wintypes.DWORD
    k._ledsim_file_protos = True
    return k


def _ensure_mutex():
    global _mutex_handle, _mutex_warned
    if _mutex_handle is not None:
        return _mutex_handle
    if sys.platform != "win32":
        return None
    name = os.environ.get(SHARED_ENV_MUTEX)
    if not name:
        path = _resolve_path()
        if path:
            safe = "".join(ch if ch.isalnum() else "_" for ch in os.path.basename(path))
            name = f"Local\\ledsim_frame_{safe}"
            os.environ[SHARED_ENV_MUTEX] = name
        else:
            return None
    try:
        from ctypes import wintypes

        k = _win32_kernel32()
        handle = k.CreateMutexW(None, False, name)
        if not handle or handle == wintypes.HANDLE(-1).value:
            if not _mutex_warned:
                print(f"[ledsim] CreateMutexW failed err={k.GetLastError()} name={name!r}")
                _mutex_warned = True
            return None
        _mutex_handle = handle
        return handle
    except Exception as exc:
        if not _mutex_warned:
            print(f"[ledsim] mutex create failed: {exc}")
            _mutex_warned = True
        return None


@contextmanager
def _frame_lock():
    """Exclusive access for frame file open/read/write/replace."""
    handle = _ensure_mutex()
    if handle is not None and sys.platform == "win32":
        k = _win32_kernel32()
        rc = k.WaitForSingleObject(handle, _MUTEX_WAIT_MS)
        if rc in (_WAIT_OBJECT_0, _WAIT_ABANDONED):
            try:
                yield True
            finally:
                try:
                    k.ReleaseMutex(handle)
                except Exception:
                    pass
            return
        global _mutex_warned
        if not _mutex_warned:
            print(f"[ledsim] frame mutex wait rc=0x{rc:X} — skipping op")
            _mutex_warned = True
        yield False
        return

    with _local_lock:
        yield True


def create_shared_buffer(width: int, height: int, name: Optional[str] = None):
    """
    Create the frame file (call once from LEDsim launcher).
    Returns (FrameBufferHandle, path, width, height).
    """
    width = int(width)
    height = int(height)
    if name and (os.path.isabs(name) or os.path.dirname(name)):
        path = name
    else:
        token = name or f"{os.getpid()}_{time.time_ns()}"
        path = os.path.join(tempfile.gettempdir(), f"ledsim_frame_{token}.bin")

    configure(path, width, height)
    zeros = b"\x00" * (width * height * 3)
    _write_payload(path, 0, zeros)
    return FrameBufferHandle(path), path, width, height


def _next_counter() -> int:
    global _counter
    with _local_lock:
        _counter = (_counter + 1) & 0xFFFFFFFF
        return ((time.time_ns() & 0xFFFFFFFF00000000) | _counter) & 0xFFFFFFFFFFFFFFFF


def _write_payload(path: str, counter: int, rgb_bytes: bytes) -> None:
    """Atomically write header+pixels under the frame mutex."""
    need = _frame_size or len(rgb_bytes)
    if len(rgb_bytes) < need:
        rgb = rgb_bytes + b"\x00" * (need - len(rgb_bytes))
    else:
        rgb = rgb_bytes[:need]
    payload = struct.pack(HEADER_FMT, int(counter) & 0xFFFFFFFFFFFFFFFF) + rgb

    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)

    with _frame_lock() as acquired:
        if not acquired:
            return
        tmp = os.path.join(
            folder,
            f".{os.path.basename(path)}.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp",
        )
        try:
            with open(tmp, "wb") as f:
                f.write(payload)
                f.flush()
                # Skip fsync: this is a live frame buffer, not durable storage.
                # fsync on every present (~30–60 Hz) made LEDsim feel very slow
                # on Windows; os.replace of a fully-written tmp is enough.
            last_err = None
            for attempt in range(_REPLACE_RETRIES):
                try:
                    os.replace(tmp, path)
                    last_err = None
                    break
                except OSError as exc:
                    last_err = exc
                    # Destination briefly locked — brief backoff
                    time.sleep(0.002 * (attempt + 1))
            if last_err is not None:
                raise last_err
        finally:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass


def publish_frame(rgb_bytes: bytes) -> None:
    path = _resolve_path()
    if not path:
        return
    if _frame_size and len(rgb_bytes) < _frame_size:
        return
    try:
        _write_payload(path, _next_counter(), rgb_bytes)
    except Exception as exc:
        # Keep noise low — one line per failure is enough for diagnosis
        print(f"[ledsim] publish_frame failed: {exc}")


def publish_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
    """
    Immediate single-pixel update (RMW of full frame). Prefer publish_frame /
    SwapOnVSync; rgbmatrix_compat throttles SetPixel so this is rare.
    """
    path = _resolve_path()
    if not path:
        return
    if x < 0 or y < 0 or x >= _width or y >= _height:
        return
    try:
        # Read+write under separate locks is fine; accept possible lost updates
        counter, data = read_frame()
        if counter < 0 or len(data) != _frame_size:
            data = bytearray(_frame_size)
        else:
            data = bytearray(data)
        offset = (y * _width + x) * 3
        data[offset] = int(r) & 0xFF
        data[offset + 1] = int(g) & 0xFF
        data[offset + 2] = int(b) & 0xFF
        _write_payload(path, _next_counter(), bytes(data))
    except Exception:
        pass


def read_frame() -> Tuple[int, bytes]:
    """
    Return (frame_counter, rgb_bytes). Always a private copy.
    On miss / lock fail returns (-1, b"") so the viewer keeps its last frame.
    """
    path = _resolve_path()
    if not path:
        return -1, b""
    need = _frame_size or 64 * 32 * 3
    try:
        with _frame_lock() as acquired:
            if not acquired:
                return -1, b""
            try:
                with open(path, "rb") as f:
                    blob = f.read(HEADER_SIZE + need)
            except FileNotFoundError:
                return -1, b""
    except Exception as exc:
        print(f"[ledsim] read_frame failed: {exc}")
        return -1, b""

    if len(blob) < HEADER_SIZE + need:
        return -1, b""
    counter = struct.unpack_from(HEADER_FMT, blob, 0)[0]
    data = blob[HEADER_SIZE : HEADER_SIZE + need]
    if len(data) != need:
        return -1, b""
    return int(counter), data


def clear_shared() -> None:
    path = _resolve_path()
    if not path:
        return
    try:
        zeros = b"\x00" * (_frame_size or 64 * 32 * 3)
        _write_payload(path, _next_counter(), zeros)
    except Exception:
        pass


def close(unlink: bool = False) -> None:
    global _frame_path, _mutex_handle
    path = _frame_path or _resolve_path()
    if unlink and path:
        try:
            FrameBufferHandle(path).unlink()
        except Exception:
            pass
    _frame_path = None
    if _mutex_handle is not None and sys.platform == "win32":
        try:
            _win32_kernel32().CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None
