Test Spec: fmc130_traccar integration

### Setup
1. Add the integration to a Home Assistant test instance.
2. Create a test asset with a 15 digit IMEI (e.g., `123456789012345`).
3. Set up a listener port (e.g., `5031`).
4. Enable **Debug Mode** in the integration settings to verify parsed IO tracking values.

### Execution
Use the `mock_teltonika.py` script to inject the test payloads found in `TEST_PAYLOADS.md` into the integration.

**Command (Plain TCP):**
```bash
python3 custom_components/fmc130_traccar/mock_teltonika.py -p 5031 -i 123456789012345 -f custom_components/fmc130_traccar/TEST_PAYLOADS.md
```

**Command (SSL/TLS):**
If your integration is configured for TLS, append the `--ssl` flag:
```bash
python3 custom_components/fmc130_traccar/mock_teltonika.py -p 5031 -i 123456789012345 -f custom_components/fmc130_traccar/TEST_PAYLOADS.md --ssl
```

### Verification
The 7th payload block is encoded using **Codec 8 Extended** and decodes to 5 AVL blocks, each containing 30 IO values.

**Expected Decoded Values (from 7th payload):**
| Timestamp | Priority | Longitude | Latitude | Altitude | Angle | Satellites | Speed | Event ID | 239 | 240 | 200 | 81 | 235 | 654 | 655 | 658 | 662 | 898 | 913 | 953 | 958 | 959 | 960 | 962 | 965 | 966 | 967 | 969 | 976 | 1211 | 1212 | 66 | 84 | 90 | 115 | 87 | 866 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
08-May-26 22:13:02	0	72687683	515556166	50	4	14	0	0	0	0	0	0	0	1	0	0	0	1	1	0	0	0	0	0	0	0	0	0	0	0	0	0	13151	340	4352	130	86192000	411
08-May-26 22:13:02	0	72687683	515556166	50	4	14	0	240	1	1	0	0	0	1	0	0	0	1	1	0	0	0	0	0	0	0	0	0	0	0	0	0	13142	340	4352	130	86192000	411
08-May-26 22:13:13	0	72687683	515556166	50	4	14	0	240	0	0	0	0	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	12983	340	4096	130	86192000	403
08-May-26 22:14:05	0	72687683	515556166	50	4	14	0	240	1	1	0	0	0	1	0	0	0	1	1	0	0	0	0	0	0	0	0	0	0	0	0	0	12985	340	4352	130	86192000	403
08-May-26 22:14:12	0	72687683	515556166	50	4	15	0	240	0	0	0	0	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	12870	340	4096	130	86192000	403

**Logs & UI Verification:**
1. Check the Home Assistant `home-assistant.log` file. With Debug Mode enabled, you should see centralized IO tracking messages that confirm scaling modifiers are applied correctly.
   * *Example:* `INFO [custom_components.fmc130_traccar] IO TRACKING [123456789012345]: ID=87, Raw=86192000, Modifier=*0.001, Val=86192.0`
2. Verify that data is received and values are decoded as expected and show up in the device UI dashboard.
   * **Total Distance**: `86,192.0 km`
   * **Fuel Level**: `34.0 %`
   * **Power**: `13.151 V` (or similar depending on the specific record)
