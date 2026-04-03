"""Configuration loader for NerdMC."""

import os
import yaml


DEFAULT_CONFIG: dict = {
    "discord": {
        "token": "",
        "channel_id": None,
        "command_prefix": "!",
    },
    "rcon": {
        "host": "localhost",
        "port": 25575,
        "password": "",
    },
    "minecraft": {
        "log_path": "/home/minecraft/logs/latest.log",
    },
    "antispam": {
        "enabled": True,
        "max_messages": 5,
        "window_seconds": 10,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str = "config.yml") -> dict:
    """Load configuration from *path*, falling back to defaults for missing keys.

    Raises ``FileNotFoundError`` if *path* does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Configuration file '{path}' not found. "
            "Copy 'config.yml.example' to 'config.yml' and fill in your values."
        )
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return _deep_merge(DEFAULT_CONFIG, raw)
