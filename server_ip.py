"""Resolve the host IPv4 reported to the API on successful provision."""

from __future__ import annotations

import ipaddress
import os
import subprocess
from pathlib import Path

DEFAULT_IPV4_SCRIPT = Path(__file__).resolve().parent / "hooks" / "ipv4.sh"
_SCRIPT_TIMEOUT_SECONDS = 10


def require_ipv4(raw: str) -> str:
    text = raw.strip()
    if not text:
        msg = "IPv4 callback produced empty output"
        raise RuntimeError(msg)
    try:
        addr = ipaddress.ip_address(text)
    except ValueError as exc:
        msg = f"IPv4 callback output is not a valid IP: {text!r}"
        raise RuntimeError(msg) from exc
    if addr.version != 4:
        msg = f"IPv4 callback output is not IPv4: {text!r}"
        raise RuntimeError(msg)
    return str(addr)


def resolve_server_ip(script: Path) -> str:
    path = script.expanduser()
    if not path.is_file():
        msg = f"IPv4 callback script not found: {path}"
        raise RuntimeError(msg)
    if not os.access(path, os.X_OK):
        msg = f"IPv4 callback script is not executable: {path}"
        raise RuntimeError(msg)

    try:
        proc = subprocess.run(
            [str(path)],
            capture_output=True,
            text=True,
            timeout=_SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"IPv4 callback timed out after {_SCRIPT_TIMEOUT_SECONDS}s: {path}"
        raise RuntimeError(msg) from exc
    except OSError as exc:
        msg = f"IPv4 callback failed to start: {path}: {exc}"
        raise RuntimeError(msg) from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        msg = f"IPv4 callback exited {proc.returncode}: {detail}"
        raise RuntimeError(msg)

    return require_ipv4(proc.stdout)
