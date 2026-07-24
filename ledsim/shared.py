# Shared RGB frame buffer between display child processes and the LEDsim viewer.
"""
Uses multiprocessing.shared_memory so Windows spawn children and the viewer
process can share one panel framebuffer without owning a GUI in each child.

Environment (set by LEDsim.py before starting children):
  LEDARCADE_SIM_SHM   — SharedMemory name
  LEDARCADE_SIM_WIDTH — panel width (cols)
  LEDARCADE_SIM_HEIGHT — panel height (rows)
"""

from __future__ import annotations

import os
import struct
import threading
from multiprocessing import shared_memory
from typing import Optional, Tuple

# Env keys
SHARED_ENV_NAME = "LEDARCADE_SIM_SHM"
SHARED_ENV_WIDTH = "LEDARCADE_SIM_WIDTH"
SHARED_ENV_HEIGHT = "LEDARCADE_SIM_HEIGHT"

# Layout: [uint64 frame_counter][width * height * 3 RGB bytes]
HEADER_FMT = "<Q"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

_lock = threading.Lock()
_shm: Optional[shared_memory.SharedMemory] = None
_width: int = 64
_height: int = 32
_frame_size: int = 0
_configured: bool = False


def frame_nbytes(width: int, height: int) -> int:
    return HEADER_SIZE + (width * height * 3)


def configure(name: str, width: int, height: int) -> None:
    """Publish shared-memory identity for this process and future children."""
    os.environ[SHARED_ENV_NAME] = name
    os.environ[SHARED_ENV_WIDTH] = str(width)
    os.environ[SHARED_ENV_HEIGHT] = str(height)
    global _width, _height, _frame_size, _configured
    _width = int(width)
    _height = int(height)
    _frame_size = _width * _height * 3
    _configured = True


def get_config() -> Tuple[Optional[str], int, int]:
    name = os.environ.get(SHARED_ENV_NAME)
    width = int(os.environ.get(SHARED_ENV_WIDTH, "64"))
    height = int(os.environ.get(SHARED_ENV_HEIGHT, "32"))
    return name, width, height


def _attach() -> Optional[shared_memory.SharedMemory]:
    global _shm, _width, _height, _frame_size, _configured
    if _shm is not None:
        return _shm
    name = os.environ.get(SHARED_ENV_NAME)
    if not name:
        return None
    _width = int(os.environ.get(SHARED_ENV_WIDTH, "64"))
    _height = int(os.environ.get(SHARED_ENV_HEIGHT, "32"))
    _frame_size = _width * _height * 3
    try:
        _shm = shared_memory.SharedMemory(name=name)
        _configured = True
        return _shm
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"[ledsim] Failed to attach shared memory '{name}': {exc}")
        return None


def create_shared_buffer(width: int, height: int, name: Optional[str] = None):
    """
    Create the shared memory block (call once from LEDsim launcher).
    Returns (SharedMemory, name, width, height).
    """
    size = frame_nbytes(width, height)
    shm = shared_memory.SharedMemory(create=True, size=size, name=name)
    # Zero-initialize
    shm.buf[:size] = b"\x00" * size
    configure(shm.name, width, height)
    global _shm, _width, _height, _frame_size
    _shm = shm
    _width = width
    _height = height
    _frame_size = width * height * 3
    return shm, shm.name, width, height


def publish_frame(rgb_bytes: bytes) -> None:
    """Copy a full RGB24 frame into shared memory and bump the frame counter."""
    shm = _attach()
    if shm is None:
        return
    if len(rgb_bytes) < _frame_size:
        return
    with _lock:
        # Increment counter
        counter = struct.unpack_from(HEADER_FMT, shm.buf, 0)[0]
        counter = (counter + 1) & 0xFFFFFFFFFFFFFFFF
        struct.pack_into(HEADER_FMT, shm.buf, 0, counter)
        shm.buf[HEADER_SIZE : HEADER_SIZE + _frame_size] = rgb_bytes[:_frame_size]


def publish_pixel(x: int, y: int, r: int, g: int, b: int) -> None:
    """Write one pixel into the shared front buffer (immediate SetPixel path)."""
    shm = _attach()
    if shm is None:
        return
    if x < 0 or y < 0 or x >= _width or y >= _height:
        return
    offset = HEADER_SIZE + (y * _width + x) * 3
    with _lock:
        shm.buf[offset] = int(r) & 0xFF
        shm.buf[offset + 1] = int(g) & 0xFF
        shm.buf[offset + 2] = int(b) & 0xFF
        counter = struct.unpack_from(HEADER_FMT, shm.buf, 0)[0]
        counter = (counter + 1) & 0xFFFFFFFFFFFFFFFF
        struct.pack_into(HEADER_FMT, shm.buf, 0, counter)


def read_frame() -> Tuple[int, bytes]:
    """Return (frame_counter, rgb_bytes) for the viewer."""
    shm = _attach()
    if shm is None:
        return 0, bytes(_frame_size or 64 * 32 * 3)
    with _lock:
        counter = struct.unpack_from(HEADER_FMT, shm.buf, 0)[0]
        data = bytes(shm.buf[HEADER_SIZE : HEADER_SIZE + _frame_size])
    return counter, data


def clear_shared() -> None:
    shm = _attach()
    if shm is None:
        return
    with _lock:
        shm.buf[HEADER_SIZE : HEADER_SIZE + _frame_size] = b"\x00" * _frame_size
        counter = struct.unpack_from(HEADER_FMT, shm.buf, 0)[0]
        counter = (counter + 1) & 0xFFFFFFFFFFFFFFFF
        struct.pack_into(HEADER_FMT, shm.buf, 0, counter)


def close(unlink: bool = False) -> None:
    global _shm
    if _shm is None:
        return
    name = _shm.name
    try:
        _shm.close()
    except Exception:
        pass
    if unlink:
        try:
            shared_memory.SharedMemory(name=name).unlink()
        except Exception:
            try:
                _shm.unlink()
            except Exception:
                pass
    _shm = None
