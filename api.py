import asyncio
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
            # Fallback for unexpected usage outside of HA managed session
            # This should ideally not be reached in production HA code
            self._session = aiohttp.ClientSession()

        url = f"{self.base_url}{path}"
        
        headers = kwargs.pop("headers", {})
        auth = None

        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif self._username and self._password:
            auth = aiohttp.BasicAuth(self._username, self._password)

        try:
            async with asyncio.timeout(10):
                async with self._session.request(
                    method, url, auth=auth, headers=headers, ssl=self._verify_ssl, **kwargs
                ) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise TraccarApiError(f"HTTP {resp.status}: {text}")
                    return await resp.json()
        except TimeoutError as err:
            raise TraccarApiError("Timeout connecting to Traccar") from err
        except aiohttp.ClientError as err:
            raise TraccarApiError(f"Connection error: {err}") from err
        except Exception as err:
            raise TraccarApiError(f"Unexpected error: {err}") from err

    async def get_devices(self) -> Any:
        """Fetch all devices."""
        return await self._request("GET", "/devices")

    async def get_positions(self) -> Any:
        """Fetch all positions."""
        return await self._request("GET", "/positions")

    async def send_command(self, device_id: int, command: dict[str, Any]) -> Any:
        """Send a command to a device."""
        payload = {"deviceId": device_id, **command}
        return await self._request("POST", "/commands/send", json=payload)
