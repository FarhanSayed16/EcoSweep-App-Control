# EcoSweep: Arduino Sensor Data vs Pi vs App

**Purpose:** List what the Arduino sends, what the Pi bridge parses/uses, and what the app is documented to display.

---

## 1. What the Arduino Sends (every 250 ms in `sendTelemetry()`)

| Packet | Source | Content | Important? |
|--------|--------|---------|------------|
| **DATA:SENSORS:** | Ultrasonic (3× HC-SR04) | `front,left,right` (cm; -1 if timeout) | **Yes** – obstacle distance, autonomy |
| **DATA:IMU:** | MPU6050 + QMC5883L | `accel_x,accel_y,accel_z, gyro_x,gyro_y,gyro_z, heading` (heading = compass azimuth) | **Yes** – orientation / tilt / heading |
| **DATA:MQ:** | MQ gas sensor (A0) | Raw analog value (0–1023) | **Yes** – air quality / safety |
| **DATA:BATT:** | Dummy in code | `7.4,11.1` (hardcoded; no real ADC) | No – not real sensor data |
| **MODE:** | Echo | Current mode (Manual, AUTO_ON, etc.) | For UI only |
| **GEAR:** | Echo | 1, 2, or 3 | For UI only |

**Not in this Arduino sketch:**  
- **Neo (GPS):** Protocol mentions `DATA:GPS:...` but the current sketch does **not** read or send GPS.  
- **Motor current/encoder:** No motor-current or encoder packets are sent; only drive commands (M:) are received.

---

## 2. Sensors in the Arduino Code (Summary)

| Sensor | Library / Pins | Used in `sendTelemetry()` |
|--------|----------------|---------------------------|
| **Ultrasonic × 3** | TRIG/ECHO 22–27 | ✅ `DATA:SENSORS:front,left,right` |
| **MPU6050** | I2C (Adafruit_MPU6050) | ✅ Accel + gyro in `DATA:IMU:...` |
| **QMC5883L compass** | I2C (QMC5883LCompass) | ✅ Heading (last value in `DATA:IMU`) |
| **MQ (A0)** | `analogRead(MQ_SENSOR_PIN)` | ✅ `DATA:MQ:<value>` |
| **Battery** | — | ❌ Only dummy `DATA:BATT:7.4,11.1` |

---

## 3. What the Pi Bridge Does

**File:** `hardware/pi/ecosweep_manual_final_patched.py`

| Arduino packet | Pi parses? | Pi uses for |
|----------------|------------|-------------|
| DATA:SENSORS | ✅ Yes | Autonomy: `front`, `left`, `right` (obstacle, stuck, recovery) |
| DATA:IMU | ❌ No | Not parsed; line is still forwarded to app |
| DATA:MQ | ❌ No | Not parsed; line is still forwarded to app |
| DATA:BATT | ❌ No | Not parsed; line is still forwarded to app |
| MODE / GEAR | ❌ No | Not parsed; forwarded to app |

So on the Pi, **only ultrasonic (DATA:SENSORS)** is parsed and used. All lines are forwarded to the app over Bluetooth.

---

## 4. What the App Is Documented to Do

From `docs/phase-3-autonomy/PHASE-3-VERIFICATION-AND-DEBUGGING.md`, `docs/project-understanding.md`, and `docs/protocol.md`:

| Data | Documented app behavior |
|------|--------------------------|
| **DATA:SENSORS** | Parsed; “Robot telemetry” (or similar) shows front/left/right distances; `lastSensorUpdate` used for “Updated Xs ago”. |
| **DATA:BATT** | Parsed; battery levels shown on Dashboard (or similar). |
| **DATA:IMU** | “App may ignore” (optional). |
| **DATA:MQ** | “App may ignore” (optional). |
| **MODE / GEAR** | Echo used for UI (current mode, gear). |

So in the docs, the app is **expected** to at least **display**:
- Ultrasonic: front, left, right (cm).
- Battery: robot and controller voltage (when real BATT is implemented).

IMU and MQ are described as optional (may be ignored by the app).

---

## 5. Gaps (Arduino → App)

| Item | Arduino | Pi | App (from docs) |
|------|---------|-----|------------------|
| Ultrasonic (front, left, right) | ✅ Sends | ✅ Parses & uses | ✅ Should display |
| IMU (accel, gyro, heading) | ✅ Sends | ❌ Only forwards | ⚠️ “May ignore” |
| MQ (gas) | ✅ Sends | ❌ Only forwards | ⚠️ “May ignore” |
| Battery | ⚠️ Dummy only | ❌ Not parsed | ✅ Should display when real |
| GPS (Neo) | ❌ Not in sketch | — | Protocol defined, not sent |

---

## 6. Recommendations

1. **App:**  
   - Confirm that **DATA:SENSORS** is parsed and that **front / left / right** are shown (e.g. on Autonomous or Dashboard).  
   - If you want IMU (tilt/heading) and MQ (gas) on the UI, add parsing for **DATA:IMU** and **DATA:MQ** in the app (and optional parsing on Pi if needed for autonomy later).

2. **Pi (optional):**  
   - Keep forwarding all Arduino lines to the app.  
   - Only DATA:SENSORS is required for current autonomy; IMU/MQ can stay “forward only” unless you add features that use them.

3. **Arduino:**  
   - No change needed for sensor *sending*.  
   - For real battery display, replace dummy `DATA:BATT:7.4,11.1` with actual voltage readings when hardware is available.

4. **GPS (Neo):**  
   - Not present in the current sketch. To use it, add a Neo module, read it in the sketch, and send `DATA:GPS:lat,lon` as per protocol; then add app parsing if you want to show position.

---

*Summary: Arduino sends ultrasonic (DATA:SENSORS), IMU+compass (DATA:IMU), MQ (DATA:MQ), and dummy BATT. Pi only parses and uses DATA:SENSORS. The app is documented to display SENSORS and BATT; IMU and MQ are optional. Motor-related data is not sent from Arduino.*
