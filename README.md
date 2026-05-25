# Teltonika FMC130 Connected Car - Custom Integration (`fmc130_traccar`)

This documentation describes the **Teltonika FMC130 Connected Car** integration for Home Assistant.  
This integration is specifically designed for the **Teltonika FMC130** (with CAN control) and operates by receiving telemetry directly from the device via a built-in TCP/TLS listener.

---

## 1. Motivation & Architecture

This integration offers an extended car tracking based on the Teltonika FMC130 + CAN-CONTROL hardware. Besides the geolocation, additional car properties and values such as total distance, engine temperature and more can be received. 
Car indicators such as door open, coolant level low and others are also supported.
**Local Push** architecture, providing real-time telemetry with sub-second latency. It eliminates the need for any external tracking server.

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
- **IMEI:** The IMEI of the device. It **must be a 15-digit integer value". All other values (less or more digits, characters etc.) are discarded.
- **Port:** Default is `5027`.
- **TLS Mode:**
    - **Disabled:** Plain TCP (unencrypted).
    - **Home Assistant Certificates:** Uses the certificates configured in your `http` section of `configuration.yaml`.
    - **Custom Certificates:** Specify manual paths to your certificate and private key.
- **Debug Mode:** This checkbox enables debug logging and prints incoming payload messages.

### Advanced Mappings (Options Flow):
You can customize the mapping of Teltonika IO IDs to the car's sensors via the **Configure** button:
- The configuration dialog allows you to configure the IO ID and a modifier for every supported vehicle parameter.
- If a certain Teltonika IO ID is not supported by your car, leave the IO ID field blank to disable it. It won't be shown in Home Assistant.
- The **IO ID** field maps specific hardware IO IDs (e.g., `85` for RPM, `84` for Fuel) to Home Assistant entities. It accepts integer numbers or hex numbers (starting with `0x`).
- The **Modifier** field can be used to apply either scaling factors (e.g. `*0.1`) or bitmask logic (e.g. `&0x0F`).
- Binary sensors for locks and complex states may use bitmask logic to determine their state.

---

## 3. Features & Sensors

The integration automatically creates entities based on the configured IMEI.

### Real-time Telemetry (Push)
- **GPS Tracking:** Real-time position updates with Altitude, Speed, and Satellites in state attributes for full map compatibility.
- **Last Update:** A dedicated timestamp sensor showing the exact time of the last received telemetry.
- **Ignition & Motion:** Instant status changes.
- **Power & Satellites:** Diagnostic monitoring.
- **Aggregated Status:** Automatically combines indicators to provide clean `All doors closed` and `No warnings` binary sensors.

### CAN Bus Telemetry
-**Supported IO ID Types:** the type value is case insensitive and one of the following values:
- "Value": Represent numbers which can be measurement values (floating point or integer values). The "Modifier" can be used to scale the received value (e.g. if "total distance" is sent in meters, use a modifier "*0.001" to calculate the distance in km). If no modifier is specified, the received values is treated as-is (no scaling is applied).
- "Indicator": Such indicators are used to transmit a certain status such as door open. The FMC130 sends either a 0 (status condition not met) or 1 (status condition active, e.g. a certain door is open). Indicators can be used in the UI to either show individual status' (for each door), an aggregation over a number of indicators (such as "All doors cloded") or only show the status of an active indicator ("front left door open", but omit all closed doors).
- "Warning": A warning is a specialised form of an indicator and correspond to indicator lights in your car's dashoard. They are utilized as heads-up to signalize a warning state of your car (check engine, oil level low, coolant liquid level low, low tire pressure, such as coolant overtemperature, ...). The FMC130 sends either a 0 (indicator light off = status okay) or 1 (the corresponding indicator light is on = a warning is shown). Equivalent to its utilization in the car's dashboard, warning indicators are usually only shown to the driver if a warning indicator is active (value of 1). If a dedicated car status page exists, usually all warning indicators are listed with either status "OK" or a meaninfull warning "Coolant level low".
- "Enum": Enums are used to represent a predefined set of possible states. The FMC130 sends intger values which can be used to map 1 of n exclusive or states (such as 0=No Sleep, 1=GPS Sleep, 2=Deep Sleep, 3=Online Sleep, 4=Ultra Sleep).

-**Default IO IDs:**
IO ID,Name,Type, Modifier,Unit
66,External Voltage, Value, *0.001,V
81,Vehicle Speed,Value,,km/h
84,Fuel Level,Value, *0.1,l
87,Total Mileage,Value, *0.001,km/h
115,Engine Temperature,Value, *0.1,°C
200,Sleep Mode,Enum,,,
235,Oil Level Indicator,Warning,,,
239,Ignition,Indicator,,,
240,Movement Indicator,Indicator,,,
654,Front Left Door Open,Indicator,,,
655,Front Right Door Open,Indicator,,,
658,Trunk Door Open,Indicator,,,
662,Car Is Closed,Indicator,,,
866,Vehicle Range,Value,,km
913,Engine Cover Open,Indicator,,,
953,Check Engine Indicator,Warning,,,
958,Oil Level Indicator,Warning,,,
959,Coolant liquid level Indicator,Warning,,,
960,Battery Not Charging Indicator,Warning,,,
964,Warning Indicator,Warning,,,
965,Lights Failure Indicator,Warning,,,
966,Low Tire Pressure Indicator,Warning,,,
967,Wear Of Brake Pads Indicator,Warning,,,
968,Low Fuel Level Indicator,Warning,,,
969,Maintenence required Indicator,Warning,,,
976,Low Coolant Level Indicator,Warning,,,

-**Data continuity:**
If your Teltonika GPS module does not send the full set of IO IDs every time, all newly received IO IDs are updated with the received payload. 
For those IO IDs which were not updated, the last known value is kept until a new value is received. This ensures that gaps do not lead to "unknown" values.

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

---

## 6. Development & Security

For developers and security-conscious users, please refer to the following supplementary documentation:
- [SECURITY.md](SECURITY.md): Details on the security architecture, threat model, and past reviews (e.g., DoS protection, memory safety, TLS handling).
- [Test_Spec.md](Test_Spec.md): Comprehensive instructions on how to test the integration using the provided mock scripts and sample payloads.
