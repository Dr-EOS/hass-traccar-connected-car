from __future__ import annotations

import asyncio
import logging
import ssl
import struct
from typing import Any

from homeassistant.core import HomeAssistant, callback
from .const import TLS_MODE_NONE, TLS_MODE_HA, TLS_MODE_CUSTOM

_LOGGER = logging.getLogger(__name__)

def crc16(data: bytes) -> int:
    """CRC-16-IBM (0xA001) implementation."""
    crc = 0x0000
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

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
        _LOGGER.debug("Incoming data from %s: %s", self._peername, data.hex())
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
            self.server._connections[self.imei] = self
            self.server._log_event(f"Device connected: {self.imei}")
            # ACK IMEI with 0x01
            self.transport.write(b"\x01")
            
        else:
            # Parse data packets
            while len(self.buffer) >= 12: # Min header length (Preamble + Length)
                if self.buffer[:4] != b"\x00\x00\x00\x00":
                    idx = self.buffer.find(b"\x00\x00\x00\x00")
                    if idx == -1:
                        # Keep last 3 bytes to avoid splitting sync sequence
                        self.buffer = self.buffer[-3:]
                        return
                    self.buffer = self.buffer[idx:]
                    continue
                
                data_len = struct.unpack(">I", self.buffer[4:8])[0]
                
                # Sanity check for data length
                if data_len > 2048:
                    _LOGGER.warning("Packet length too large (%d), clearing buffer", data_len)
                    self.buffer.clear()
                    return

                if len(self.buffer) < 8 + data_len + 4: # Header + Data + CRC
                    return
                
                # We have a full packet
                packet = self.buffer[8:8+data_len]
                
                if self.server.is_debug(self.imei):
                    self.server._log_event(f"RAW PACKET [{self.imei}]: {packet.hex()}")
                    _LOGGER.info("RAW PACKET [%s]: %s", self.imei, packet.hex())
                
                # Verify CRC (CRC-16-IBM)
                packet_crc = struct.unpack(">I", self.buffer[8+data_len:8+data_len+4])[0]
                calculated_crc = crc16(packet)
                
                if packet_crc != calculated_crc:
                    _LOGGER.warning("CRC mismatch for %s: expected %04X, got %04X", self.imei, packet_crc, calculated_crc)
                    # For now we only log it and continue, but in strict mode we might want to drop it
                
                try:
                    num_records = self._parse_records(packet)
                    # ACK with number of records (4 bytes)
                    self.transport.write(struct.pack(">I", num_records))
                except Exception as err:
                    _LOGGER.error("Error parsing Teltonika packet from %s: %s", self.imei, err)
                    self.transport.close()
                    return
                
                # Move buffer
                self.buffer = self.buffer[8+data_len+4:]

    def _parse_records(self, data: bytes) -> int:
        """Parse Codec 8/8E records."""
        if len(data) < 3:
            return 0
            
        codec_id = data[0]
        num_records = data[1]
        
        if num_records > 100:
            _LOGGER.warning("Packet from %s has too many records (%d), limiting to 100", self.imei, num_records)
            num_records = 100

        _LOGGER.debug("Parsing %d records from %s (Codec 0x%02X)", num_records, self.imei, codec_id)
        
        offset = 2
        last_extracted_data = {}

        for i in range(num_records):
            # Check if we have enough data for a record header: Timestamp(8)+Priority(1)+GPS(15) = 24 bytes
            if len(data) < offset + 24:
                _LOGGER.warning("Truncated record %d in packet from %s", i+1, self.imei)
                break
            
            # Skip Timestamp(8) and Priority(1)
            offset += 9
            
            # GPS Data: Lon(4), Lat(4), Alt(2), Ang(2), Sat(1), Spd(2) = 15 bytes
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
                if len(data) < offset + 1: break
                # Event ID (1 byte)
                offset += 1
                
                for size in [1, 2, 4, 8]:
                    if len(data) < offset + 1: break
                    n_elements = data[offset]
                    offset += 1
                    
                    for _ in range(n_elements):
                        if len(data) < offset + 1 + size: break
                        io_id = data[offset]
                        offset += 1
                        val = self._unpack_value(data, offset, size)
                        if val is not None:
                            self._map_io(last_extracted_data, io_id, val)
                        offset += size
            
            elif codec_id == 0x8E: # Codec 8 Extended
                if len(data) < offset + 4: break
                # Event ID (2 bytes) + Total IO Count (2 bytes)
                offset += 4
                
                for size in [1, 2, 4, 8]:
                    if len(data) < offset + 2: break
                    n_elements = struct.unpack(">H", data[offset:offset+2])[0]
                    offset += 2

                    for _ in range(n_elements):
                        if len(data) < offset + 2 + size: break
                        io_id = struct.unpack(">H", data[offset:offset+2])[0]
                        offset += 2
                        val = self._unpack_value(data, offset, size)
                        if val is not None:
                            self._map_io(last_extracted_data, io_id, val)
                        offset += size
                
                # NX variable length elements
                if len(data) >= offset + 2:
                    nx_elements = struct.unpack(">H", data[offset:offset+2])[0]
                    offset += 2
                    for _ in range(nx_elements):
                        if len(data) < offset + 4: break
                        io_id = struct.unpack(">H", data[offset:offset+2])[0]
                        offset += 2
                        val_len = struct.unpack(">H", data[offset:offset+2])[0]
                        offset += 2
                        if len(data) < offset + val_len: break
                        # We currently don't map variable length data, just skip it
                        offset += val_len


        # Final ACK records check
        if len(data) > offset and data[offset] != num_records:
            _LOGGER.debug("Num records check at end: %d != %d", data[offset], num_records)

        self.server._log_event(f"Data received from {self.imei}: {num_records} records (Codec {codec_id})")
        
        if last_extracted_data:
            last_extracted_data["num_records"] = num_records
            self.server.handle_data(self.imei, last_extracted_data)
        
        return num_records

    def _unpack_value(self, data: bytes, offset: int, size: int) -> int | None:
        """Unpack IO value of given size."""
        try:
            if size == 1:
                return data[offset]
            if size == 2:
                return struct.unpack(">H", data[offset:offset+2])[0]
            if size == 4:
                return struct.unpack(">I", data[offset:offset+4])[0]
            if size == 8:
                return struct.unpack(">Q", data[offset:offset+8])[0]
        except (struct.error, IndexError):
            pass
        return None

    def _map_io(self, data: dict, io_id: int, val: int) -> None:
        """Map IO ID to named attribute or generic key."""
        # Always store the raw IO ID
        data[io_id] = val
        
        # Common Teltonika IO IDs (FMC130) for standard logic
        mapped = True
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
        elif io_id == 16: # Odometer
            data["odometer"] = val
        elif io_id == 87: # Total Mileage
            data["totalDistance"] = val
        elif io_id == 320: # CAN Doors
            data["doorFrontLeft"] = bool(val & 0x01)
            data["doorFrontRight"] = bool(val & 0x02)
            data["doorRearLeft"] = bool(val & 0x04)
            data["doorRearRight"] = bool(val & 0x08)
            data["trunk"] = bool(val & 0x10)
            data["bonnet"] = bool(val & 0x20)
        elif io_id == 321: # CAN Security
            data["locked"] = bool((val & 0x1E) == 0x1E)
        elif io_id == 327: # Handbrake
            data["handbrake"] = bool(val)
        elif io_id == 331: # Lights
            data["lights"] = bool(val)
        elif io_id == 324: # Windows
            data["windows"] = bool(val)
        else:
            # Check dynamic mappings
            if io_id not in self.server.get_mappings(self.imei):
                mapped = False
                _LOGGER.debug("Unknown Teltonika IO ID %d for %s: %s", io_id, self.imei, val)
                
                # In debug mode, log new unknown IOs to the event log
                if self.server.is_debug(self.imei):
                    seen = self.server._unknown_io_seen.setdefault(self.imei, set())
                    if io_id not in seen:
                        seen.add(io_id)
                        self.server._log_event(f"UNKNOWN IO ID [{self.imei}]: {io_id} (Value: {val})")

        if mapped:
            _LOGGER.debug("Mapped Teltonika IO ID %d for %s: %s", io_id, self.imei, val)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            _LOGGER.error("Connection lost for %s: %s", self.imei, exc)
            self.server._log_event(f"Error for {self.imei}: {exc}")
        else:
            _LOGGER.debug("Connection closed for %s", self.imei)
            self.server._log_event(f"Disconnected: {self.imei}")
        
        if self.imei:
            self.server.handle_disconnect(self.imei)

    def send_command(self, command: str) -> bool:
        """Send a GPRS command (Codec 12) to the device."""
        if not self.transport:
            return False
            
        cmd_bytes = command.encode("ascii")
        # Codec 12: Preamble(4) + DataLen(4) + Codec(1) + Quantity(1) + Type(1) + CmdLen(4) + Cmd(X) + Quantity(1) + CRC(4)
        data_len = 1 + 1 + 1 + 4 + len(cmd_bytes) + 1
        
        # Build the data part for CRC calculation
        data_part = (
            b"\x0c" +           # Codec 12
            b"\x01" +           # Quantity
            b"\x05" +           # Type (GPRS Command)
            struct.pack(">I", len(cmd_bytes)) +
            cmd_bytes +
            b"\x01"             # Quantity 2
        )
        
        crc_val = crc16(data_part)
        
        packet = (
            b"\x00\x00\x00\x00" +
            struct.pack(">I", data_len) +
            data_part +
            struct.pack(">I", crc_val)
        )
        self.transport.write(packet)
        _LOGGER.debug("Sent command to %s: %s (CRC: 0x%04X)", self.imei, command, crc_val)
        return True

