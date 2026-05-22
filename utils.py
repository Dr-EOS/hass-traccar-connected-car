"""Utilities for Teltonika FMC130 integration."""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

def parse_int_value(value: Any) -> int | None:
    """Parse a value that could be int, hex string or binary string."""
    if value is None or value == "":
        return None
    
    if isinstance(value, int):
        return value
        
    str_val = str(value).strip().lower()
    
    try:
        if str_val.startswith("0x"):
            return int(str_val, 16)
        if str_val.startswith("0b"):
            return int(str_val, 2)
        return int(str_val)
    except (ValueError, TypeError):
        _LOGGER.error("Failed to parse integer value: %s", value)
        return None
