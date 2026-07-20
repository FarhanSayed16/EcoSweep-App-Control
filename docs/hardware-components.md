# Hardware Components & Technical Stack

This document lists all components and technical hardware used in the EcoSweep robot system, as inferred from the Arduino sketch, Pi bridge, and project READMEs.

---

## 1. Compute & Connectivity

| Component | Role | Notes |
|-----------|------|--------|
| **Arduino Mega 2560** | Main motor/servo/sensor controller | Serial @ 9600 baud, USB to Pi |
| **Raspberry Pi 4** | Bluetooth SPP server, serial bridge, optional audio | Runs `ecosweep_bridge.py`; implied by README |
| **Bluetooth Classic (SPP)** | App ↔ Pi link | RFCOMM channel 1, UUID `00001101-0000-1000-8000-00805F9B34FB` |

---

## 2. Actuation (Arduino)

### DC Motors (Drive)

| Item | Detail |
|------|--------|
| **Count** | 4 DC motors (2 left, 2 right) |
| **Driver** | 2× **BTS7960** (43A H-bridge, 8-pin control per side) |
| **Arduino pins** | Left: `L_EN_R` 6, `L_EN_L` 7, `L_RPWM` 8, `L_LPWM` 9 — Right: `R_EN_R` 10, `R_EN_L` 11, `R_RPWM` 12, `R_LPWM` 13 |
| **Control** | PWM 0–255 per side; forward/reverse via RPWM/LPWM |

### Servos (Arm / Gripper)

| Item | Detail |
|------|--------|
| **Count** | 5 servos |
| **Driver** | **PCA9685** 16-channel PWM (I2C address `0x40`) |
| **Channels** | 0 Base, 1 Arm, 2 Forearm, 3 Wrist, 4 Gripper |
| **Pulse** | 50 Hz; pulse width 150–600 (mapped from 0–180°) |
| **Libraries** | Adafruit_PWMServoDriver (Arduino) |

---

## 3. Sensors (Arduino)

### Ultrasonic Distance

| Item | Detail |
|------|--------|
| **Count** | 3 (front, left, right) |
| **Type** | HC-SR04-style (TRIG + ECHO per sensor) |
| **Pins** | Front: 22 (TRIG), 23 (ECHO) — Left: 24, 25 — Right: 26, 27 |
| **Output** | Distance in cm (or -1 if timeout); sent as `DATA:SENSORS:front,left,right` |

### IMU (Gyro / Accel)

| Item | Detail |
|------|--------|
| **Module** | **Adafruit MPU6050** (6-DOF) |
| **Interface** | I2C (Wire) |
| **Output** | Accel x,y,z; gyro x,y,z; temp — sent as `DATA:IMU:...` (app may ignore) |

### Compass

| Item | Detail |
|------|--------|
| **Module** | **QMC5883L** |
| **Calibration** | Offsets/scales in sketch (3479, 4508, -1863; 0.96, 0.74, 1.66) |
| **Output** | Heading (azimuth); included in `DATA:IMU` packet |

### Analog (Gas / Air Quality)

| Item | Detail |
|------|--------|
| **Sensor** | **MQ-series** (e.g. MQ-2/MQ-5) on **A0** |
| **Output** | Raw analog value; sent as `DATA:MQ:<value>` (app may ignore) |

---

## 4. Power & Battery (Mentioned but Not Measured in Code)

- **Robot battery** and **controller battery** are referenced in protocol (`DATA:BATT:robot_v,controller_v`).
- Arduino sketch currently sends **dummy values** `DATA:BATT:7.4,11.1` — no ADC or fuel-gauge wiring in the provided code.
- Real implementation would require voltage dividers + analog reads or I2C fuel gauge.

---

## 5. Optional / Referenced in Main README (Not in This Repo’s Firmware)

| Component | Mentioned In | Status in Arduino/Pi Code |
|-----------|----------------|---------------------------|
| **Raspberry Pi Camera** | Main README (FPV) | Not in `hardware/`; FPV stream is separate (e.g. mjpg-streamer or Flask on Pi) |
| **GPS module** | Main README, protocol | Not in Arduino sketch; could be on Pi or future add-on |
| **Microphone & speaker** | Main README (voice) | Not in Arduino/Pi bridge code |
| **Face recognition camera** | Main README | Not in Arduino/Pi bridge code |

---

## 6. Pi-Side Optional: Audio

| Item | Detail |
|------|--------|
| **Player** | `aplay` (ALSA) |
| **Location** | `hardware/pi/sounds/` (optional WAV files) |
| **Files** | `engine_idle.wav`, `engine_gear1/2/3.wav`, `shift.wav`, `turbo.wav` |
| **Trigger** | Movement (`M:`), gear change (`GEAR:`), throttle lift (turbo), or app `SOUND:TURBO` / `SOUND:SHIFT` |

---

## 7. Arduino Libraries (from Sketch)

| Library | Purpose |
|---------|---------|
| `Wire` | I2C (PCA9685, MPU6050, QMC5883L) |
| `Adafruit_PWMServoDriver` | PCA9685 servos |
| `Adafruit_MPU6050` | MPU6050 IMU |
| `Adafruit_Sensor` | Sensor abstraction for MPU6050 |
| `QMC5883LCompass` | QMC5883L compass |

---

## 8. Summary Table (What’s in the Sketch / Bridge)

| Category | Component | Present in Code |
|----------|-----------|------------------|
| MCU | Arduino Mega 2560 | ✅ |
| SBC | Raspberry Pi 4 | ✅ (run environment) |
| Drive | 4 DC motors + 2× BTS7960 | ✅ |
| Arm | 5 servos + PCA9685 | ✅ |
| Distance | 3× ultrasonic (HC-SR04 style) | ✅ |
| IMU | MPU6050 | ✅ |
| Compass | QMC5883L | ✅ |
| Gas | MQ on A0 | ✅ |
| Battery | Voltage reading | ⚠️ Dummy values only |
| GPS | Module | ❌ Not in Arduino |
| Camera | Pi camera / FPV | ❌ Separate from bridge |
| Audio | WAV on Pi | ✅ Optional in bridge |
