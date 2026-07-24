# ledsim — software LED matrix backend for Windows / desktop development
"""
LEDsim provides an rgbmatrix-compatible software display so LEDcommander and
LEDarcade can run without Raspberry Pi GPIO hardware.

Set environment variable LEDARCADE_DISPLAY=sim before importing LEDarcade.
Shared frame presentation is configured via ledsim.shared.configure(...).
"""

from .shared import (
    SHARED_ENV_NAME,
    SHARED_ENV_WIDTH,
    SHARED_ENV_HEIGHT,
    configure,
    get_config,
)

__all__ = [
    "SHARED_ENV_NAME",
    "SHARED_ENV_WIDTH",
    "SHARED_ENV_HEIGHT",
    "configure",
    "get_config",
]