class TeltonikaServer:
    """Teltonika direct GPRS server."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._server = None
        self._connections = {}
        self._debug_modes = {} # IMEI -> bool
        self._mappings = {} # IMEI -> set(IO IDs)
        self._unknown_io_seen = {} # IMEI -> set(IO IDs)
        self.events = [] # Store last 20 events
        self._update_callbacks = []
        self._data_callbacks = {} # IMEI -> callback

    def set_debug(self, imei: str, enabled: bool) -> None:
        """Set debug mode for an IMEI."""
        self._debug_modes[imei] = enabled

    def is_debug(self, imei: str) -> bool:
        """Check if debug mode is enabled for an IMEI."""
        return self._debug_modes.get(imei, False)

    def set_mappings(self, imei: str, mapping_ids: set[int]) -> None:
        """Set dynamic IO mappings for an IMEI."""
        self._mappings[imei] = mapping_ids

    def get_mappings(self, imei: str) -> set[int]:
        """Get dynamic IO mappings for an IMEI."""
        return self._mappings.get(imei, set())

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
        return lambda: self.async_remove_update_callback(callback)

    def async_remove_update_callback(self, callback):
        """Remove a callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def async_add_data_callback(self, imei: str, callback):
        """Add a callback for data from a specific IMEI."""
        self._data_callbacks[imei] = callback
        return lambda: self.async_remove_data_callback(imei)

    def async_remove_data_callback(self, imei: str):
        """Remove a callback."""
        self._data_callbacks.pop(imei, None)

    async def async_start(self, port: int, tls_config: dict | None = None) -> None:
        """Start the TCP/TLS server."""
        ssl_context = None
        mode = tls_config.get("mode", TLS_MODE_NONE)
        
        if mode != TLS_MODE_NONE:
            cert_file = None
            key_file = None
            
            if mode == TLS_MODE_HA:
                cert_file = getattr(self.hass.http, "ssl_certificate", None)
                key_file = getattr(self.hass.http, "ssl_key", None)
                
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
                # Load certificates in executor to avoid blocking event loop
                await self.hass.async_add_executor_job(
                    ssl_context.load_cert_chain, cert_file, key_file
                )
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
        if callback := self._data_callbacks.get(imei):
            self.hass.add_job(callback, imei, data)

    def handle_disconnect(self, imei: str) -> None:
        """Handle device disconnect."""
        if imei in self._connections:
            del self._connections[imei]

    def send_command(self, imei: str, command: str) -> bool:
        """Send a command to a specific device."""
        if imei not in self._connections:
            _LOGGER.error("Device %s not connected", imei)
            return False
        return self._connections[imei].send_command(command)
