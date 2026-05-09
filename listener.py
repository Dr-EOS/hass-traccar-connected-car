from __future__ import annotations

import asyncio
import logging
import ssl
import struct
from typing import Any

from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)

class TeltonikaProtocol(asyncio.Protocol):
    """Protocol for Teltonika FMC130 Codec 8/8E."""

    def __init__(self, server: TeltonikaServer) -> None:
        self.server = server
        self.transport = None
        self.imei = None
        self.buffer = bytearray()
        self._peername = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self._peername = transport.get_extra_info("peername")
        _LOGGER.debug("Connection from %s", self._peername)

    def data_received(self, data: bytes) -> None:
        self.buffer.extend(data)
        
        if self.imei is None:
            # First packet should be IMEI (prefixed with 2 bytes length? No, usually raw 15 digits)
            # Standard Teltonika: 2 bytes length + IMEI
            if len(self.buffer) < 2:
                return
            
            imei_len = struct.unpack(">H", self.buffer[:2])[0]
            if len(self.buffer) < 2 + imei_len:
                return
            
            self.imei = self.buffer[2:2+imei_len].decode("ascii")
            self.buffer = self.buffer[2+imei_len:]
            
            _LOGGER.info("Device connected with IMEI: %s", self.imei)
            # ACK IMEI with 0x01
            self.transport.write(b"\x01")
            
        else:
            # Parse data packets
            while len(self.buffer) >= 12: # Min header length
                # Preamble 4x00
                if self.buffer[:4] != b"\x00\x00\x00\x00":
                    # Desync, find next preamble or close
                    idx = self.buffer.find(b"\x00\x00\x00\x00")
                    if idx == -1:
                        self.buffer.clear()
                        return
                    self.buffer = self.buffer[idx:]
                    continue
                
                data_len = struct.unpack(">I", self.buffer[4:8])[0]
                if len(self.buffer) < 8 + data_len + 4: # Header + Data + CRC
                    return
                
                # We have a full packet
                packet = self.buffer[8:8+data_len]
                crc = struct.unpack(">I", self.buffer[8+data_len:8+data_len+4])[0]
                
                # TODO: Validate CRC
                
                num_records = self._parse_records(packet)
                
                # ACK with number of records (4 bytes)
                self.transport.write(struct.pack(">I", num_records))
                
                # Move buffer
                self.buffer = self.buffer[8+data_len+4:]

    def _parse_records(self, data: bytes) -> int:
        """Parse Codec 8 records."""
        if not data:
            return 0
            
        codec_id = data[0]
        num_records = data[1]
        
        # Simple placeholder for now - extract key data
        # In production this would be a full Teltonika parser
        _LOGGER.debug("Received %d records from %s (Codec 0x%02X)", num_records, self.imei, codec_id)
        
        # Trigger update in HA
        # For now, we'll just simulate a data update with some mapping
        # This will be refined as we get real packet structures
        self.server.handle_data(self.imei, {"num_records": num_records, "codec": codec_id})
        
        return num_records

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            _LOGGER.error("Connection lost for %s: %s", self.imei, exc)
        else:
            _LOGGER.debug("Connection closed for %s", self.imei)
        self.server.handle_disconnect(self.imei)

class TeltonikaServer:
    """Teltonika direct GPRS server."""

    def __init__(self, hass: HomeAssistant, callback_fn) -> None:
        self.hass = hass
        self.callback_fn = callback_fn
        self._server = None
        self._connections = {}

    async def async_start(self, port: int, tls_config: dict | None = None) -> None:
        """Start the TCP/TLS server."""
        ssl_context = None
        if tls_config and tls_config.get("enabled"):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                ssl_context.load_cert_chain(
                    tls_config["cert"],
                    tls_config["key"]
                )
                _LOGGER.info("TLS enabled for Teltonika listener on port %d", port)
            except Exception as err:
                _LOGGER.error("Failed to load SSL certificates: %s", err)
                return

        loop = asyncio.get_running_loop()
        self._server = await loop.create_server(
            lambda: TeltonikaProtocol(self),
            host="0.0.0.0",
            port=port,
            ssl=ssl_context
        )
        _LOGGER.info("Started Teltonika listener on port %d", port)

    async def async_stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            _LOGGER.info("Stopped Teltonika listener")

    def handle_data(self, imei: str, data: dict) -> None:
        """Process received data."""
        self.hass.add_job(self.callback_fn, imei, data)

    def handle_disconnect(self, imei: str) -> None:
        """Handle device disconnect."""
        if imei in self._connections:
            del self._connections[imei]
