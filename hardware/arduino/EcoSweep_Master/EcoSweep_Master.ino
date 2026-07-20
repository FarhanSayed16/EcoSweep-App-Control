// =================================================================
//                 EcoSweep: Universal Cleaning Robot
//                  Master Integration Controller (Readable)
// =================================================================

// --- Includes ---
#include <Wire.h>                 // I2C
#include <Adafruit_PWMServoDriver.h>  // PCA9685 servos
#include <Adafruit_MPU6050.h>     // Gyro/Accel
#include <Adafruit_Sensor.h>
#include <QMC5883LCompass.h>      // Compass

// =================================================================
//                       OBJECT INITIALIZATION
// =================================================================
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);  // I2C addr 0x40
Adafruit_MPU6050 mpu;
QMC5883LCompass compass;

// =================================================================
//                       PIN DEFINITIONS
// =================================================================
// DC Motor Driver Pins (BTS7960, 8-pin control)
#define L_EN_R   6
#define L_EN_L   7
#define L_RPWM   8   // Left forward PWM
#define L_LPWM   9   // Left reverse PWM
#define R_EN_R   10
#define R_EN_L   11
#define R_RPWM   12  // Right forward PWM
#define R_LPWM   13  // Right reverse PWM

// PCA9685 Servo Channels
#define BASE_SERVO    0
#define ARM_SERVO     1
#define FOREARM_SERVO 2
#define WRIST_SERVO   3
#define GRIPPER_SERVO 4

// Ultrasonic Sensor Pins
#define FRONT_TRIG_PIN  22
#define FRONT_ECHO_PIN  23
#define LEFT_TRIG_PIN   24
#define LEFT_ECHO_PIN   25
#define RIGHT_TRIG_PIN  26
#define RIGHT_ECHO_PIN  27

// Analog Sensors
#define MQ_SENSOR_PIN   A0

// =================================================================
//                       GLOBAL CONFIG / STATE
// =================================================================
// Servos
#define SERVO_MIN_PULSE 150
#define SERVO_MAX_PULSE 600
#define SERVO_FREQ      50

int baseAngle     = 90;
int armAngle      = 90;
int forearmAngle  = 90;
int wristAngle    = 90;
int gripperAngle  = 90;

// Continuous servo movement flags (SA commands)
bool baseLeftMoving       = false;
bool baseRightMoving      = false;
bool armUpMoving          = false;
bool armDownMoving        = false;
bool forearmForwardMoving   = false;
bool forearmBackwardMoving  = false;
bool wristLeftMoving      = false;
bool wristRightMoving     = false;
bool gripperOpenMoving    = false;
bool gripperCloseMoving   = false;

// Safety / timing
unsigned long lastCommandTime       = 0;    // For motor watchdog
const unsigned long COMMAND_TIMEOUT_MS  = 500;  // Stop motors if no command in 0.5s

unsigned long lastTelemetryTime     = 0;    // Telemetry scheduler
const unsigned long TELEMETRY_INTERVAL_MS = 250;  // 4 Hz

unsigned long lastServoMoveTime     = 0;    // Servo movement timer
const int SERVO_MOVE_INTERVAL_MS  = 20;   // How fast servos move

// Drive tuning
const int PWM_MAX          = 255;  // BTS7960 accepts 0..255 on Arduino PWM
const int SPEED_DEADBAND   = 8;    // Ignore ± small values to reduce jitter

// Mode echo (for UI)
String currentMode = "Manual";   // Manual, AUTO_ON, AUTO_OFF, etc.

// Gear system
int currentGear = 1;             // 1,2,3
float gearScale = 0.40;          // 1:0.40, 2:0.70, 3:1.00

// Motor/turn calibration signs (adjust here if directions feel wrong)
// +1 means as-is, -1 flips direction
int LEFT_MOTOR_SIGN  = -1;  // flip if left forward goes backward
int RIGHT_MOTOR_SIGN = -1;  // flip if right forward goes backward
int TURN_SIGN        = +1;  // flip if joystick right turns left

// =================================================================
//                         HELPERS (IO)
// =================================================================
static inline void enableDrivers(bool enable) {
  digitalWrite(L_EN_R, enable ? HIGH : LOW);
  digitalWrite(L_EN_L, enable ? HIGH : LOW);
  digitalWrite(R_EN_R, enable ? HIGH : LOW);
  digitalWrite(R_EN_L, enable ? HIGH : LOW);
}

static inline void sendLine(const String &s) {
  Serial.println(s);
}

static inline void sendAck(const char *what) {
  Serial.print("DATA:LOG:");
  Serial.print(what);
  Serial.println(" OK");
}

static inline void sendErr(const char *what) {
  Serial.print("DATA:LOG:ERR ");
  Serial.println(what);
}

