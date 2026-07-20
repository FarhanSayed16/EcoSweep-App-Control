## EcoSweep App – Minimal Sensor Display Plan (IMU, Compass, MQ Gas)

**Goal:** Show live readings from the **IMU (MPU6050)**, **compass (QMC/HMC)** and **MQ gas sensor** in the Flutter app, so users and judges can see that the robot has advanced onboard sensing.  
Changes are **display-only**: autonomy logic on the Pi/Arduino is not modified.

---

## Phase 0 – Prerequisites (Arduino + Pi) ✅ Implemented

**What is already implemented:**

- Arduino sends the following packets from `sendTelemetry()` every 250 ms:
  - `DATA:IMU:ax,ay,az,gx,gy,gz,heading`
  - `DATA:MQ:value`
  - (Plus existing `DATA:SENSORS:front,left,right` and dummy `DATA:BATT:7.4,11.1`)
- The Pi bridge forwards every line from Arduino to the app over Bluetooth SPP.

**Implemented for verification:**

- In `hardware/pi/ecosweep_manual_final_patched.py`:
  - `TELEMETRY_LOG_IMU_MQ = True` and `TELEMETRY_LOG_IMU_MQ_INTERVAL_S = 5.0`
  - When the bridge receives a line starting with `DATA:IMU:` or `DATA:MQ:`, it logs once per 5 s: *"Telemetry: IMU/MQ packets received (forwarded to app)"*
- Run the bridge (and connect the app or a serial monitor to the Pi) and check `journalctl -u ecosweep-bridge -f` (or terminal) to confirm Phase 0.

**Exit criteria:**

- `DATA:IMU` and `DATA:MQ` are visible in bridge logs and look reasonable.

---

## Phase 1 – App: Parse `DATA:IMU` and `DATA:MQ` (no UI yet) ✅ Implemented

**Objective:** Extend the Bluetooth receive handler to understand IMU and MQ packets, but only log them for now.

**Implemented:**

- In `lib/services/bluetooth_service.dart`:
  - In `_handleIncomingData()`, added branches for `DATA:IMU:` and `DATA:MQ:`.
  - **`_parseImuData(message)`**: strips `DATA:IMU:`, splits on `,`, parses 7 doubles (ax, ay, az, gx, gy, gz, heading). Logs in debug: `IMU ax=... ay=... az=... heading=...°`.
  - **`_parseMqData(message)`**: strips `DATA:MQ:`, parses one int. Logs in debug: `MQ gas=...`.
  - Logging uses `kDebugMode` and `debugPrint` so it only appears in debug builds.

**Exit criteria:**

- When the robot is running and the app is connected, the Flutter debug console shows parsed IMU and MQ values without crashes, e.g.:
  - `IMU ax=0.12 ay=-0.03 az=9.80 heading=125°`
  - `MQ gas=345`

---

## Phase 2 – Shared Telemetry Model ✅ Implemented

**Objective:** Store parsed IMU and MQ data in a small telemetry object that the UI can read.

**Tasks:**

- Define a simple data class, for example:
  - `SensorTelemetry` with fields:
    - `ax, ay, az, gx, gy, gz` (double?)
    - `headingDeg` (double?)
    - `gasRaw` (int?)
    - `lastImuUpdate` and `lastGasUpdate` (`DateTime?`)
- In the Bluetooth service or provider:
  - Maintain a single instance of `SensorTelemetry` (e.g. `_telemetry`).
  - On `DATA:IMU`:
    - Update IMU/heading fields and `lastImuUpdate = DateTime.now()`.
  - On `DATA:MQ`:
    - Update `gasRaw` and `lastGasUpdate = DateTime.now()`.
- Expose this telemetry to the UI:
  - Either via a `ChangeNotifier` + `Provider` getter, or a `Stream<SensorTelemetry>`.

**Implemented:**

