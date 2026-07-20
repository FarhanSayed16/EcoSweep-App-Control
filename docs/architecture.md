# Architecture

## Overview

```
┌─────────────────┐     Bluetooth SPP      ┌─────────────────┐     USB Serial     ┌─────────────────┐
│   Flutter App   │ ◄───────────────────► │  Raspberry Pi   │ ◄────────────────► │  Arduino Mega   │
│  (Android etc)  │                       │   (bridge.py)   │                    │ (EcoSweep_Master)│
└─────────────────┘                       └─────────────────┘                    └─────────────────┘
```

## Flutter App Structure

```
lib/
├── main.dart                    # Entry: Firebase init, Provider, MaterialApp, MainNavigationScreen
├── services/
│   ├── bluetooth_service.dart   # Connection, commands, telemetry parsing, presets, auto-reconnect
│   ├── database_service.dart    # SQLite: people, missions, achievements
│   └── firebase_service.dart    # FCM init, token, handlers, topics
└── screens/
    ├── main_navigation.dart     # Bottom nav, IndexedStack of 8 screens
    ├── enhanced_dashboard_screen.dart
    ├── manual_control_screen.dart
    ├── autonomous_screen.dart
    ├── fpv_camera_screen.dart
    ├── people_management_screen.dart
    ├── mission_history_screen.dart
    ├── achievements_screen.dart
    ├── settings_screen.dart
    # Legacy / alternate (not in main nav):
    ├── home_screen.dart
    ├── bluetooth_screen.dart
    ├── device_control.dart
    ├── dashboard_screen.dart
    └── advanced_dashboard_screen.dart
```

## Data Flow

- **State**: `BluetoothService` is provided at root via `ChangeNotifierProvider`; screens use `Consumer<BluetoothService>` or `context.read<BluetoothService>()`.
- **Persistence**: Presets and “last device” in SharedPreferences; people, missions, achievements in SQLite via `DatabaseService`.
- **Realtime**: Bluetooth input is parsed and pushed via `notifyListeners()` and dedicated streams (e.g. `gpsStream`, `logStream`).

## Key Dependencies

| Package | Use |
|---------|-----|
| `provider` | State management (BluetoothService) |
| `flutter_bluetooth_serial` | Bluetooth Classic SPP |
| `google_maps_flutter` | Map and mission planning |
| `sqflite` | Local DB |
| `shared_preferences` | Presets, last device |
| `firebase_core` / `firebase_messaging` | Push notifications |
| `flutter_joystick` | Manual control joystick |
| `mjpeg_stream` | FPV video stream |

## Hardware Roles

- **Arduino**: Motors, servos, sensors, serial protocol implementation.
- **Raspberry Pi**: Bluetooth SPP server, serial bridge to Arduino, optional sound (engine/gear/turbo WAVs).
