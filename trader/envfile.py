"""Load a local .env file into the process environment.

Existing process variables win. Values are never logged. This is not a
substitute for OS secrets management and must not be committed with keys.
"""
from __future__ import annotations

import os
from typing import MutableMapping


def default_env_paths() -> tuple[str, ...]:
    cwd = os.path.join(os.getcwd(), ".env")
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.normcase(cwd) == os.path.normcase(root):
        return (cwd,)
    return (cwd, root)


def parse_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if key:
                values[key] = value
    return values


def load_env_file(
    path: str | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> str | None:
    """Fill empty keys from the first readable .env. Return the path loaded."""
    env: MutableMapping[str, str] = os.environ if environ is None else environ
    candidates = (path,) if path else default_env_paths()
    for candidate in candidates:
        if not candidate or not os.path.isfile(candidate):
            continue
        parsed = parse_env_file(candidate)
        for key, value in parsed.items():
            if not str(env.get(key, "")).strip():
                env[key] = value
        return candidate
    return None


def load_os_env_file() -> str | None:
    """Load `.env` into ``os.environ`` when the caller did not pass a mapping."""
    return load_env_file()