// Safe constrain for PWM
static inline int clampPWM(int v) {
  if (v > PWM_MAX) return PWM_MAX;
  if (v < -PWM_MAX) return -PWM_MAX;
  return v;
}

// =================================================================
//                         SETUP
// =================================================================
void setup() {
  Serial.begin(9600);
  Serial.println("EcoSweep Master Controller Initializing...");

  Wire.begin();

  // Motors
  pinMode(L_EN_R, OUTPUT);
  pinMode(L_EN_L, OUTPUT);
  pinMode(L_RPWM, OUTPUT);
  pinMode(L_LPWM, OUTPUT);
  pinMode(R_EN_R, OUTPUT);
  pinMode(R_EN_L, OUTPUT);
  pinMode(R_RPWM, OUTPUT);
  pinMode(R_LPWM, OUTPUT);
  enableDrivers(true);
  stopMotors();
  Serial.println("Motors Initialized.");

  // Servos
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  setServoAngle(BASE_SERVO,     baseAngle);
  setServoAngle(ARM_SERVO,      armAngle);
  setServoAngle(FOREARM_SERVO,  forearmAngle);
  setServoAngle(WRIST_SERVO,    wristAngle);
  setServoAngle(GRIPPER_SERVO,  gripperAngle);
  Serial.println("Servos Initialized.");

  // Ultrasonic
  pinMode(FRONT_TRIG_PIN, OUTPUT);
  pinMode(FRONT_ECHO_PIN, INPUT);
  pinMode(LEFT_TRIG_PIN, OUTPUT);
  pinMode(LEFT_ECHO_PIN, INPUT);
  pinMode(RIGHT_TRIG_PIN, OUTPUT);
  pinMode(RIGHT_ECHO_PIN, INPUT);
  Serial.println("Ultrasonic Sensors Initialized.");

  // IMU
  if (!mpu.begin()) Serial.println("MPU6050 not found. Check wiring.");
  else Serial.println("MPU6050 Found.");

  // Compass
  compass.init();
  compass.setCalibrationOffsets(3479.00, 4508.00, -1863.00);
  compass.setCalibrationScales(0.96, 0.74, 1.66);
  Serial.println("Compass Initialized + Calibrated.");

  Serial.println("✅ EcoSweep System Ready.");
}

// =================================================================
//                         MAIN LOOP
// =================================================================
void loop() {
  handleCommands();           // 1) Commands from Pi/app
  runServoMovement();         // 2) Continuous servo motions

  // 3) Motor watchdog
  if (millis() - lastCommandTime > COMMAND_TIMEOUT_MS) {
    stopMotors();
  }

  // 4) Telemetry at fixed interval
  if (millis() - lastTelemetryTime > TELEMETRY_INTERVAL_MS) {
    sendTelemetry();
    lastTelemetryTime = millis();
  }
}

// =================================================================
//                      COMMAND HANDLING / PARSING
// =================================================================
void handleCommands() {
  if (Serial.available() <= 0) return;

  String command = Serial.readStringUntil('\n');
  command.trim();
  if (command.length() == 0) return;

  // Proportional motor control: M:<speed>,<turn>
  if (command.startsWith("M:")) {
    lastCommandTime = millis();
    int commaIndex = command.indexOf(',');
    if (commaIndex <= 2) { sendErr("Bad M"); return; }
    int speed = command.substring(2, commaIndex).toInt();
    int turn  = command.substring(commaIndex + 1).toInt();
    handleProportionalMove(speed, turn);
    return;
  }

  // Direct servo angle: S:<id>,<angle>
  if (command.startsWith("S:")) {
    int commaIndex = command.indexOf(',');
    if (commaIndex <= 2) { sendErr("Bad S"); return; }
    int id    = command.substring(2, commaIndex).toInt();
    int angle = command.substring(commaIndex + 1).toInt();

    // Persist angle
    if (id == BASE_SERVO) baseAngle = angle;
    else if (id == ARM_SERVO) armAngle = angle;
    else if (id == FOREARM_SERVO) forearmAngle = angle;
    else if (id == WRIST_SERVO) wristAngle = angle;
    else if (id == GRIPPER_SERVO) gripperAngle = angle;

    setServoAngle(id, angle);
    return;
  }

  // Servo actions: SA:<ACTION>
  if (command.startsWith("SA:")) {
    handleServoAction(command.substring(3));
    return;
  }

  // Mode set: MODE:<mode>
  if (command.startsWith("MODE:")) {
    currentMode = command.substring(5);
    Serial.print("MODE:");
    Serial.println(currentMode);  // Echo for app UI
    sendAck("MODE");
    return;
  }

  // Gear set: GEAR:<1|2|3>
  if (command.startsWith("GEAR:")) {
    int g = command.substring(5).toInt();
    if (g < 1) g = 1; if (g > 3) g = 3;
    currentGear = g;
    if (currentGear == 1) gearScale = 0.40;
    else if (currentGear == 2) gearScale = 0.70;
    else gearScale = 1.00;
    Serial.print("GEAR:");
    Serial.println(currentGear);  // Echo for UI/Pi audio logic
    sendAck("GEAR");
    return;
  }

  // Preset recall (no-op here, app already sets angles)
  if (command.startsWith("PRESET:")) {
    sendAck("PRESET");
    return;
  }

  // Mission path (no-op placeholder; implement autonomous follower if needed)
  if (command.startsWith("PATH:")) {
    sendAck("PATH");
    return;
  }

  // Unknown
  sendErr("Unknown cmd");
}

