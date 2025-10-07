# EcoSweep Intelligent Robot Control App

A comprehensive Flutter application for controlling the EcoSweep universal cleaning robot with advanced AI-powered features including voice interaction, people recognition, GPS tracking, and real-time telemetry monitoring.

## 🚀 Features

### 📱 Multi-Screen Navigation
- **Advanced Dashboard**: Real-time GPS map, live status log, performance metrics, and command center
- **Manual Control**: Proportional joystick control with servo sliders and presets
- **Autonomous**: Mission selection and autonomous cleaning modes
- **FPV Camera**: Live video streaming with overlay controls
- **People Management**: Add and manage people for face recognition
- **Settings**: Bluetooth device management and app configuration

### 🤖 Intelligent Features
- **Voice Interaction**: Real-time display of robot speech and voice commands
- **People Recognition**: Add people with photos for robot to recognize
- **GPS Tracking**: Live map view showing robot's current location
- **Performance Monitoring**: Track garbage collection and other metrics
- **Live Status Log**: Real-time feed of robot actions and interactions

### 🎮 Enhanced Control System
- **Proportional Movement**: Smooth speed and turn control (-255 to 255 range)
- **Servo Control**: Individual angle control (0-180°) with sliders
- **Preset Management**: Save and recall servo position presets
- **Real-time Feedback**: Live sensor data and battery monitoring

### 📡 Enhanced Communication Protocol

The app uses an advanced communication protocol with the Raspberry Pi:

#### **Outgoing Commands**
| Command Type | Format | Example | Description |
| :--- | :--- | :--- | :--- |
| **Movement** | `M:<speed>,<turn>` | `M:200,-90` | Proportional motor control |
| **Servo Angle** | `S:<id>,<angle>` | `S:1,120` | Set servo to specific angle |
| **Servo Action** | `SA:<command>` | `SA:ARM_UP_START` | Continuous servo movement |
| **Mode Set** | `MODE:<mode>` | `MODE:AUTO_ON` | Set operational mode |
| **Preset Recall** | `PRESET:<name>` | `PRESET:pickup` | Execute saved preset |
| **Person Add** | `PERSON:ADD:<name>` | `PERSON:ADD:John` | Add person for recognition |

#### **Incoming Data**
| Data Type | Format | Example | Description |
|:--- |:--- |:--- |:--- |
| **Sensors** | `DATA:SENSORS:<front>,<left>,<right>` | `DATA:SENSORS:45,30,60` | Ultrasonic sensor readings |
| **Battery** | `DATA:BATT:<robot_v>,<controller_v>` | `DATA:BATT:12.5,3.7` | Battery voltage levels |
| **GPS** | `DATA:GPS:<lat>,<lon>` | `DATA:GPS:19.0760,72.8777` | Live GPS coordinates |
| **Log** | `DATA:LOG:<message>` | `DATA:LOG:Voice cmd 'FORWARD'` | Status message for live log |
| **Speech** | `DATA:SPEAK:<text>` | `DATA:SPEAK:My name is EcoSweep.` | Robot speech transcript |
| **Stats** | `DATA:STATS:<items>` | `DATA:STATS:5` | Performance statistics |

## 🏗️ Architecture

### Hardware Communication Flow
```
Flutter App ↔ Bluetooth Classic (SPP) ↔ Raspberry Pi 4 ↔ USB Serial ↔ Arduino Mega 2560
```

### Key Components
- **4 DC Motors**: For robot movement
- **5 Servo Motors**: For robotic arm control
- **Ultrasonic & IR Sensors**: For navigation and obstacle detection
- **Raspberry Pi Camera**: For FPV video streaming
- **GPS Module**: For location tracking
- **Microphone & Speaker**: For voice interaction
- **Face Recognition Camera**: For people recognition

## 📦 Dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8
  flutter_joystick: ^0.2.1
  google_fonts: ^5.1.0
  flutter_bluetooth_serial: ^0.4.0
  permission_handler: ^11.0.1
  provider: ^6.1.1
  shared_preferences: ^2.2.2
  google_maps_flutter: ^2.5.0
  image_picker: ^1.0.4
  path_provider: ^2.1.1
```

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Robot_newcontrol
   ```

2. **Install dependencies**
   ```bash
   flutter pub get
   ```

3. **Run the app**
   ```bash
   flutter run
   ```

## 📱 Usage

### Initial Setup
1. Open the app and navigate to **Settings**
2. Scan for and connect to your Raspberry Pi Bluetooth device
3. Configure the camera stream URL (default: `http://192.168.1.100:8080/stream`)

### Manual Control
1. Navigate to **Manual Control** tab
2. Use the joystick for proportional movement control
3. Adjust servo angles using the sliders
4. Save current servo positions as presets for quick recall

### Autonomous Operation
1. Navigate to **Autonomous** tab
2. Select a cleaning mission (Room, Spot, Edge, Custom)
3. Configure safety settings
4. Start the mission and monitor progress

### FPV Camera
1. Navigate to **FPV** tab
2. Connect to the camera stream
3. Use overlay joystick for FPV control
4. Take snapshots and record video

## 🔧 Configuration

### Camera Setup
The Raspberry Pi should run a video streaming server (e.g., `mjpg-streamer`):
```bash
# On Raspberry Pi
mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8080"
```

### Bluetooth Pairing
1. Pair your Raspberry Pi with the mobile device
2. Ensure the Pi is running the robot control software
3. Use the app's Settings screen to connect

## 🛠️ Development

### Project Structure
```
lib/
├── main.dart                 # App entry point
├── services/
│   └── bluetooth_service.dart # Enhanced Bluetooth communication
└── screens/
    ├── main_navigation.dart   # Bottom navigation wrapper
    ├── dashboard_screen.dart  # Main dashboard
    ├── manual_control_screen.dart # Manual control interface
    ├── autonomous_screen.dart # Autonomous mode control
    ├── fpv_camera_screen.dart # FPV camera interface
    └── settings_screen.dart  # App settings
```

### Key Features Implemented
- ✅ Multi-screen navigation with BottomNavigationBar
- ✅ Proportional speed control with M:<speed>,<turn> commands
- ✅ Enhanced servo control with sliders and presets
- ✅ Real-time data parsing for sensors and battery
- ✅ FPV camera integration with overlay controls
- ✅ Dashboard with connection status and radar view
- ✅ Comprehensive settings and device management

## 🐛 Troubleshooting

### Common Issues
1. **Bluetooth Connection Failed**
   - Ensure devices are paired
   - Check Bluetooth permissions
   - Restart Bluetooth service

2. **Camera Stream Not Loading**
   - Verify camera URL is correct
   - Check network connectivity
   - Ensure streaming server is running

3. **Commands Not Working**
   - Verify Bluetooth connection
   - Check robot is not in autonomous mode
   - Ensure proper command format

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For support and questions, please contact the development team or create an issue in the repository.