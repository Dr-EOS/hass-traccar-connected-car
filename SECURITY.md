# Security Policy & Review

This integration is designed with a strong focus on security, particularly because it opens a direct TCP listener on the Home Assistant host. 

A comprehensive security review was conducted with the following key findings and architectural highlights:

## 1. Network & Buffer Management (DoS Protection)
The `TeltonikaProtocol` listener receives raw bytes over a TCP socket. To prevent Memory Exhaustion (DoS) attacks:
- **IMEI Boundary Checks:** The initial connection handshake enforces strict bounds on the claimed IMEI length (maximum 100 bytes).
- **Packet Size Limits:** Data payload lengths are capped (max 8192 bytes) to accommodate large multi-record batches safely.
- **Aggressive Drop Policy:** If any length bounds are exceeded, the integration immediately closes the transport connection rather than just clearing the buffer, cleanly dropping malicious or malformed connections.

## 2. Payload Parsing & Memory Safety
- The Codec 8 and Codec 8 Extended (`0x8E`) parsing logic uses strict array bounds checking.
- Before every slice operation or byte read, the code explicitly validates that the buffer contains the required number of bytes (e.g. `if len(data) < offset + required_bytes: break`).
- This prevents `IndexError` exceptions that could crash the TCP listener task or the Home Assistant event loop.
- The number of records per packet is clamped to a maximum of 100, preventing CPU starvation attacks via infinite loops.

## 3. Cryptography & TLS
- When `TLS_MODE_CUSTOM` or `TLS_MODE_HA` is enabled, the integration uses `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)`, which is the modern, secure default for establishing server-side TLS connections in Python.
- The loading of certificates is safely deferred to an executor job, preventing high-latency cryptographic I/O from blocking Home Assistant's main asynchronous event loop.

## 4. Command Injection & Services
- Custom services (e.g., `lock`, `unlock`, `engine_start`) do not accept arbitrary string inputs to send to the device.
- They rely on a strict, hardcoded internal mapping (e.g., calling the `lock` service always translates to the exact string `"can_control lock"`). There is no avenue for a user or automation to inject arbitrary Teltonika GPRS commands.

## 5. Data Privacy
- The integration does not log any sensitive Home Assistant configuration data (such as paths to SSL private keys).
- Device IMEIs and raw hex payloads are only logged when the integration is explicitly placed into `DEBUG` mode via the Options Flow, which is required for the integration's documented IO TRACKING features.
- Dynamic user inputs (like scaling modifiers) are safely parsed using standard Python type casting (`int()`, `float()`) wrapped in robust `try/except` blocks, avoiding unsafe evaluations like `eval()` or `exec()`.
