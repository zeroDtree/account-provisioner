"""Detect the host IP reported to gsad on successful provision."""

from __future__ import annotations

import ipaddress
import subprocess


def detect_netbird_ipv4(netbird_bin: str = "netbird") -> str | None:
    """Return NetBird mesh IPv4 from `netbird status --ipv4`, or None on failure."""
    try:
        proc = subprocess.run(
            [netbird_bin, "status", "--ipv4"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None

    if proc.returncode != 0:
        return None

    raw = proc.stdout.strip()
    if not raw:
        return None

    try:
        addr = ipaddress.ip_address(raw)
    except ValueError:
        return None

    if addr.version != 4:
        return None
    return str(addr)


def resolve_server_ip(configured: str | None, *, netbird_bin: str = "netbird") -> str:
    if configured and configured.strip():
        return configured.strip()

    detected = detect_netbird_ipv4(netbird_bin)
    if detected:
        return detected

    msg = "PROVISION_SERVER_IP is unset and netbird status --ipv4 failed"
    raise RuntimeError(msg)
