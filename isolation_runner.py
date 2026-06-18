"""Execute isolation add-user.sh / remove-user.sh via subprocess."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunResult:
    success: bool
    error_message: str | None = None


def _tail_message(stdout: str, stderr: str, *, max_len: int = 500) -> str:
    for text in (stderr.strip(), stdout.strip()):
        if text:
            lines = [line for line in text.splitlines() if line.strip()]
            if lines:
                msg = lines[-1]
                return msg if len(msg) <= max_len else msg[: max_len - 3] + "..."
    return "isolation script failed"


def _build_command(script: Path, args: list[str], *, use_sudo: bool) -> list[str]:
    cmd = [str(script), *args]
    if use_sudo and os.geteuid() != 0:
        return ["sudo", "-n", *cmd]
    return cmd


def provision_user(
    *,
    isolation_dir: Path,
    data_root: str,
    linux_username: str,
    password: str,
    use_sudo: bool,
    timeout: float = 600.0,
) -> RunResult:
    script = isolation_dir / "add-user.sh"
    if not script.is_file():
        return RunResult(False, f"missing script: {script}")

    env = os.environ.copy()
    env["DATA_ROOT"] = data_root
    cmd = _build_command(
        script,
        [linux_username, "--password", password],
        use_sudo=use_sudo,
    )
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    if proc.returncode == 0:
        return RunResult(True)
    return RunResult(False, _tail_message(proc.stdout, proc.stderr))


def revoke_user(
    *,
    isolation_dir: Path,
    data_root: str,
    linux_username: str,
    use_sudo: bool,
    timeout: float = 300.0,
) -> RunResult:
    script = isolation_dir / "remove-user.sh"
    if not script.is_file():
        return RunResult(False, f"missing script: {script}")

    env = os.environ.copy()
    env["DATA_ROOT"] = data_root
    cmd = _build_command(
        script,
        [linux_username, "--ignore-missing"],
        use_sudo=use_sudo,
    )
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    if proc.returncode == 0:
        return RunResult(True)
    return RunResult(False, _tail_message(proc.stdout, proc.stderr))
