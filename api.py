"""FMC130 Traccar API Client.

Generated with ha-integration@aurora-smart-home v1.0.0
https://github.com/tonylofgren/aurora-smart-home
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import aiohttp


class TraccarApiError(Exception):
    """Exception to indicate a Traccar API error."""


class TraccarClient:
    """Client for interacting with Traccar API."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = True,
        token: str | None = None,
        session: aiohttp.ClientSession | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the client."""
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._token = token
        self._session = session
        self._verify_ssl = verify_ssl

    @property
    def base_url(self) -> str:
        """Return the base URL for the API."""
        scheme = "https" if self._use_ssl else "http"
        return f"{scheme}://{self._host}:{self._port}/api"

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make a request to the API."""
        if self._session is None:
             raise TraccarApiError("ClientSession is not initialized")

        url = f"{self.base_url}{path}"

        headers = kwargs.pop("headers", {})
        auth = None

        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif self._username and self._password:
            auth = aiohttp.BasicAuth(self._username, self._password)

        logger = logging.getLogger(__name__)
        logger.debug(
            "Requesting %s %s with %s",
            method,
            url,
            kwargs.get("json", kwargs.get("params")),
        )

        try:
            async with asyncio.timeout(10):
                async with self._session.request(
                    method,
                    url,
                    auth=auth,
                    headers=headers,
                    ssl=self._verify_ssl,
                    **kwargs,
                ) as resp:
                    if resp.status >= 400:
                        await self._handle_error(resp, logger, method, url)
                    return await resp.json()
        except TimeoutError as err:
            raise TraccarApiError("Timeout connecting to Traccar") from err
        except aiohttp.ClientError as err:
            raise TraccarApiError(f"Connection error: {err}") from err
        except Exception as err:
            raise TraccarApiError(f"Unexpected error: {err}") from err

    async def _handle_error(self, resp, logger, method, url) -> None:
        """Handle error response."""
        text = await resp.text()
        logger.error("Error from Traccar: %s %s - %s", method, url, text)
        raise TraccarApiError(f"HTTP {resp.status}: {text}")

    async def get_devices(self) -> Any:
        """Fetch all devices."""
        return await self._request("GET", "/devices")

    async def get_positions(self) -> Any:
        """Fetch all positions."""
        return await self._request("GET", "/positions")

    async def send_command(self, device_id: int | str, command: dict[str, Any]) -> Any:
        """Send a command to a device."""
        with contextlib.suppress(ValueError, TypeError):
            device_id = int(device_id)
        payload = {"deviceId": device_id, **command}
        return await self._request("POST", "/commands/send", json=payload)
