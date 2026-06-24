"""Account provision loop for a single GPU host."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from upstream_api_client import UpstreamApiClient
from health_server import HealthState, load_health_bind, start_health_server
from isolation_runner import provision_user, revoke_user
from server_ip import resolve_server_ip

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_ISOLATION_DIR = REPO_ROOT / "isolation"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> dict[str, Any]:
    load_dotenv()

    api_url = os.getenv("UPSTREAM_API_URL", "http://localhost:8080").rstrip("/")
    agent_psk = os.getenv("AGENT_PSK", "").strip()
    if not agent_psk:
        msg = "AGENT_PSK is required"
        raise ValueError(msg)

    server_id = os.getenv("AGENT_SERVER_ID", "").strip()
    if not server_id:
        msg = "AGENT_SERVER_ID is required"
        raise ValueError(msg)

    poll_interval = max(5, int(os.getenv("PROVISION_POLL_INTERVAL", "30")))

    isolation_dir = Path(os.getenv("ISOLATION_DIR", str(DEFAULT_ISOLATION_DIR))).resolve()
    data_root = os.getenv("DATA_ROOT", "/data").strip()
    if not data_root.startswith("/"):
        msg = f"DATA_ROOT must be an absolute path (got: {data_root!r})"
        raise ValueError(msg)

    server_ip_override = os.getenv("PROVISION_SERVER_IP", "").strip() or None
    netbird_bin = os.getenv("NETBIRD_BIN", "netbird").strip() or "netbird"
    use_sudo = _env_bool("PROVISION_USE_SUDO", True)
    dry_run = _env_bool("PROVISION_DRY_RUN", False)

    return {
        "api_url": api_url,
        "agent_psk": agent_psk,
        "server_id": server_id,
        "poll_interval": poll_interval,
        "isolation_dir": isolation_dir,
        "data_root": data_root,
        "server_ip_override": server_ip_override,
        "netbird_bin": netbird_bin,
        "use_sudo": use_sudo,
        "dry_run": dry_run,
    }


def _handle_grant(
    client: UpstreamApiClient,
    config: dict[str, Any],
    task: dict[str, Any],
) -> None:
    server_id = config["server_id"]
    app_id = task["applicationId"]
    linux_username = task["linuxUsername"]
    password = task["password"]

    if config["dry_run"]:
        print(
            f"DRY_RUN grant app={app_id} user={linux_username} "
            f"isolation={config['isolation_dir']}",
            flush=True,
        )
        return

    result = provision_user(
        isolation_dir=config["isolation_dir"],
        data_root=config["data_root"],
        linux_username=linux_username,
        password=password,
        use_sudo=config["use_sudo"],
    )
    if not result.success:
        client.complete_provision(
            application_id=app_id,
            server_id=server_id,
            success=False,
            error_message=result.error_message,
        )
        print(
            f"ERROR provision failed app={app_id} user={linux_username}: {result.error_message}",
            flush=True,
        )
        return

    try:
        server_ip = resolve_server_ip(
            config["server_ip_override"],
            netbird_bin=config["netbird_bin"],
        )
    except RuntimeError as exc:
        client.complete_provision(
            application_id=app_id,
            server_id=server_id,
            success=False,
            error_message=str(exc),
        )
        print(
            f"ERROR provision serverIp resolution failed app={app_id}: {exc}",
            flush=True,
        )
        return

    client.complete_provision(
        application_id=app_id,
        server_id=server_id,
        success=True,
        server_ip=server_ip,
    )
    print(f"INFO provision complete app={app_id} user={linux_username}", flush=True)


def _handle_revoke(client: UpstreamApiClient, config: dict[str, Any], task: dict[str, Any]) -> None:
    server_id = config["server_id"]
    app_id = task["applicationId"]
    linux_username = task["linuxUsername"]

    if config["dry_run"]:
        print(
            f"DRY_RUN revoke app={app_id} user={linux_username} "
            f"isolation={config['isolation_dir']}",
            flush=True,
        )
        return

    result = revoke_user(
        isolation_dir=config["isolation_dir"],
        data_root=config["data_root"],
        linux_username=linux_username,
        use_sudo=config["use_sudo"],
    )
    if result.success:
        client.complete_revoke(
            application_id=app_id,
            server_id=server_id,
            success=True,
        )
        print(f"INFO revoke complete app={app_id} user={linux_username}", flush=True)
        return

    client.complete_revoke(
        application_id=app_id,
        server_id=server_id,
        success=False,
        error_message=result.error_message,
    )
    print(
        f"ERROR revoke failed app={app_id} user={linux_username}: {result.error_message}",
        flush=True,
    )


def poll_once(
    client: UpstreamApiClient,
    config: dict[str, Any],
    health: HealthState | None,
) -> None:
    server_id = config["server_id"]
    try:
        data = client.post_pending(server_id)
    except requests.RequestException as exc:
        msg = f"pending poll failed: {exc}"
        print(f"WARN {msg} for {server_id}", flush=True)
        if health is not None:
            health.record_failure(msg)
        return

    if health is not None:
        health.record_success()

    if not data:
        return

    for grant in data.get("pendingGrants") or []:
        try:
            _handle_grant(client, config, grant)
        except requests.RequestException as exc:
            print(f"ERROR provision complete callback failed: {exc}", flush=True)

    for revoke in data.get("pendingRevokes") or []:
        try:
            _handle_revoke(client, config, revoke)
        except requests.RequestException as exc:
            print(f"ERROR revoke complete callback failed: {exc}", flush=True)


def main() -> None:
    try:
        config = load_config()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    health: HealthState | None = None
    bind = load_health_bind()
    if bind is not None:
        host, port = bind
        health = HealthState(agent="account-provisioner", server_id=config["server_id"])
        start_health_server(health, host, port)

    client = UpstreamApiClient(config["api_url"], config["agent_psk"], config["server_id"])
    print(
        f"account-provisioner polling api={config['api_url']} "
        f"server_id={config['server_id']} interval={config['poll_interval']}s "
        f"isolation={config['isolation_dir']} dry_run={config['dry_run']}",
        flush=True,
    )

    while True:
        poll_once(client, config, health)
        time.sleep(config["poll_interval"])


if __name__ == "__main__":
    main()