- In `lib/services/bluetooth_service.dart`:
  - **`SensorTelemetry`** class with `ax, ay, az, gx, gy, gz, headingDeg, gasRaw, lastImuUpdate, lastGasUpdate` and `copyWith()`.
  - **`_sensorTelemetry`** held in `BluetoothService`; updated in `_parseImuData` and `_parseMqData` with `notifyListeners()`.
  - Getter **`sensorTelemetry`** for the UI.

**Exit criteria:**

- A temporary debug widget (or unit test) can read `SensorTelemetry` and see values update when the robot is running.

---

## Phase 3 – UI: “Advanced Sensors” Card ✅ Implemented

**Objective:** Show the sensor data in a small, clear card on an existing screen (Dashboard or Autonomous tab).

**Tasks:**

- Create a widget, e.g. `AdvancedSensorsCard`, which:
  - Reads `SensorTelemetry` (via `Consumer`, `Selector`, or `StreamBuilder`).
  - Displays:
    - **Heading (Compass):** `XXX°` (rounded `headingDeg`)
    - **Tilt (IMU):** `ax, ay` (or a simplified pitch/roll)
    - **Gas (MQ):** raw `gasRaw` value
- Handle staleness:
  - If `now - lastImuUpdate > 3 s`, show `Heading: —` and/or `IMU: —`.
  - If `now - lastGasUpdate > 3 s`, show `Gas: —`.
- Place the card:
  - On the Dashboard or Autonomous screen, under existing telemetry or status sections.

**Implemented:**

- **`lib/widgets/advanced_sensors_card.dart`**: `AdvancedSensorsCard` uses `Consumer<BluetoothService>`, shows Heading (°), Tilt (ax, ay), Gas (raw). Values older than 3 s show "—".
- **Dashboard** (`lib/screens/enhanced_dashboard_screen.dart`): card added after Performance Metrics.
- **Autonomous** (`lib/screens/autonomous_screen.dart`): card added after Robot telemetry card.

**Exit criteria:**

- During a demo:
  - Rotating the robot changes the **heading** value.
  - Tilting the robot changes **IMU** values.
  - Stimulating the MQ sensor changes the **Gas** value.
- When sensors are inactive or disconnected, the card shows `—` instead of stale numbers and the app remains stable.

---

## Phase 4 – Optional Polishing ✅ Implemented

These are nice-to-have improvements if time allows:

- Replace raw `ax, ay` with more user-friendly labels:
  - e.g. `Pitch` and `Roll` calculated from accelerometer.
- Show a simple color-coded bar for gas:
  - Green (safe), yellow (medium), red (high), based on calibrated thresholds.
- Add a one-line caption under the card:
  - “Live data from onboard IMU, compass, and gas sensor.”

**Implemented:**

- **Pitch & Roll:** Computed from ax, ay, az in the card: `pitch = atan2(-ax, sqrt(ay²+az²))`, `roll = atan2(ay, sqrt(ax²+az²))` (degrees). Displayed as "P X° R Y°".
- **Gas bar:** Horizontal `LinearProgressIndicator` (0–1023): green ≤350, orange 351–650, red >650. Grey bar when stale.
- **Caption:** "Live data from onboard IMU, compass, and gas sensor." in grey italic below the bar.

No further changes in this phase are required for functionality.

---

## Phase review (post–Phase 4) – Enhancements applied

After implementing Phase 4, all phases were reviewed and the following enhancements were applied:

- **Phase 0 (Pi bridge):** Added a short comment above `TELEMETRY_LOG_IMU_MQ` noting that IMU/MQ logging is for the app’s Advanced Sensors card.
- **Phase 1 / 2 (Parsing):**  
  - **IMU:** Payload and each comma-separated part are trimmed before parsing to tolerate spaces.  
  - **MQ:** Gas value is clamped to 0–1023 before storing so the UI and bar never see out-of-range values.
- **Phases 3–4 (Card):** No further code changes; pitch/roll, gas bar, and caption are implemented as specified.

No breaking changes; behaviour remains backward compatible.
