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
- **Shared Listener:** Support for multiple vehicles on the same TCP port.
- **Deep Control:** Functional GPRS command support (Codec 12) for vehicle control (locking/unlocking, engine start/stop).

### Data Flow:
**Direct Mode:** Teltonika FMC130 → TCP/TLS (Port 5027) → HA Integration.

---

## 2. Direct Listener Configuration

The integration acts as a Teltonika Protocol Server (Codec 8/8E).

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
- **Debug Mode:** This checkbox enables debug logging and prints incoming payload messages.

### Advanced Mappings (Options Flow):
You can customize the Teltonika IO ID mappings (refer to 3. Features & Sensors) via the **Configure** button:
- Each line contains input fields: IO ID, modifier field, unit
- If a certain Teltonika IO ID is not supported by your car, leave the IO ID field blank to disable it.
- The IO ID field maps specific hardware IO IDs (e.g., `85` for RPM, `83` for Fuel) to Home Assistant sensors. It accepts integer numbers or hex numbers (starting with 0x).
- The modifier field can be used to apply either scaling factors (e.g. '*0.1' or bitmask logic (e.g. '&0x0F')
- Binary sensors for doors and security use bitmask logic on the configured IO IDs. The bitmask field accepts hex or binary notation (starting with 0b).


---

## 3. Features & Sensors

The integration automatically creates entities based on the configured IMEI.

### Real-time Telemetry (Push)
- **GPS Tracking:** Real-time position updates with Altitude, Speed, and Satellites in state attributes for full map compatibility.
- **Last Update:** A dedicated timestamp sensor showing the exact time of the last received telemetry.
- **Ignition & Motion:** Instant status changes.
- **Power & Satellites:** Diagnostic monitoring.

### CAN Bus Telemetry
-**Default IO IDs:**
IO ID,Name,Scaling,Unit
66,External Voltage,0.001,V
81,Vehicle Speed,,km/h
84,Fuel Level,0.1,l
87,Total Mileage,0.001,km/h
115,Engine Temperature,0.1,°C
200,Sleep Mode,,
235,Oil Level Indicator,,
239,Ignition,,
240,Movement Indicator,,
654,Front Left Door Open,,
655,Front Right Door Open,,
658,Trunk Door Open,,
662,Car Is Closed,,
866,Vehicle Range,,km
913,Engine Cover Open,,
953,Check Engine Indicator,,
958,Oil Level Indicator,,
959,Coolant liquid level Indicator,,
960,Battery Not Charging Indicator,,
964,Warning Indicator,,
965,Lights Failure Indicator,,
966,Low Tire Pressure Indicator,,
967,Wear Of Brake Pads Indicator,,
968,Low Fuel Level Indicator,,
969,Maintenence required Indicator,,
976,Low Coolant Level Indicator,,
- **Logs:** Real-time protocol event log sensor showing connections and raw data info.

---

## 4. Debugging & Troubleshooting

The integration provides extensive debug information which can be enabled in the config dialog:
- **Raw Hex Dumps:** Every incoming packet is logged as hex in `DEBUG` mode.
- **IO Tracking:** Any IO IDs sent by your hardware are logged to Home Assistent built-in logs for easy identification. Log entries comprise IO ID, corresponding raw value, the configured modifier to apply (scaling, bitmask, ...) and converted value after applying the modifier.
- **Blocking Protection:** High-latency tasks like SSL certificate loading are handled in background threads to ensure Home Assistant UI stability.

---

## 5. Installation

1. Ensure the folder `custom_components/fmc130_traccar/` is present in your HA `config` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **"Teltonika FMC130 Connected Car"**.
5. Enter your device details and select your preferred **TLS Mode**.
