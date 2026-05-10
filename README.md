# FMC130 Direct Integration - Custom Integration (`fmc130_traccar`)

This documentation describes the **FMC130 Car Control** integration for Home Assistant.  
This integration is specifically designed for the **Teltonika FMC130** (with CAN control) and is now capable of operating independently of a Traccar server by receiving telemetry directly from the device.

---

## 1. Motivation & Architecture

Traditional tracking integrations rely on polling external APIs. This integration offers a **Local Push** architecture, providing real-time telemetry with sub-second latency.

### Key Advantages:
- **Independence:** No dedicated Traccar server app required within Home Assistant.
- **Real-time:** Telemetry is pushed directly from the FMC130 to Home Assistant.
- **Security:** Built-in support for **TLS (encrypted)** communication.
- **Completeness:** Full CAN bus support (doors, windows, fuel, RPM) and remote commands.

### Data Flow Options:
1. **Direct Mode (Recommended):** Teltonika FMC130 → TCP/TLS (Port 5027) → HA Integration.
2. **Hybrid Mode:** Teltonika FMC130 → Traccar Server → HA Integration (via Polling).

---

## 2. Direct Listener Configuration

The integration acts as a Teltonika Protocol Server (Codec 8/8E).

### Device Configuration:
To use direct mode, configure your Teltonika device (via Configurator or SMS) with:
- **Domain/IP:** Your Home Assistant address.
- **Port:** `5027` (or your custom configured port).
- **Protocol:** TCP.
- **TLS:** Enabled (if SSL certificates are configured in HA).

### Integration Setup:
When adding the integration, you can enable the **Direct Listener**:
- **Port:** Default is `5027`.
- **Use TLS:** Enable to encrypt the data stream.
- **SSL Certificate:** Path to your certificate (e.g., `/config/ssl/fullchain.pem`).
- **SSL Key:** Path to your private key (e.g., `/config/ssl/privkey.pem`).

---

## 3. Features & Sensors

The integration automatically creates entities based on the device's IMEI.

### Real-time Telemetry (Push)
- **GPS Tracking:** Real-time position updates on the HA Map.
- **Ignition & Motion:** Instant status changes.
- **Power & Satellites:** Diagnostic monitoring.

### CAN Bus Telemetry
- **Engine:** RPM, Oil Level, Fuel Level (%).
- **Doors & Windows:** Individual status for all four doors and windows.
- **Security:** Locked/Unlocked status, Handbrake, and Light status.
- **Diagnostics:** DTC (Diagnostic Trouble Codes) list.

### Remote Commands (Services)
Remote commands can be sent via the following services:
- `fmc130_traccar.lock` / `unlock`
- `fmc130_traccar.horn`
- `fmc130_traccar.flash_lights`
- `fmc130_traccar.engine_start` / `stop`
- `fmc130_traccar.dtc_reset`

---

## 4. Integration Files

```
custom_components/fmc130_traccar/
├── __init__.py      # Lifecycle & Server management
├── listener.py      # Teltonika Binary Protocol Server
├── api.py           # Traccar API Fallback client
├── config_flow.py   # UI Configuration with TLS support
├── const.py         # Configuration constants
├── sensor.py        # Telemetry & CAN sensors
├── binary_sensor.py # Status & Security sensors
└── manifest.json    # Component metadata
```

---

## 5. Security Notes

- **IMEI Filtering:** The integration only accepts connections from IMEIs that are registered during the configuration flow.
- **TLS Termination:** It is highly recommended to use TLS when exposing the listener port to the internet.
- **ACK Handling:** The server sends a proper 4-byte ACK for all records, ensuring the device correctly manages its internal data buffer and does not resend duplicate data.

---

## 6. Installation

1. Ensure the folder `custom_components/fmc130_traccar/` is present in your HA `config` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **"FMC130 Traccar Car Control"**.
5. Configure your Traccar endpoint (as fallback) and enable the **Direct Listener**.
