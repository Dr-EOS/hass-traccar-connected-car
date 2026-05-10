# Teltonika FMC130 Connected Car - Custom Integration (`fmc130_traccar`)

This documentation describes the **Teltonika FMC130 Connected Car** integration for Home Assistant.  
This integration is specifically designed for the **Teltonika FMC130** (with CAN control) and operates by receiving telemetry directly from the device via a built-in TCP/TLS listener.

---

## 1. Motivation & Architecture

This integration offers a **Local Push** architecture, providing real-time telemetry with sub-second latency. It eliminates the need for any external tracking server.

### Key Advantages:
- **Push-Only:** No external API polling for telemetry. Data is pushed directly from the device.
- **Real-time:** Telemetry is updated immediately upon reception from the FMC130.
- **Flexible Security:** Built-in support for **TLS (encrypted)** communication using Home Assistant's own certificates or custom ones.
- **Completeness:** Full CAN bus support (doors, windows, fuel, RPM) and location tracking.

### Data Flow:
**Direct Mode:** Teltonika FMC130 → TCP/TLS (Port 5027) → HA Integration.

---

## 2. Direct Listener Configuration

The integration acts as a Teltonika Protocol Server (Codec 8).

### Device Configuration:
Configure your Teltonika device (via Configurator or SMS) with:
- **Domain/IP:** Your Home Assistant address.
- **Port:** `5027` (or your custom configured port).
- **Protocol:** TCP.
- **TLS:** Enabled (if SSL certificates are configured).

### Integration Setup:
The **Direct Listener** is configured during setup:
- **Friendly Name:** A name for your vehicle.
- **IMEI:** The 15-digit IMEI of the device.
- **Port:** Default is `5027`.
- **TLS Mode:**
    - **Disabled:** Plain TCP (unencrypted).
    - **Home Assistant Certificates:** Uses the certificates configured in your `http` section of `configuration.yaml`.
    - **Custom Certificates:** Specify manual paths to your certificate and private key.

---

## 3. Features & Sensors

The integration automatically creates entities based on the configured IMEI.

### Real-time Telemetry (Push)
- **GPS Tracking:** Real-time position updates on the HA Map.
- **Ignition & Motion:** Instant status changes.
- **Power & Satellites:** Diagnostic monitoring.

### CAN Bus Telemetry
- **Engine:** RPM, Oil Level, Fuel Level (%).
- **Doors & Windows:** Individual status for all four doors and windows.
- **Security:** Locked/Unlocked status, Handbrake, and Light status.
- **Logs:** Real-time protocol event log sensor.

---

## 4. Security Notes

- **TLS Termination:** It is highly recommended to use TLS when exposing the listener port to the internet.
- **HA Certificate Integration:** By default, the integration tries to use the certificates already configured for Home Assistant, simplifying setup for secure connections.
- **ACK Handling:** The server sends a proper 4-byte ACK for all records, ensuring the device correctly manages its internal data buffer.

---

## 5. Installation

1. Ensure the folder `custom_components/fmc130_traccar/` is present in your HA `config` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **"Teltonika FMC130 Connected Car"**.
5. Enter your device details and select your preferred **TLS Mode**.
