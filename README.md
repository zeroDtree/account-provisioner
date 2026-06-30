# account-provisioner

Polls the upstream API for pending grant/revoke tasks and runs [isolation](isolation/) shell scripts.

## Run

```bash
uv sync && cp .env.example .env
uv run python provision_loop.py
```

Dry run: `PROVISION_DRY_RUN=1 uv run python provision_loop.py`

Required env: `AGENT_SERVER_ID`, `AGENT_PSK`, `UPSTREAM_API_URL`. See [.env.example](.env.example) for all options.

## Upstream API

All routes need `Content-Type: application/json`, `X-Agent-Server-Id: <AGENT_SERVER_ID>`, and `X-Agent-PSK: <AGENT_PSK>`.

**Credentials:** the API supplies `linuxUsername` + `password`; this agent must not alter them. Sends `serverIp` on grant complete.

### Flow

1. `POST /api/internal/servers/provision/pending` — `{ "serverId": "<AGENT_SERVER_ID>" }`
2. For each grant: `isolation/add-user.sh <linuxUsername> --password <password> --with-install-miniconda|--no-install-miniconda --with-install-rootless-docker` (`installMiniconda` from pending grant; Miniconda install requires outbound network; rootless Docker prep configures subuid/subgid, linger, and shell env)
3. `POST /api/internal/servers/provision/complete`
4. For each revoke: `isolation/remove-user.sh <linuxUsername> --ignore-missing`
5. `POST /api/internal/servers/revoke/complete`

### Callbacks

Grant complete (no username/password in body):

```json
{
  "applicationId": "app-abc12345",
  "serverId": "gpu-node-01",
  "success": true,
  "serverIp": "10.0.1.5",
  "errorMessage": null
}
```

Revoke complete:

```json
{
  "applicationId": "app-def67890",
  "serverId": "gpu-node-01",
  "success": true,
  "errorMessage": null
}
```

### Health

Default `http://127.0.0.1:9091/health` — includes `serverId`, `lastPollOk`, `lastError`.