// =================================================================
//                      TELEMETRY TO APP
// =================================================================
void sendTelemetry() {
  // Distances
  long frontDist = getDistance(FRONT_TRIG_PIN, FRONT_ECHO_PIN);
  long leftDist  = getDistance(LEFT_TRIG_PIN, LEFT_ECHO_PIN);
  long rightDist = getDistance(RIGHT_TRIG_PIN, RIGHT_ECHO_PIN);
  int mqVal      = analogRead(MQ_SENSOR_PIN);

  // IMU + compass
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  compass.read();
  int heading = compass.getAzimuth();

  // DATA:SENSORS:<front>,<left>,<right>
  Serial.print("DATA:SENSORS:");
  Serial.print(frontDist); Serial.print(",");
  Serial.print(leftDist);  Serial.print(",");
  Serial.println(rightDist);

  // Optional IMU packet (app ignores if not parsed)
  Serial.print("DATA:IMU:");
  Serial.print(a.acceleration.x, 2); Serial.print(",");
  Serial.print(a.acceleration.y, 2); Serial.print(",");
  Serial.print(a.acceleration.z, 2); Serial.print(",");
  Serial.print(g.gyro.x, 2);         Serial.print(",");
  Serial.print(g.gyro.y, 2);         Serial.print(",");
  Serial.print(g.gyro.z, 2);         Serial.print(",");
  Serial.println(heading);

  // MQ gas value
  Serial.print("DATA:MQ:");
  Serial.println(mqVal);

  // Battery (dummy values)
  Serial.print("DATA:BATT:7.4,11.1\n");

  // Echo current mode and gear so UI / Pi can react
  Serial.print("MODE:");
  Serial.println(currentMode);
  Serial.print("GEAR:");
  Serial.println(currentGear);
}

// =================================================================
//                       HELPER FUNCTIONS
// =================================================================

// This is the NON-BLOCKING servo movement function
void runServoMovement() {
  // Only run this logic on its own timer
  if (millis() - lastServoMoveTime < SERVO_MOVE_INTERVAL_MS) {
    return;
  }
  lastServoMoveTime = millis();

  if (baseLeftMoving && baseAngle > 0) { baseAngle--; setServoAngle(BASE_SERVO, baseAngle); }
  if (baseRightMoving && baseAngle < 180) { baseAngle++; setServoAngle(BASE_SERVO, baseAngle); }
  if (armUpMoving && armAngle > 0) { armAngle--; setServoAngle(ARM_SERVO, armAngle); }
  if (armDownMoving && armAngle < 180) { armAngle++; setServoAngle(ARM_SERVO, armAngle); }
  if (forearmForwardMoving && forearmAngle < 180) { forearmAngle++; setServoAngle(FOREARM_SERVO, forearmAngle); }
  if (forearmBackwardMoving && forearmAngle > 0) { forearmAngle--; setServoAngle(FOREARM_SERVO, forearmAngle); }
  if (wristLeftMoving && wristAngle > 0) { wristAngle--; setServoAngle(WRIST_SERVO, wristAngle); }
  if (wristRightMoving && wristAngle < 180) { wristAngle++; setServoAngle(WRIST_SERVO, wristAngle); }
  if (gripperOpenMoving && gripperAngle < 90) { gripperAngle++; setServoAngle(GRIPPER_SERVO, gripperAngle); } // 90=open
  if (gripperCloseMoving && gripperAngle > 0) { gripperAngle--; setServoAngle(GRIPPER_SERVO, gripperAngle); } // 0=closed
}

