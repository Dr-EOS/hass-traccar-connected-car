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

def apply_modifier(value: Any, modifier: str | None) -> Any:
    """Apply a modifier string (*factor or &mask) to a value."""
    if value is None:
        return None
    
    if not modifier or not isinstance(modifier, str):
        return value
        
    mod = modifier.strip()
    if not mod:
        return value

    try:
        if mod.startswith("*"):
            factor = float(mod[1:])
            return value * factor
        
        if mod.startswith("&"):
            mask_val = parse_int_value(mod[1:])
            if mask_val is not None:
                return value & mask_val
                
    except (ValueError, TypeError) as err:
        _LOGGER.error("Error applying modifier %s to value %s: %s", modifier, value, err)
        
    return value
