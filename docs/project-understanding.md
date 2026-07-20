# Project Understanding

## What the Project Is

**EcoSweep Robot Control** is a Flutter application (`robot_control`) for controlling the EcoSweep universal cleaning robot. It communicates with the robot over **Bluetooth Classic (SPP)** and provides manual drive, servo control, autonomous missions, FPV camera, people management, mission history, and achievements.

---

## Architecture

### Tech Stack

- **Flutter** (SDK ≥3.6.1) with **Provider** for state management
- **Bluetooth**: `flutter_bluetooth_serial` (Classic SPP)
- **Maps**: `google_maps_flutter`
- **Local DB**: **SQLite** via `sqflite`
- **Firebase**: Core + Messaging (push notifications)
- **Hardware path**: App ↔ Bluetooth SPP ↔ Raspberry Pi 4 ↔ USB Serial ↔ Arduino Mega 2560

### Supported Platforms

- **Android** (primary), plus Linux, macOS, Windows, web

---

## App Structure

### Entry Point & Shell

- **`main.dart`**: Initializes Firebase (non-blocking), runs `EcoSweepApp` with `ChangeNotifierProvider<BluetoothService>`, teal theme and Google Fonts; home is `MainNavigationScreen`.
- **`main_navigation.dart`**: Bottom navigation with **8 tabs** (IndexedStack): Dashboard, Manual, Autonomous, FPV, People, History, Achievements, Settings.

### Services

| Service | Purpose |
|--------|---------|
| **bluetooth_service.dart** | Singleton `ChangeNotifier`. Connects to device, sends commands (`M:`, `S:`, `SA:`, `MODE:`, `PRESET:`, `GEAR:`, `PATH:`, `PERSON:ADD:`, etc.), parses incoming telemetry (sensors, battery, GPS, log, speech, stats, MODE, GEAR). Manages presets (SharedPreferences), known people (in-memory + prefs), auto-reconnect (10 attempts, 5s interval), and streams for connection/sensors/battery/log/GPS. |
| **database_service.dart** | Singleton SQLite DB `ecosweep.db`. Tables: **people** (name, photoPath, addedAt), **missions** (name, times, items, distance, gpsPath, status), **achievements** (id, title, description, icon, isUnlocked, requiredValue, metric). Seeds default achievements: First Mission, Garbage Collector, Distance Traveler, People Person. |
| **firebase_service.dart** | Singleton. `Firebase.initializeApp()`, FCM permission, token, `onMessage` / `onMessageOpenedApp` / `getInitialMessage`, topic subscribe/unsubscribe. Notifications are logged; tap handling can route by `data['screen']`. |

### Screens (Main Navigation)

| Screen | Purpose |
|--------|---------|
| **Enhanced Dashboard** | Google Map, mission planning (tap waypoints, polyline, send `PATH:`), live status log, connection/reconnect indicator, “connect first” state. |
| **Manual Control** | Joystick (speed/turn with deadband and throttling), gear 1/2/3, 5 servos (sliders), presets (save/recall/delete). Requires connection. |
| **Autonomous** | Mode toggle (manual/auto), mission type (room/spot/edge/custom), status/progress, start/stop, safety options. Requires connection. |
| **FPV Camera** | Camera URL (default `http://10.96.89.158:5000/video_feed`), stream connect, fullscreen, record toggle, overlay joystick. Requires connection. |
| **People Management** | Add person (name + image picker), list from DB, delete; sends `PERSON:ADD:name` when connected. |
| **Mission History** | List missions from DB, detail cards, map replay of GPS path. |
| **Achievements** | Grid of achievements, progress, unlock check from stats (missions + people), unlock dialog. |
| **Settings** | Bluetooth (bonded list, connect/disconnect, scan), camera URL, app/about. Default camera URL `http://192.168.1.100:8080/stream`. |

### Other Screens (Present but Not in Bottom Nav)

- `home_screen.dart`, `bluetooth_screen.dart`, `device_control.dart`, `dashboard_screen.dart`, `advanced_dashboard_screen.dart` — legacy or alternate flows; main flow uses `EnhancedDashboardScreen` and the 8-tab nav.

---

## Communication Protocol (App ↔ Robot)

### Outgoing Commands

| Command | Format | Description |
|---------|--------|-------------|
| Movement | `M:<speed>,<turn>` | Speed and turn in range -255 to 255 |
| Servo angle | `S:<id>,<angle>` | Servo 0–180° |
| Servo action | `SA:<action>` | Continuous servo movement |
| Mode | `MODE:<mode>` | e.g. AUTO_ON, AUTO_OFF |
| Preset | `PRESET:<name>` | Recall saved servo preset |
| Gear | `GEAR:1\|2\|3` | 3-speed gear (scales movement) |
| Path | `PATH:lat,lon;...` | Mission waypoints |
| Person | `PERSON:ADD:<name>` | Add person for recognition |
| Sound | `SOUND:TURBO\|SHIFT` | Pi-only; trigger WAV playback |

### Incoming Data (Telemetry)

| Type | Format | Description |
|------|--------|-------------|
| Sensors | `DATA:SENSORS:front,left,right` | Ultrasonic distances (cm) |
| Battery | `DATA:BATT:robot_v,controller_v` | Voltages |
| GPS | `DATA:GPS:lat,lon` | Current position |
| Log | `DATA:LOG:...` | Status message |
| Speech | `DATA:SPEAK:...` | Robot speech text |
| Stats | `DATA:STATS:...` | e.g. garbage count |
| Mode | `MODE:...` | Current mode echo |
| Gear | `GEAR:n` | Current gear (1–3) |

---

## Hardware

- **Arduino** (`hardware/arduino/EcoSweep_Master/`): Mega sketch — DC motors (BTS7960), PCA9685 servos, ultrasonics, MPU6050, QMC5883L; gear scaling; MODE/GEAR; serial @ 9600.
- **Raspberry Pi** (`hardware/pi/ecosweep_bridge.py`): Bluetooth SPP server (RFCOMM 1), bridges app ↔ Arduino; handles `SOUND:*` and engine/gear/turbo WAV playback via `aplay`.

---

## Android

- **AndroidManifest**: Bluetooth (and BLUETOOTH_SCAN/CONNECT), location (fine/coarse), Maps API key from `@string/google_maps_api_key`, `usesCleartextTraffic`, launcher activity. App uses **Bluetooth Classic SPP** (not BLE).

---

## Tests & Config

- **`test/widget_test.dart`**: Expects “EcoSweep Dashboard” and “Connection Status”; current UI uses “EcoSweep Command Center” — test is outdated and will fail until updated.
- **`analysis_options.yaml`**: Uses `package:flutter_lints/flutter.yaml`.

---

## Summary

EcoSweep is a full-featured robot control app: Bluetooth service with auto-reconnect, SQLite for people/missions/achievements, Firebase for push, and eight main screens (dashboard with map and planning, manual with joystick/gears/servos, autonomous, FPV, people, history, achievements, settings). Hardware side: Arduino Mega plus Raspberry Pi bridge; app uses a text-based protocol over Bluetooth SPP. Some legacy screens exist outside the main nav; the widget test needs updating to match the current dashboard.
