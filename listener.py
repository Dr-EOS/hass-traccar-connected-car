from __future__ import annotations

import asyncio
import logging
import ssl
import struct
from typing import Any

from homeassistant.core import HomeAssistant, callback
from .const import TLS_MODE_NONE, TLS_MODE_HA, TLS_MODE_CUSTOM

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
            # Standard Teltonika: 2 bytes length + IMEI
            if len(self.buffer) < 2:
                return
            
            imei_len = struct.unpack(">H", self.buffer[:2])[0]
            if len(self.buffer) < 2 + imei_len:
                return
            
            try:
                self.imei = self.buffer[2:2+imei_len].decode("ascii")
            except UnicodeDecodeError:
                _LOGGER.error("Invalid IMEI received from %s", self._peername)
                self.transport.close()
                return

            self.buffer = self.buffer[2+imei_len:]
            
            _LOGGER.info("Device connected with IMEI: %s", self.imei)
            self.server._log_event(f"Device connected: {self.imei}")
            # ACK IMEI with 0x01
            self.transport.write(b"\x01")
            
        else:
            # Parse data packets
            while len(self.buffer) >= 12: # Min header length
                if self.buffer[:4] != b"\x00\x00\x00\x00":
                    idx = self.buffer.find(b"\x00\x00\x00\x00")
                    if idx == -1:
                        # Keep last 3 bytes to avoid splitting sync sequence
                        self.buffer = self.buffer[-3:]
                        return
                    self.buffer = self.buffer[idx:]
                    continue
                
                data_len = struct.unpack(">I", self.buffer[4:8])[0]
                if len(self.buffer) < 8 + data_len + 4: # Header + Data + CRC
                    return
                
                # We have a full packet
                packet = self.buffer[8:8+data_len]
                # TODO: Verify CRC here if needed
                
                num_records = self._parse_records(packet)
                
                # ACK with number of records (4 bytes)
                self.transport.write(struct.pack(">I", num_records))
                
                # Move buffer
                self.buffer = self.buffer[8+data_len+4:]

    def _parse_records(self, data: bytes) -> int:
        """Parse Codec 8/8E records."""
        if len(data) < 2:
            return 0
            
        codec_id = data[0]
        num_records = data[1]
        
        _LOGGER.debug("Received %d records from %s (Codec 0x%02X)", num_records, self.imei, codec_id)
        
        offset = 2
        last_extracted_data = {}

        for _ in range(num_records):
            if len(data) < offset + 15: # Min record size (Timestamp + Priority + GPS)
                break
            
            # Timestamp (8), Priority (1)
            # gps_time = struct.unpack(">Q", data[offset:offset+8])[0]
            offset += 9
            
            # GPS Data
            lon = struct.unpack(">i", data[offset:offset+4])[0] / 10000000.0
            lat = struct.unpack(">i", data[offset+4:offset+8])[0] / 10000000.0
            alt = struct.unpack(">H", data[offset+8:offset+10])[0]
            ang = struct.unpack(">H", data[offset+10:offset+12])[0]
            sat = data[offset+12]
            spd = struct.unpack(">H", data[offset+13:offset+15])[0]
            offset += 15
            
            last_extracted_data.update({
                "longitude": lon,
                "latitude": lat,
                "altitude": alt,
                "angle": ang,
                "sat": sat,
                "speed": spd,
            })
            
            # IO Elements
            if codec_id == 0x08:
                offset += 1 # Event ID (1 byte)
                for size in [1, 2, 4, 8]:
                    n_elements = data[offset]
                    offset += 1
                    for _ in range(n_elements):
                        io_id = data[offset]
                        offset += 1
                        if size == 1:
                            val = data[offset]
                        elif size == 2:
                            val = struct.unpack(">H", data[offset:offset+2])[0]
                        elif size == 4:
                            val = struct.unpack(">I", data[offset:offset+4])[0]
                        elif size == 8:
                            val = struct.unpack(">Q", data[offset:offset+8])[0]
                        
                        self._map_io(last_extracted_data, io_id, val)
                        offset += size
            
            elif codec_id == 0x8E: # Codec 8 Extended
                offset += 2 # Event ID (2 bytes)
                for size in [1, 2, 4, 8]:
                    n_elements = struct.unpack(">H", data[offset:offset+2])[0]
                    offset += 2
                    for _ in range(n_elements):
                        io_id = struct.unpack(">H", data[offset:offset+2])[0]
                        offset += 2
                        if size == 1:
                            val = data[offset]
                        elif size == 2:
                            val = struct.unpack(">H", data[offset:offset+2])[0]
                        elif size == 4:
                            val = struct.unpack(">I", data[offset:offset+4])[0]
                        elif size == 8:
                            val = struct.unpack(">Q", data[offset:offset+8])[0]
                        
                        self._map_io(last_extracted_data, io_id, val)
                        offset += size

        # Log to the server's event buffer
        self.server._log_event(f"Data received from {self.imei}: {num_records} records (Codec {codec_id})")
        
        # Trigger update in HA with the last record's data
        if last_extracted_data:
            last_extracted_data["num_records"] = num_records
            self.server.handle_data(self.imei, last_extracted_data)
        
        return num_records

    def _map_io(self, data: dict, io_id: int, val: int) -> None:
        """Map IO ID to named attribute or generic key."""
        # Common Teltonika IO IDs (FMC130)
        if io_id == 1: # Ignition
            data["ignition"] = bool(val)
        elif io_id == 240: # Motion
            data["motion"] = bool(val)
        elif io_id == 66: # External Voltage
            data["power"] = val / 1000.0
        elif io_id == 67: # Battery Voltage
            data["battery"] = val / 1000.0
        elif io_id == 113: # Battery Level (%)
            data["batteryLevel"] = val
        elif io_id == 24: # Speed (GNSS)
            data["speed"] = val
        elif io_id == 239: # Ignition (Alternative)
            data["ignition"] = bool(val)
        elif io_id == 16: # Odometer
            data["odometer"] = val
        elif io_id == 85: # RPM
            data["rpm"] = val
        elif io_id == 83: # Fuel Level
            data["fuel"] = val
        else:
            data[f"io_{io_id}"] = val

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            _LOGGER.error("Connection lost for %s: %s", self.imei, exc)
            self.server._log_event(f"Error for {self.imei}: {exc}")
        else:
            _LOGGER.debug("Connection closed for %s", self.imei)
            self.server._log_event(f"Disconnected: {self.imei}")
        self.server.handle_disconnect(self.imei)

