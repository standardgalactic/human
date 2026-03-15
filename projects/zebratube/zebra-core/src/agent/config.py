#!/usr/bin/env python3
"""
agent/config.py — persistent agent configuration

Stored at ~/.zebra/agent.yaml (or XDG_CONFIG_HOME/zebra/agent.yaml).
Created with sensible defaults on first run.
"""

import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "url":   "http://localhost:8000/api",
        "token": None,
    },
    "agent": {
        "mode":           "suggest",    # "suggest" | "auto"
        "poll_interval":  300,          # seconds between task fetches
        "max_claims":     3,            # max simultaneous active claims
        "auto_claim_min_score": 0.6,    # auto-claim threshold in auto mode
    },
    "scan": {
        "directories": [
            "~/Documents",
            "~/Projects",
            "~/repos",
            "~/code",
            "~/notes",
        ],
        "enabled":    True,
        "cache_ttl":  3600,             # seconds before re-scanning
    },
    "filters": {
        "projection_types": [],         # empty = all
        "min_bounty":       0,
        "max_difficulty":   "complex",
        "status":           "open",
    },
    "identity": {
        "username": None,
        "node_name": None,              # defaults to hostname
    },
}


def config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        base = Path(xdg)
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", "~")).expanduser()
    else:
        base = Path("~/.config").expanduser()
    return base / "zebra" / "agent.yaml"


def load() -> dict:
    """Load config from disk, merging with defaults."""
    path = config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        import yaml  # type: ignore
        with open(path) as f:
            user = yaml.safe_load(f) or {}
        return _deep_merge(dict(DEFAULT_CONFIG), user)
    except ImportError:
        # Fall back to JSON if PyYAML not available
        import json
        try:
            return _deep_merge(dict(DEFAULT_CONFIG),
                               json.loads(path.with_suffix(".json").read_text()))
        except Exception:
            return dict(DEFAULT_CONFIG)


def save(cfg: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        with open(path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    except ImportError:
        import json
        path.with_suffix(".json").write_text(
            json.dumps(cfg, indent=2), encoding="utf-8"
        )


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def init_config(server_url: str, username: str | None = None,
                token: str | None = None) -> dict:
    """Create or update config with server URL and credentials."""
    cfg = load()
    cfg["server"]["url"]   = server_url
    cfg["server"]["token"] = token
    if username:
        cfg["identity"]["username"] = username
    import socket
    cfg["identity"]["node_name"] = socket.gethostname()
    save(cfg)
    return cfg
