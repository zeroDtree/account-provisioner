# API data formats

All gsad internal routes use **camelCase** JSON. Full backend contract: [backend/gsad/agent-provision.md](../../../backend/gsad/agent-provision.md).

## Authentication

Every gsad request:

| Header         | Value              |
| -------------- | ------------------ |
| `Content-Type` | `application/json` |
| `X-Agent-PSK`  | `<AGENT_PSK>`      |

## Response envelope

gsad wraps payloads in `ApiResponse`:

```json
{
  "code": "",
  "message": "ok",
  "data": { ... }
}
```

The agent reads the `data` field. When `data` is `null`, there are no pending tasks.

## `POST /api/internal/servers/provision/pending`

Poll pending grant/revoke tasks for this host.

**Request body:**

| Field      | Required | Description                                                |
| ---------- | -------- | ---------------------------------------------------------- |
| `hostname` | yes      | Same value as `AGENT_HOSTNAME`; used in complete callbacks |

**Response `data`:**

| Field            | Description                     |
| ---------------- | ------------------------------- |
| `pendingGrants`  | Array of account-creation tasks |
| `pendingRevokes` | Array of account-removal tasks  |

**`pendingGrants[]` fields:**

| Field           | Used by agent | Description                                                   |
| --------------- | ------------- | ------------------------------------------------------------- |
| `applicationId` | yes           | Passed to `provision/complete`                                |
| `linuxUsername` | yes           | Passed to `add-user.sh`                                       |
| `password`      | yes           | Passed to `add-user.sh` (gsad-supplied; agent must not alter) |
| `email`         | no            | Context only                                                  |
| `serverId`      | no            | Derived from hostname (strip trailing `.internal`)            |
| `resourceLevel` | no            | Resource tier label                                           |

**`pendingRevokes[]` fields:**

| Field           | Used by agent | Description                 |
| --------------- | ------------- | --------------------------- |
| `applicationId` | yes           | Passed to `revoke/complete` |
| `linuxUsername` | yes           | Passed to `remove-user.sh`  |

Example `data`:

```json
{
  "pendingGrants": [
    {
      "applicationId": "app-abc12345",
      "email": "user@example.com",
      "serverId": "gpu-mock-004",
      "resourceLevel": "H100",
      "linuxUsername": "user",
      "password": "gsad-supplied-secret"
    }
  ],
  "pendingRevokes": [
    {
      "applicationId": "app-def67890",
      "linuxUsername": "user"
    }
  ]
}
```

## `POST /api/internal/servers/provision/complete`

Report account-creation result. **Do not** send `linuxUsername` or `password` — gsad already stored them.

**Request body:**

| Field           | Required   | Description                           |
| --------------- | ---------- | ------------------------------------- |
| `applicationId` | yes        | From the pending grant task           |
| `hostname`      | yes        | Same value as `AGENT_HOSTNAME`        |
| `success`       | yes        | `true` when `add-user.sh` succeeded   |
| `serverIp`      | on success | NetBird IPv4 or `PROVISION_SERVER_IP` |
| `errorMessage`  | on failure | Script or IP-resolution error text    |

Success:

```json
{
  "applicationId": "app-abc12345",
  "hostname": "gpu-mock-004.internal",
  "success": true,
  "serverIp": "10.0.1.5",
  "errorMessage": null
}
```

Failure:

```json
{
  "applicationId": "app-abc12345",
  "hostname": "gpu-mock-004.internal",
  "success": false,
  "serverIp": null,
  "errorMessage": "isolation script failed: ..."
}
```

## `POST /api/internal/servers/revoke/complete`

Report account-removal result.

**Request body:**

| Field           | Required   | Description                            |
| --------------- | ---------- | -------------------------------------- |
| `applicationId` | yes        | From the pending revoke task           |
| `hostname`      | yes        | Same value as `AGENT_HOSTNAME`         |
| `success`       | yes        | `true` when `remove-user.sh` succeeded |
| `errorMessage`  | on failure | Script error text                      |

Success:

```json
{
  "applicationId": "app-def67890",
  "hostname": "gpu-mock-004.internal",
  "success": true,
  "errorMessage": null
}
```

Failure:

```json
{
  "applicationId": "app-def67890",
  "hostname": "gpu-mock-004.internal",
  "success": false,
  "errorMessage": "isolation script failed: ..."
}
```

## `GET /health`

Local health endpoint (default `http://127.0.0.1:9091/health`). Set `AGENT_HEALTH_PORT=0` to disable.

| Field        | Description                                       |
| ------------ | ------------------------------------------------- |
| `ok`         | Overall health (`false` after a failed gsad poll) |
| `agent`      | Always `"account-provisioner"`                    |
| `hostname`   | Configured `AGENT_HOSTNAME`                       |
| `lastPollAt` | UTC ISO-8601 timestamp of last poll attempt       |
| `lastPollOk` | Whether the last poll succeeded                   |
| `lastError`  | Poll error message, or `null`                     |

Example:

```json
{
  "ok": true,
  "agent": "account-provisioner",
  "hostname": "gpu-node-01.internal",
  "lastPollAt": "2026-06-18T12:00:00+00:00",
  "lastPollOk": true,
  "lastError": null
}
```