class TeltonikaServer:
    """Teltonika direct GPRS server."""

    def __init__(self, hass: HomeAssistant, callback_fn) -> None:
        self.hass = hass
        self.callback_fn = callback_fn
        self._server = None
        self._connections = {}
        self.events = [] # Store last 20 events
        self._update_callbacks = []

    def _log_event(self, message: str) -> None:
        """Log an event for the UI."""
        from homeassistant.util import dt as dt_util
        self.events.insert(0, {
            "time": dt_util.now().isoformat(),
            "event": message
        })
        self.events = self.events[:20]
        for callback in self._update_callbacks:
            callback()

    def async_add_update_callback(self, callback):
        """Add a callback for when events are logged."""
        self._update_callbacks.append(callback)

    def async_remove_update_callback(self, callback):
        """Remove a callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    async def async_start(self, port: int, tls_config: dict | None = None) -> None:
        """Start the TCP/TLS server."""
        ssl_context = None
        mode = tls_config.get("mode", TLS_MODE_NONE)
        
        if mode != TLS_MODE_NONE:
            cert_file = None
            key_file = None
            
            if mode == TLS_MODE_HA:
                http_conf = self.hass.config.as_dict().get("http", {})
                cert_file = http_conf.get("ssl_certificate")
                key_file = http_conf.get("ssl_key")
                
                if not cert_file or not key_file:
                    _LOGGER.error("Home Assistant SSL certificates not found in 'http' configuration")
                    return
            elif mode == TLS_MODE_CUSTOM:
                cert_file = tls_config.get("cert")
                key_file = tls_config.get("key")
                
            if not cert_file or not key_file:
                _LOGGER.error("SSL mode %s requested but paths missing", mode)
                return

            try:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(cert_file, key_file)
                _LOGGER.info("TLS enabled (%s) for Teltonika listener on port %d", mode, port)
            except Exception as err:
                _LOGGER.error("Failed to load SSL certificates (%s): %s", mode, err)
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
