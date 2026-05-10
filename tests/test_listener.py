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
    """Test the IMEI handshake."""
    protocol = TeltonikaProtocol(mock_server)
    transport = MagicMock(spec=asyncio.Transport)
    protocol.connection_made(transport)
    
    # 2 bytes length (15) + 15 bytes IMEI
    imei_data = b"\x00\x0f" + b"123456789012345"
    protocol.data_received(imei_data)
    
    assert protocol.imei == "123456789012345"
    transport.write.assert_called_with(b"\x01")

def test_protocol_data_reception(mock_server):
    """Test receiving a data packet."""
    protocol = TeltonikaProtocol(mock_server)
    transport = MagicMock(spec=asyncio.Transport)
    protocol.connection_made(transport)
    
    # Complete handshake first
    protocol.data_received(b"\x00\x0f" + b"123456789012345")
    transport.write.reset_mock()
    
    # Construct a dummy Codec 8 packet
    # Preamble(4) + DataLen(4) + Codec(1) + NumRec(1) + ... + CRC(4)
    # Total data length for this dummy: 2 bytes (Codec + NumRec)
    packet = (
        b"\x00\x00\x00\x00" + # Preamble
        b"\x00\x00\x00\x02" + # Length
        b"\x08" +             # Codec 8
        b"\x05" +             # 5 records
        b"\x00\x00\x00\x00"   # CRC placeholder
    )
    
    protocol.data_received(packet)
    
    # Should ACK with number of records (5) as a 4-byte integer
    transport.write.assert_called_with(b"\x00\x00\x00\x05")
    mock_server.handle_data.assert_called_once()
    assert mock_server.handle_data.call_args[0][0] == "123456789012345"
    assert mock_server.handle_data.call_args[0][1]["num_records"] == 5