// This function handles the logic for SA: commands
void handleServoAction(const String &saCmd) {
  if      (saCmd == "BASE_LEFT_START")       baseLeftMoving = true;
  else if (saCmd == "BASE_LEFT_STOP")        baseLeftMoving = false;
  else if (saCmd == "BASE_RIGHT_START")     baseRightMoving = true;
  else if (saCmd == "BASE_RIGHT_STOP")      baseRightMoving = false;
  else if (saCmd == "ARM_UP_START")           armUpMoving = true;
  else if (saCmd == "ARM_UP_STOP")            armUpMoving = false;
  else if (saCmd == "ARM_DOWN_START")       armDownMoving = true;
  else if (saCmd == "ARM_DOWN_STOP")        armDownMoving = false;
  else if (saCmd == "FOREARM_FORWARD_START") forearmForwardMoving = true;
  else if (saCmd == "FOREARM_FORWARD_STOP")  forearmForwardMoving = false;
  else if (saCmd == "FOREARM_BACKWARD_START") forearmBackwardMoving = true;
  else if (saCmd == "FOREARM_BACKWARD_STOP")  forearmBackwardMoving = false;
  else if (saCmd == "WRIST_ROTATE_LEFT_START") wristLeftMoving = true;
  else if (saCmd == "WRIST_ROTATE_LEFT_STOP")  wristLeftMoving = false;
  else if (saCmd == "WRIST_ROTATE_RIGHT_START") wristRightMoving = true;
  else if (saCmd == "WRIST_ROTATE_RIGHT_STOP")  wristRightMoving = false;
  else if (saCmd == "GRIP_OPEN_START")       gripperOpenMoving = true;
  else if (saCmd == "GRIP_OPEN_STOP")        gripperOpenMoving = false;
  else if (saCmd == "GRIP_CLOSE_START")      gripperCloseMoving = true;
  else if (saCmd == "GRIP_CLOSE_STOP")       gripperCloseMoving = false;
  else                                        sendErr("Bad SA");
}

// Drive one side with signed PWM considering wiring sign
void driveLeft(int pwmSigned) {
  int v = pwmSigned * LEFT_MOTOR_SIGN;
  if (v >= 0) {
    analogWrite(L_RPWM, v);
    analogWrite(L_LPWM, 0);
  } else {
    analogWrite(L_RPWM, 0);
    analogWrite(L_LPWM, -v);
  }
}

void driveRight(int pwmSigned) {
  int v = pwmSigned * RIGHT_MOTOR_SIGN;
  if (v >= 0) {
    analogWrite(R_RPWM, v);
    analogWrite(R_LPWM, 0);
  } else {
    analogWrite(R_RPWM, 0);
    analogWrite(R_LPWM, -v);
  }
}

// Proportional Drive: speed (-255..255), turn (-255..255)
void handleProportionalMove(int speed, int turn) {
  // Swap axes to match physical motor wiring layout
  int temp = speed;
  speed = turn;
  turn = temp;

  // Apply deadband for stability
  if (speed > -SPEED_DEADBAND && speed < SPEED_DEADBAND) speed = 0;
  if (turn  > -SPEED_DEADBAND && turn  < SPEED_DEADBAND)  turn = 0;

  // Apply gear scaling
  long sScaled = (long)(speed * gearScale);
  long tScaled = (long)(turn  * gearScale * TURN_SIGN);

  // Pivot-in-place if little to no forward speed but significant turn
  const int PIVOT_SPEED_BAND = 20;   // |speed| below this -> allow pure pivot
  long left, right;
  if (labs(sScaled) <= PIVOT_SPEED_BAND && tScaled != 0) {
    // Pure pivot: counter-rotating wheels
    left  =  tScaled;
    right = -tScaled;
  } else {
    // Standard arcade mix
    left  = sScaled + tScaled;
    right = sScaled - tScaled;
  }

  // Normalize to keep ratio if any exceeds PWM_MAX
  long maxAbs = max(labs(left), labs(right));
  if (maxAbs > PWM_MAX && maxAbs > 0) {
    left  = (left  * PWM_MAX) / maxAbs;
    right = (right * PWM_MAX) / maxAbs;
  }

  int leftPWM  = (int)left;
  int rightPWM = (int)right;

  driveLeft(leftPWM);
  driveRight(rightPWM);
}

void stopMotors() {
  analogWrite(L_RPWM, 0);
  analogWrite(L_LPWM, 0);
  analogWrite(R_RPWM, 0);
  analogWrite(R_LPWM, 0);
}

void setServoAngle(int channel, int angle) {
  angle = constrain(angle, 0, 180);
  int pulse = map(angle, 0, 180, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  pwm.setPWM(channel, 0, pulse);
}

long getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Timeout to avoid blocking if no echo
  long duration = pulseIn(echoPin, HIGH, 30000UL);  // 30ms timeout
  if (duration == 0) return -1;                      // -1 indicates out of range
  long distance = (long)(duration / 58.8);
  return distance;
}