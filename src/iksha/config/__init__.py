"""
Configuration model for IKSHA.

Sources, highest precedence first:

1. CLI overrides
2. Project-local iksha.config.json
3. Built-in defaults
"""

from .loader import CONFIG_FILENAME, ConfigLoadResult, load_config
from .model import CaseSensitivity, Config

__all__ = [
    "CONFIG_FILENAME",
    "CaseSensitivity",
    "Config",
    "ConfigLoadResult",
    "load_config",
]
