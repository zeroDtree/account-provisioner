# account-provisioner

GPU host agent that polls gsad (GPU Server Access Dashboard) for pending account grant/revoke tasks and runs the bundled [isolation](isolation/) shell scripts locally.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Linux host with `sudo` (passwordless for provision user) or run as root
- [NetBird](https://netbird.io/) client installed, connected, and `netbird` in `PATH` (for `serverIp` auto-detection)
- Reachable gsad API (`GSAD_API_URL`)

## Clone

```bash
git clone --recursive git@github.com:zeroDtree/account-provisioner.git
cd account-provisioner
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

## Setup

```bash
uv sync
cp .env.example .env
# Edit .env: GSAD_API_URL, AGENT_PSK, AGENT_HOSTNAME, DATA_ROOT
```

## Run

```bash
uv run python provision_loop.py
```

Dry run (log pending tasks without executing scripts or calling complete):

```bash
PROVISION_DRY_RUN=1 uv run python provision_loop.py
```

## Configuration

| Variable                  | Description                                                        |
| ------------------------- | ------------------------------------------------------------------ |
| `GSAD_API_URL`            | gsad base URL                                                      |
| `AGENT_PSK`               | `X-Agent-PSK` header value                                         |
| `AGENT_HOSTNAME`          | Hostname sent to gsad (default: system hostname)                   |
| `PROVISION_POLL_INTERVAL` | Poll seconds (default `30`, min `5`)                               |
| `ISOLATION_DIR`           | Path to isolation checkout (default `./isolation`)                 |
| `DATA_ROOT`               | Absolute path passed to `add-user.sh` / `remove-user.sh`           |
| `PROVISION_SERVER_IP`     | IP reported on successful grant (default: `netbird status --ipv4`) |
| `NETBIRD_BIN`             | NetBird CLI path (default `netbird`)                               |
| `PROVISION_USE_SUDO`      | Use `sudo -n` when not root (default `1`)                          |
| `PROVISION_DRY_RUN`       | Log only, no exec or complete callbacks                            |
| `AGENT_HEALTH_HOST`       | Health bind address (default `127.0.0.1`)                          |
| `AGENT_HEALTH_PORT`       | Health HTTP port (default `9091`; `0` disables)                    |

## Flow

1. `POST /api/internal/servers/provision/pending` with `{ "hostname": "..." }` — see [provision/pending](docs/api_data_formats.md#post-apiinternalserversprovisionpending)
2. For each `pendingGrants[]` entry: `isolation/add-user.sh <linuxUsername> --password <password>`
3. `POST /api/internal/servers/provision/complete` — see [provision/complete](docs/api_data_formats.md#post-apiinternalserversprovisioncomplete)
4. For each `pendingRevokes[]` entry: `isolation/remove-user.sh <linuxUsername> --ignore-missing`
5. `POST /api/internal/servers/revoke/complete` — see [revoke/complete](docs/api_data_formats.md#post-apiinternalserversrevokecomplete)

Usernames and passwords come from gsad; the provisioner must not generate them.

See [docs/api_data_formats.md](docs/api_data_formats.md) for request/response JSON schemas.

## Quality checks

```bash
uv run ruff check
uv run ty check
```
