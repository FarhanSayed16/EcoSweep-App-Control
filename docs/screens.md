# Screens

## Main Navigation (Bottom Tabs)

The app uses a single `MainNavigationScreen` with a `BottomNavigationBar` and `IndexedStack`. Order:

| Index | Label | Screen | Description |
|-------|--------|--------|-------------|
| 0 | Dashboard | `EnhancedDashboardScreen` | Map, mission planning, status log, connection indicator |
| 1 | Manual | `ManualControlScreen` | Joystick, gear 1–3, 5 servo sliders, presets |
| 2 | Autonomous | `AutonomousScreen` | Mode toggle, mission type, start/stop, safety |
| 3 | FPV | `FPVCameraScreen` | Camera stream URL, connect, fullscreen, record, overlay joystick |
| 4 | People | `PeopleManagementScreen` | Add/list/delete people (DB + optional PERSON:ADD) |
| 5 | History | `MissionHistoryScreen` | List missions from DB, detail view, GPS path replay |
| 6 | Achievements | `AchievementsScreen` | Achievement grid, progress, unlock check/dialog |
| 7 | Settings | `SettingsScreen` | Bluetooth devices, camera URL, about |

## Connection Gating

Dashboard, Manual, Autonomous, and FPV show a “Please connect to device first” (or similar) state when `BluetoothService.isConnected` is false. People, History, Achievements, and Settings are usable without a live connection.

## Legacy / Alternate Screens

Not in the bottom nav; may be used by other entry points or legacy flows:

- `HomeScreen` — Buttons to Bluetooth Control, Device Control, etc.
- `BluetoothScreen` — Bluetooth-focused UI.
- `DeviceControlScreen` — Device control UI.
- `DashboardScreen` — Older dashboard.
- `AdvancedDashboardScreen` — Alternate dashboard.

Current primary dashboard is `EnhancedDashboardScreen`.
