"""Test Teltonika Protocol Listener."""
import asyncio
from unittest.mock import MagicMock, patch
import pytest

from custom_components.fmc130_traccar.listener import TeltonikaProtocol, TeltonikaServer

@pytest.fixture
def mock_server():
    """Mock TeltonikaServer."""
    server = MagicMock(spec=TeltonikaServer)
    server.events = []
    return server

def test_protocol_handshake(mock_server):
    """Test the initial IMEI handshake."""
    protocol = TeltonikaProtocol(mock_server)
    transport = MagicMock(spec=asyncio.Transport)
    protocol.connection_made(transport)

    # Device sends length (2 bytes) + IMEI (15 bytes)
    imei = b"123456789012345"
    protocol.data_received(b"\x00\x0f" + imei)

    # Server should ACK with 0x01
    transport.write.assert_called_with(b"\x01")
    assert protocol.imei == "123456789012345"

def test_protocol_data_reception(mock_server):
    """Test receiving a data packet."""
    protocol = TeltonikaProtocol(mock_server)
    transport = MagicMock(spec=asyncio.Transport)
    protocol.connection_made(transport)

    # Complete handshake first
    protocol.data_received(b"\x00\x0f" + b"123456789012345")
    transport.write.reset_mock()

    # Construct a minimal valid Codec 8 record (without IOs for simplicity)
    # Timestamp(8) + Priority(1) + Lon(4) + Lat(4) + Alt(2) + Ang(2) + Sat(1) + Spd(2) = 24 bytes
    record = (
        b"\x00\x00\x00\x00\x00\x00\x00\x01" + # Timestamp
        b"\x01" +                             # Priority
        b"\x00\x00\x00\x00" +                 # Lon
        b"\x00\x00\x00\x00" +                 # Lat
        b"\x00\x00" +                         # Alt
        b"\x00\x00" +                         # Ang
        b"\x00" +                             # Sat
        b"\x00\x00" +                         # Spd
        b"\x00" +                             # Event ID
        b"\x00\x00\x00\x00"                   # IO Counts (1,2,4,8)
    )

    # Preamble(4) + DataLen(4) + Codec(1) + NumRec(1) + Record + NumRec(1) + CRC(4)
    # DataLen = 1 (Codec) + 1 (NumRec) + 29 (Record) + 1 (NumRec) = 32
    packet = (
        b"\x00\x00\x00\x00" + # Preamble
        b"\x00\x00\x00\x20" + # Length (32 bytes)
        b"\x08" +             # Codec 8
        b"\x01" +             # 1 record
        record + 
        b"\x01" +             # 1 record (repeat at end)
        b"\x00\x00\x00\x00"   # CRC placeholder
    )

    protocol.data_received(packet)

    # Should ACK with number of records (1) as a 4-byte integer
    transport.write.assert_called_with(b"\x00\x00\x00\x01")
    mock_server.handle_data.assert_called_once()
    assert mock_server.handle_data.call_args[0][0] == "123456789012345"
    assert mock_server.handle_data.call_args[0][1]["num_records"] == 1
