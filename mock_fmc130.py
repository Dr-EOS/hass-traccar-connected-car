import socket
import time
import sys
import os

def send_payloads(host, port, imei, payloads):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print(f"Connected to {host}:{port}")

            # 1. IMEI Handshake
            # 2 bytes length + IMEI
            imei_bytes = imei.encode('ascii')
            imei_packet = len(imei_bytes).to_bytes(2, 'big') + imei_bytes
            s.sendall(imei_packet)
            
            ack = s.recv(1)
            if ack == b'\x01':
                print(f"IMEI {imei} accepted by server")
            else:
                print(f"IMEI {imei} rejected by server (ACK: {ack.hex() if ack else 'None'})")
                return

            # 2. Send Payloads
            for i, payload_hex in enumerate(payloads):
                if not payload_hex.strip():
                    continue
                
                print(f"Sending payload {i+1}...")
                try:
                    data = bytes.fromhex(payload_hex.strip())
                except ValueError:
                    print(f"Skipping invalid hex line: {payload_hex[:20]}...")
                    continue

                s.sendall(data)
                
                # Wait for ACK (4 bytes num records)
                ack_data = s.recv(4)
                if len(ack_data) == 4:
                    num_records = int.from_bytes(ack_data, 'big')
                    print(f"Received ACK: {num_records} records processed")
                else:
                    print(f"Unexpected ACK: {ack_data.hex()}")
                
                time.sleep(1) # Interval between packets

    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}. Is the integration listener running?")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Get current directory of the script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Default configuration
    HOST = "127.0.0.1"
    PORT = 5027
    IMEI = "123456789012345"
    
    # Path to payloads file (same directory as script)
    payload_file = os.path.join(SCRIPT_DIR, "TEST_PAYLOADS.md")
    
    if not os.path.exists(payload_file):
        print(f"Payload file not found: {payload_file}")
        sys.exit(1)
        
    with open(payload_file, 'r') as f:
        # Extract hex payloads, ignoring comments and empty lines
        payloads = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])
    if len(sys.argv) > 3:
        IMEI = sys.argv[3]

    print(f"Starting mock FMC130 sender for IMEI {IMEI}")
    send_payloads(HOST, PORT, IMEI, payloads)
