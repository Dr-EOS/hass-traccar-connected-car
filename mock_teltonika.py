#!/usr/bin/env python3
import socket
import time
import sys
import os
import argparse
import ssl

def send_payloads(host, port, imei, payloads, interval=1.0, loop=False, use_ssl=False):
    """Connect to server and send payloads."""
    try:
        while True:
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.settimeout(5.0) # Prevent indefinite hang during SSL handshake or connection
            if use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                s = context.wrap_socket(raw_sock, server_hostname=host)
            else:
                s = raw_sock

            with s:
                s.connect((host, port))
                print(f"Connected to {host}:{port} {'(SSL)' if use_ssl else '(Plain)'}")

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
                    
                    print(f"Sending payload {i+1}/{len(payloads)}...")
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
                    
                    if i < len(payloads) - 1 or loop:
                        time.sleep(interval)
                
                if not loop:
                    break
                print("Looping payloads...")

    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}. Is the integration listener running?")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except TimeoutError:
        print(f"Error: Connection timed out. If you used --ssl, ensure port {port} is actually configured for TLS in Home Assistant.")
    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Mock Teltonika device sender for Home Assistant.")
    
    parser.add_argument("-H", "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=5027, help="Server port (default: 5027)")
    parser.add_argument("-i", "--imei", default="123456789012345", help="Device IMEI (default: 123456789012345)")
    parser.add_argument("-f", "--file", help="Path to hex payloads file (default: TEST_PAYLOADS.md in script dir)")
    parser.add_argument("-t", "--interval", type=float, default=1.0, help="Interval between payloads in seconds (default: 1.0)")
    parser.add_argument("-l", "--loop", action="store_true", help="Loop the payloads indefinitely")
    parser.add_argument("-s", "--single", help="Send a single hex payload string and exit")
    parser.add_argument("--ssl", action="store_true", help="Use SSL for connection")

    args = parser.parse_args()

    # Determine payloads
    payloads = []
    if args.single:
        payloads = [args.single]
    else:
        # Default to TEST_PAYLOADS.md in same dir as script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        payload_file = args.file if args.file else os.path.join(script_dir, "TEST_PAYLOADS.md")
        
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            sys.exit(1)
            
        with open(payload_file, 'r') as f:
            payloads = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    if not payloads:
        print("No payloads found to send.")
        sys.exit(1)

    print(f"Starting mock Teltonika sender for IMEI {args.imei}")
    print(f"Target: {args.host}:{args.port}, Interval: {args.interval}s, Loop: {args.loop}, SSL: {args.ssl}")
    
    send_payloads(args.host, args.port, args.imei, payloads, args.interval, args.loop, args.ssl)

if __name__ == "__main__":
    main()
