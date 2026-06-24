"""Upstream API client for account provision."""

from __future__ import annotations

from typing import Any

import requests


class UpstreamApiClient:
    def __init__(
            self,
            api_url: str,
            agent_psk: str,
            server_id: str,
            *,
            timeout: float = 30.0) -> None:
        self._api_url = api_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "X-Agent-PSK": agent_psk,
            "X-Agent-Server-Id": server_id,
        }
        self._timeout = timeout
        self._session = requests.Session()

    def post_pending(self, server_id: str) -> dict[str, Any] | None:
        url = f"{self._api_url}/api/internal/servers/provision/pending"
        resp = self._session.post(
            url,
            json={"serverId": server_id},
            headers=self._headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data")
        if data is None:
            return None
        if not isinstance(data, dict):
            msg = f"unexpected pending response data type: {type(data).__name__}"
            raise TypeError(msg)
        return data

    def complete_provision(
        self,
        *,
        application_id: str,
        server_id: str,
        success: bool,
        server_ip: str | None = None,
        error_message: str | None = None,
    ) -> None:
        url = f"{self._api_url}/api/internal/servers/provision/complete"
        body = {
            "applicationId": application_id,
            "serverId": server_id,
            "success": success,
            "serverIp": server_ip,
            "errorMessage": error_message,
        }
        resp = self._session.post(url, json=body, headers=self._headers, timeout=self._timeout)
        resp.raise_for_status()

    def complete_revoke(
        self,
        *,
        application_id: str,
        server_id: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        url = f"{self._api_url}/api/internal/servers/revoke/complete"
        body = {
            "applicationId": application_id,
            "serverId": server_id,
            "success": success,
            "errorMessage": error_message,
        }
        resp = self._session.post(url, json=body, headers=self._headers, timeout=self._timeout)
        resp.raise_for_status()
