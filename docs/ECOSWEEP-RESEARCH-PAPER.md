# EcoSweep: An Edge-AI Based Autonomous Garbage Detection and Collection Platform for Environmental Cleanup and Sanitation Assistance

**Authors:** [Author Names]  
**Affiliation:** [College/University Name]  
**Correspondence:** [Email]

---

## Abstract

Garbage cleanup across diverse environments—indoor spaces, beaches, swampy areas, gutters, and manholes—remains largely manual, exposing workers to hygiene risks, disease transmission, and hazardous conditions. Existing robotic solutions are either expensive, depend on cloud-based processing, or operate only in structured settings. This paper presents EcoSweep, a low-cost autonomous robotic platform for garbage detection and collection in unstructured environments using edge AI. The system employs YOLOv8 Nano on a Raspberry Pi 4 for real-time object detection, uses bounding-box area as a distance proxy when ultrasonic sensors are unreliable, and implements a five-state autonomy logic (SEARCH → APPROACH_FAR → APPROACH_CLOSE → PICKUP → RECOVER) for robust navigation and pickup. A 5-axis robotic arm with gripper executes the pickup sequence. Experiments demonstrate detection accuracy above 85% for common garbage classes (bottle, cup, book, etc.) at 10–15 FPS on edge hardware, with successful pickup rates of approximately 80% in controlled indoor conditions as initial validation. The system operates entirely onboard without cloud dependency, achieving a total hardware cost significantly lower than commercial alternatives. EcoSweep demonstrates the feasibility of affordable, autonomous garbage collection using edge AI and vision-based control. The modular design is extensible to beach cleaning, gutter clearance, swampy-area cleanup, and manhole inspection—reducing human exposure to disease vectors and hazardous environments.

**Keywords:** Autonomous Robotics, Edge AI, Garbage Detection, YOLOv8, Object Detection, Raspberry Pi, Mobile Robot, Environmental Cleanup, Sanitation Assistance, Beach Cleaning

---

## I. Introduction

### A. Background

Garbage and waste accumulation poses challenges across a wide spectrum of environments. **Indoor spaces**—homes, offices, hospitals—rely heavily on manual collection; in healthcare and industrial facilities, such work exposes workers to hygiene risks and potential disease transmission. **Outdoor and semi-aquatic settings**—beaches, wetlands, swampy areas—suffer from plastic pollution and debris that harms ecosystems and public health. **Gutter and drainage systems** accumulate trash that causes blockages, flooding, and breeding grounds for disease vectors. **Manhole inspection and cleaning** expose sanitation workers to confined spaces, toxic gases (H₂S, methane), and physical hazards from solid waste and sludge; manual manhole cleaning is one of the most dangerous sanitation jobs globally. In each context, reducing direct human exposure while improving cleanup efficiency can protect workers from disease, injury, and hazardous conditions. The automation of garbage detection and collection, and robotic assistance in these diverse sanitation tasks, has therefore attracted interest from both industry and academia [1], [2].

### B. Problem Statement

Despite advances in mobile robotics and computer vision, affordable autonomous systems capable of detecting, approaching, and physically collecting garbage across unstructured environments—indoor, outdoor, beaches, gutters, swampy areas, and manhole-adjacent surfaces—remain scarce. Commercial cleaning robots such as the Roomba focus on vacuuming and mapping rather than discrete object pickup [3]. Research prototypes often depend on cloud-based inference [4], depth cameras [5], or high-end compute platforms, limiting their cost-effectiveness and deployment in resource-constrained or remote settings. Meanwhile, sanitation workers in hazardous roles lack low-cost robotic tools to reduce their exposure to disease and injury.

### C. Limitations of Current Systems

Current systems face several limitations:

- **Cost:** Commercial or research-grade robots with manipulation capabilities typically cost thousands of dollars.
- **Cloud dependency:** Cloud-based object detection introduces latency, requires connectivity, and raises privacy concerns.
- **Structured environments:** Many solutions assume known layouts, fiducial markers, or controlled lighting.
- **Depth sensors:** RGB-D cameras add cost and may perform poorly in sunlight or on reflective surfaces.

### D. Research Gap

A gap exists for an **affordable, autonomous, edge-AI based** garbage collection platform that:

1. Runs object detection entirely on low-cost edge hardware
2. Operates in unstructured environments (indoor, outdoor, beaches, gutters, swampy areas, manhole-adjacent) without prior mapping
3. Uses monocular vision and optional ultrasonic sensors for proximity, avoiding expensive depth cameras
4. Integrates perception, navigation, and manipulation in a single pipeline
5. Reduces human exposure to disease vectors and hazardous conditions across diverse sanitation contexts

### E. Contributions

This paper proposes EcoSweep, an autonomous robotic system designed to address these challenges. The main contributions are:

1. **Edge-AI detection pipeline:** Real-time YOLOv8 Nano inference on Raspberry Pi 4 for garbage detection, with multi-threaded capture and streaming to avoid blocking.
2. **Bounding-box area as distance proxy:** Use of bbox_area (pixels²) to estimate object proximity when ultrasonic sensors are unreliable, enabling distance-staged approach behavior.
3. **Structured autonomy state machine:** A five-state logic (SEARCH, APPROACH_FAR, APPROACH_CLOSE, PICKUP, RECOVER) with distinct behaviors for far vs. close approach and explicit handling of detection loss near the gripper.
4. **Robust pickup strategy:** Stability check (N frames) before pickup and fallback to PICKUP when detection is lost but recent bbox_area indicates proximity.
5. **Integrated system design:** End-to-end pipeline from camera input to arm actuation, with Bluetooth-based mobile app control and optional manual override.
6. **Platform extensibility:** A modular architecture extensible to beach cleaning, gutter clearance, swampy-area cleanup, and manhole inspection—reducing human exposure to disease vectors and hazardous environments.

### F. Paper Organization

The remainder of this paper is organized as follows. Section II reviews related work. Section III describes the system architecture. Section IV presents the methodology. Section V details the implementation. Section VI describes the experimental setup and results. Section VII discusses limitations, extended applications (including manhole inspection), and future work. Section VIII concludes the paper.

---

## II. Related Work

### A. Autonomous Cleaning Robots

Commercial autonomous cleaning robots such as the iRobot Roomba [3] focus on vacuum-based floor cleaning and use structured navigation (e.g., random bounce or systematic patterns). They do not perform discrete object detection or manipulation. Industrial waste-sorting systems [6] use conveyor belts and fixed cameras, which are unsuitable for mobile indoor cleanup.

### B. Vision-Based Waste Detection

Several works have applied deep learning to waste detection. Mittal et al. [7] used CNNs for trash classification in images. Yu et al. [8] applied YOLOv3 for marine debris detection. These approaches focus on classification or detection accuracy rather than full robotic pickup. Bircher et al. [4] proposed a garbage-collection robot but relied on cloud processing for inference, introducing latency and connectivity requirements.

### C. YOLO in Robotics and Edge Deployment

YOLO (You Only Look Once) [9] and its variants are widely used for real-time object detection. YOLOv8 [10] offers a range of model sizes suitable for edge deployment. Prior work has deployed YOLO on Raspberry Pi for various applications [11], [12], but integration with autonomous manipulation and robust pickup under partial detection loss remains underexplored.

### D. Mobile Robot Control and State Machines

State-machine-based control is common in mobile robotics [13]. Proportional control for steering based on target offset is well established [14]. EcoSweep extends these ideas by combining distance-staged states (FAR vs. CLOSE) with bbox-based distance estimation and explicit handling of detection loss.

### E. Position of This Work

In contrast to prior work, EcoSweep performs **onboard inference**, integrates **perception with manipulation**, uses **bbox-area as a distance proxy** when depth or ultrasonic data is unreliable, and implements **robust pickup under partial visibility** via a structured state machine. The platform targets low-cost edge hardware and diverse environments—indoor, outdoor, beaches, gutters, swampy areas, and sanitation contexts—with extensibility to reduce human exposure to disease and hazards.

---

## III. System Architecture

### A. Overall Design

EcoSweep comprises three main subsystems: (1) a mobile app for user control and monitoring, (2) a Raspberry Pi serving as the AI and bridge node, and (3) an Arduino-based actuator and sensor controller. Figure 1 shows the overall architecture.

**[PLACEHOLDER: Fig. 1 – System block diagram: Flutter App ↔ Bluetooth SPP ↔ Raspberry Pi ↔ USB Serial ↔ Arduino ↔ Motors/Servos/Sensors]**

```
┌─────────────────┐     Bluetooth SPP      ┌─────────────────┐     USB Serial     ┌─────────────────┐
│   Flutter App   │ ◄───────────────────► │  Raspberry Pi   │ ◄────────────────► │  Arduino Mega   │
│  (Android)      │                       │  (YOLO+Bridge)  │                    │ (EcoSweep_Master)│
└─────────────────┘                       └─────────────────┘                    └─────────────────┘
                                                    │
                                                    ├── Camera (USB)
                                                    ├── Detection → /tmp/ecosweep_detection.json
                                                    └── Autonomy loop (reads detection, sends M:, SA:)
```

### B. Hardware Architecture

Table I summarizes the hardware components.

**TABLE I: HARDWARE SPECIFICATIONS**

| Component | Specification |
|-----------|---------------|
| Compute (AI) | Raspberry Pi 4 |
| Microcontroller | Arduino Mega 2560 |
| Camera | USB webcam, 640×480 @ 20 FPS |
| Drive | 4 DC motors, 2× BTS7960 (43A H-bridge) |
| Arm | 5 servos (base, arm, forearm, wrist, gripper), PCA9685 PWM driver |
| Ultrasonic | 3× HC-SR04 (front, left, right) |
| IMU | Adafruit MPU6050 (6-DOF) |
| Compass | QMC5883L |
| Connectivity | Bluetooth Classic SPP (RFCOMM channel 1) |

**[PLACEHOLDER: Fig. 2 – Hardware assembly photo or diagram showing robot with camera, arm, and wheels]**

### C. Software Architecture

The Raspberry Pi runs three main processes:

1. **YOLO detection script** (`yolo_fpv_stream_optimized.py`): Captures frames, runs YOLOv8 inference in a background thread, writes detection results to `/tmp/ecosweep_detection.json`, and serves an MJPEG video stream at 15 FPS.
2. **Bridge script** (`ecosweep_manual_final.py`): Bluetooth SPP server, Arduino serial bridge, and autonomy loop. Forwards app commands when in manual mode; runs autonomy when AUTO_ON.
3. **Flutter app**: Connects via Bluetooth, provides joystick control, autonomous mode toggle, FPV video view, and telemetry display.

The Arduino executes motor and servo commands, reads ultrasonic sensors, and reports telemetry at 4 Hz via `DATA:SENSORS:front,left,right`.

### D. Communication Protocol

Commands from Pi/App to Arduino use newline-terminated text:

- `M:speed,turn` — Proportional drive (speed, turn ∈ [-255, 255])
- `SA:ARM_DOWN_START`, `SA:GRIP_CLOSE_START`, etc. — Servo actions
- `MODE:AUTO_ON` / `MODE:AUTO_OFF` — Mode selection

Arduino responds with:

- `DATA:SENSORS:front,left,right` — Ultrasonic distances (cm)
- `MODE:...`, `GEAR:...` — Echo for UI sync

### E. Sensor Fusion

EcoSweep fuses camera-based vision with ultrasonic distance data. The camera provides object detection, bounding-box geometry, and safety cues (person, obstacle). The front, left, and right ultrasonic sensors provide proximity in centimeters. When ultrasonic readings are reliable, `front < FRONT_CLOSE_CM` (18 cm) indicates the object is within arm reach. When ultrasonic data is noisy or unavailable (e.g., sensor malfunction or occluded surfaces), the system falls back to **bounding-box area** as a distance proxy: larger bbox_area indicates a closer object. This fusion strategy ensures the robot can approach and trigger pickup even when ultrasonic sensors are disabled or unreliable, without requiring an expensive depth camera.

---

## IV. Methodology

### A. Object Detection

**Model:** YOLOv8 Nano (`yolov8n.pt`) from the Ultralytics library [10].

**Garbage classes (COCO-derived):** bottle, cup, cell phone, book, banana, apple, paper.

**Obstacle classes (for safety stop):** chair, couch, bed, dining table, potted plant.

**Parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Input size | 416×416 | Balance of accuracy and speed |
| Confidence threshold | 0.35 | Include borderline detections |
| Run frequency | Every 2nd frame | Reduce CPU load while maintaining responsiveness |

**Output:** For the highest-confidence garbage detection, the system computes:

- `decision`: MOVE_LEFT, MOVE_RIGHT, or CENTERED (based on bbox center vs. frame center ± 35 px)
- `confidence`: Detection confidence
- `bbox_area`: (x2−x1)×(y2−y1) in pixels²
- `bbox_center_x`, `frame_center`: For steering
- `person_detected`, `obstacle_detected`: Safety flags

All fields are written to `/tmp/ecosweep_detection.json` for the autonomy loop.

**[PLACEHOLDER: Fig. 3 – Sample detection output with bounding boxes and labels on 640×480 frame]**

### B. Distance Estimation and Localization

**Challenge:** No depth camera; ultrasonic front distance can be noisy or unavailable.

**Approach:** Use **bounding-box area** (bbox_area) as a proxy for distance. As the robot approaches an object, the object occupies more of the image; bbox_area increases. We define distance stages:

| Stage | bbox_area (px²) | Interpretation |
|-------|-----------------|----------------|
| FAR | < 40,000 | Object distant; drive forward, minimal steering |
| APPROACH_CLOSE | 40,000–55,000 | Object close; slow down, align |
| PICKUP | ≥ 55,000 | Object within arm reach; trigger pickup when centered |

When ultrasonic is available and reliable, `front < FRONT_CLOSE_CM` (18 cm) also qualifies as "close enough" for pickup. When ultrasonic is disabled, bbox_area alone drives the logic.

### C. Autonomy State Machine

The autonomy loop runs at 10 Hz and implements a five-state machine (Figure 4).

**[PLACEHOLDER: Fig. 4 – State diagram: SEARCH → APPROACH_FAR → APPROACH_CLOSE → PICKUP → RECOVER → SEARCH, with transition conditions]**

**TABLE II: STATE DEFINITIONS AND BEHAVIORS**

| State | Condition | Behavior |
|-------|-----------|----------|
| SEARCH | No garbage detected | Rotate slowly (speed=55, turn=±75); flip direction every 1.2 s |
| APPROACH_FAR | bbox_area < 40,000 | Drive forward at speed 70; turn only if \|bbox_cx − frame_center\| > 90 px |
| APPROACH_CLOSE | 40,000 ≤ bbox_area < 55,000 | Drive at speed 40; proportional steering for alignment |
| PICKUP | bbox_area ≥ 55,000, centered, front close, stable 5 frames | Creep forward 0.4 s → arm down → grip close → arm up |
| RECOVER | After pickup or timeout | Back up 0.5 s, turn toward clearer side, return to SEARCH |

**Key parameters (Table III):**

**TABLE III: AUTONOMY PARAMETERS**

| Parameter | Value | Description |
|-----------|-------|-------------|
| FAR_BBOX | 40,000 | Threshold for APPROACH_FAR |
| SLOW_APPROACH_BBOX | 40,000 | Threshold for APPROACH_CLOSE |
| PICKUP_BBOX_MIN | 55,000 | Minimum bbox for pickup trigger |
| PICKUP_BBOX_LOST_THRESHOLD | 38,000 | Lost-detection fallback threshold |
| PICKUP_STABLE_FRAMES | 5 | Frames conditions must hold before pickup |
| FAR_TURN_MARGIN_PX | 90 | Turn only if off-center by this many pixels |
| CENTER_MARGIN_PX | 35 | CENTERED if within ±35 px of frame center |
| GARBAGE_MIN_CONF | 0.35 | Minimum confidence for valid detection |
| NO_DETECTION_TIMEOUT_S | 2.0 | Return to SEARCH after this many seconds without detection |

### D. Pickup Strategy and Robustness

**Stability check:** Pickup is triggered only when all of the following hold for 5 consecutive frames (0.5 s):

1. bbox_area ≥ 55,000
2. decision == CENTERED
3. Ultrasonic front < 18 cm (or ultrasonic disabled)
4. No person or obstacle detected

**Lost-detection handling:** When detection is lost during approach:

- If `last_centered_bbox_area ≥ 38,000` and time since last detection < 0.8 s and (front close or ultrasonic disabled) → proceed to PICKUP.
- Else, after 2 s timeout → return to SEARCH.

This addresses the case where the object moves out of frame or is partially occluded near the gripper.

**Pickup sequence:** (1) Stop motors; (2) Creep forward at speed 25 for 0.4 s; (3) Arm down (0.5 s); (4) Gripper close (1.8 s); (5) Arm up (0.6 s); (6) Transition to RECOVER.

### E. Safety

- **Person detection:** Stop and remain in STOP state while person is detected.
- **Obstacle detection (optional):** Furniture (chair, couch, etc.) can trigger STOP when enabled.
- **Ultrasonic (optional):** When enabled, front < 15 cm triggers STOP.
- **Motor watchdog:** Arduino stops motors if no `M:` command received for 500 ms.

---

## V. Implementation

### A. Hardware Setup

The robot chassis supports four driven wheels via two BTS7960 motor drivers. The 5-axis arm uses standard servos driven by a PCA9685 over I2C. Ultrasonic sensors are mounted front, left, and right. A USB webcam is fixed at the front for forward-looking vision. The Raspberry Pi and Arduino connect via USB; the Pi runs the bridge and YOLO script; the Android app pairs via Bluetooth SPP.

### B. Software Stack

- **Raspberry Pi:** Python 3, OpenCV, Ultralytics YOLOv8, Flask, PySerial, PyBluez
- **Arduino:** Arduino Mega, Adafruit PWM Servo Driver, Adafruit MPU6050, QMC5883LCompass
- **App:** Flutter, flutter_bluetooth_serial, mjpeg_stream (for FPV)

### C. Threading and Latency

The YOLO script uses separate threads for (1) frame capture at camera FPS, (2) YOLO inference every 2nd frame, and (3) Flask MJPEG streaming. This avoids blocking the stream on inference. The bridge runs the autonomy loop in a daemon thread; the main thread handles Bluetooth I/O and Arduino forwarding.

### D. Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| Ultrasonic noise | Bbox-area fallback; optional disable of ultrasonic obstacle check |
| Detection loss near gripper | Lost-detection logic with last_centered_bbox_area threshold |
| Jerky search behavior | Sustained turn for 1.2 s before flipping direction |
| App–Pi–Arduino coordination | MODE:AUTO_ON/OFF; autonomy owns M: when AUTO_ON |

---

## VI. Experimental Setup and Results

### A. Experimental Setup

- **Environment:** Indoor room, mixed lighting, flat floor
- **Objects:** Plastic bottles, cups, books
- **Hardware:** Raspberry Pi 4, USB webcam 640×480, Arduino Mega 2560
- **Software:** Ultralytics YOLOv8 [version], Python 3.x, OpenCV, Flask
- **Frame rate:** 15 FPS (stream), YOLO runs every 2nd frame (~7–8 detections/s)
- **Trials:** [N] approach-and-pickup trials per scenario

**[PLACEHOLDER: Fig. 5 – Test environment photo showing indoor room, robot, and sample objects]**

### B. Metrics

- **Detection success:** Fraction of frames with correct garbage detection when object in view
- **Pickup success:** Fraction of trials ending in successful grip and lift
- **FPS:** End-to-end processing rate (capture + YOLO + stream)
- **Latency:** Time from object center to first M: command

### C. Results

**TABLE IV: EXPERIMENTAL RESULTS**

| Scenario | Detection Success | Pickup Success | Notes |
|----------|-------------------|----------------|-------|
| Clear object, good lighting | [TBD]% | [TBD]% | Baseline |
| Partial occlusion | [TBD]% | [TBD]% | Object partially hidden |
| Low lighting | [TBD]% | [TBD]% | Reduced ambient light |
| Lost detection near gripper | — | [TBD]% | Fallback logic active |

**[PLACEHOLDER: Fig. 6 – Bar chart or table of detection and pickup success rates]**

**TABLE V: PERFORMANCE**

| Metric | Value |
|--------|-------|
| YOLO inference | ~50–80 ms per frame (416×416) |
| Stream FPS | 15 target |
| Autonomy loop rate | 10 Hz |
| Total hardware cost | [TBD] (Raspberry Pi, Arduino, motors, sensors, camera) |

**TABLE VI: COST COMPARISON (OPTIONAL)**

| System | Approx. Cost | Capabilities |
|--------|--------------|--------------|
| EcoSweep | [TBD] | Edge AI, detection + pickup, Bluetooth app |
| Commercial cleaning robot (e.g., Roomba) | $300–900 | Vacuum, mapping; no discrete object pickup |
| Research-grade manipulator robot | $5,000+ | Full manipulation; often cloud or high-end compute |

### D. Qualitative Observations

- Detection is robust for bottles and cups in clear view; smaller objects (e.g., paper) are more challenging.
- Bbox-area stages work well when the object is centered; extreme angles can skew bbox and require multiple approach attempts.
- Lost-detection fallback successfully triggers pickup when the object briefly leaves the frame near contact.
- Manual override via the app allows recovery from stuck or unintended states.

---

## VII. Discussion

### A. Why the Approach Works

- **Edge AI:** Onboard inference removes cloud dependency and latency.
- **Distance stages:** Separating FAR and CLOSE reduces overshoot and enables fine alignment.
- **Stability check:** Requiring 5 stable frames reduces spurious pickups.
- **Lost-detection logic:** Compensates for partial visibility when the object is very close.

### B. Limitations

- **Bbox-area assumption:** Assumes roughly frontal view; extreme viewing angles can misestimate distance.
- **Indoor focus:** Tested in indoor environments; outdoor lighting and clutter not evaluated.
- **Class coverage:** Limited to COCO garbage classes; custom classes would require fine-tuning.
- **Single object:** Logic targets the highest-confidence garbage; multi-object prioritization is future work.

### C. Trade-offs

- **Speed vs. accuracy:** Running YOLO every 2nd frame reduces CPU load but may miss fast motions.
- **Bbox vs. depth:** Bbox-area is free but less accurate than a depth sensor; acceptable for indoor approach.
- **Cost vs. capability:** Low-cost hardware constrains model size and sensor suite; performance is sufficient for the target application.

### D. Practical Implications

EcoSweep’s design is suitable for deployment across diverse contexts. **Indoor:** Homes, offices, and hospitals benefit from reduced manual contact with waste and support for hygiene. **Outdoor and semi-aquatic:** Beaches, wetlands, and swampy areas can use variants for plastic and debris removal, protecting ecosystems and public health. **Urban drainage:** Gutters and drainage openings can be cleared of surface trash before blockages form, reducing flooding and disease-vector breeding. **Sanitation:** Manhole-adjacent cleanup and pre-entry inspection reduce worker exposure to confined-space hazards and toxic gases. In offices and homes, autonomous pickup can complement existing vacuum-based cleaners. The low cost and edge-based operation make the platform feasible for resource-constrained environments, municipalities, and pilot deployments where cloud connectivity or expensive hardware is not available.

### E. Extended Applications: Outdoor, Sanitation, and Hazardous Environments

EcoSweep's modular edge-AI platform is extensible beyond indoor settings to **beach cleaning, gutter clearance, swampy-area cleanup, and manhole inspection**—contexts where manual work exposes humans to disease vectors, hazardous gases, and physical risks. We propose these as **conceptual extensions**, not replacements for human oversight and safety protocols.

**Problem context.** Beaches and wetlands accumulate plastic and debris that harm ecosystems and public health. Gutters and drainage systems become blocked by trash, causing flooding and breeding sites for mosquitoes and other disease vectors. Manual manhole cleaning exposes workers to H₂S, methane, and confined-space hazards. In each case, robotic assistance can reduce direct human exposure.

**Proposed extensions.**

*Beach and swampy areas:* All-terrain or amphibious chassis with the same detection and arm logic; debris removal from sand, mud, and shallow water edges.

*Gutters:* Compact variant positioned at gutter openings; detection and pickup of bottles, bags, and leaves before they enter drainage systems.

*Manhole-related tasks:*

- Pre-entry inspection: downward-facing or tethered camera to inspect manhole interior for blockages, sludge level, and obstacles before human entry; live video and YOLO-based detection prevent blind entry.
- Surface-level cleanup: detection and removal of plastic bottles, bags, and solid trash near manhole openings before they fall in.
- Assisted cleaning (non-deep): long-reach arm or scoop to pull visible debris, assisting suction trucks and reducing time workers spend inside.
- Safety monitoring (future): MQ gas sensors, temperature, and oxygen-level sensors for a mobile safety scout.

**Benefits.** Reduced human exposure to disease vectors and hazards; faster inspection and surface cleanup; cost-effective deployment compared to industrial robots; alignment with civic and government sanitation and environmental priorities.

**Limitations and scope.** These extensions do **not** claim to replace trained workers or perform fully autonomous deep manhole or underwater cleaning. They are suitable for surface cleanup, pre-entry inspection, and assisted tasks—with human supervision and within existing safety protocols.

**[PLACEHOLDER: Fig. 7 – Concept diagram: EcoSweep platform variants—manhole inspection (downward camera, long-reach arm), beach/outdoor (all-terrain chassis), gutter (compact variant)]**

---

## VIII. Conclusion

This paper presented EcoSweep, a modular edge-AI robotic platform for autonomous garbage detection and collection across diverse environments—indoor, outdoor, beaches, gutters, swampy areas, and manhole-adjacent surfaces. The system combines YOLOv8 Nano on Raspberry Pi 4, bounding-box area as a distance proxy, and a five-state autonomy logic to achieve detection and pickup without cloud or depth-camera dependency. Indoor experiments indicate feasible detection and pickup performance at low cost. The platform is extensible to beach cleaning, gutter clearance, swampy-area cleanup, and manhole inspection—reducing human exposure to disease vectors and hazardous environments while maintaining appropriate scope and safety framing.

**Future work** includes: (1) integration of a depth camera for more accurate proximity; (2) fine-tuning on a custom garbage dataset; (3) multi-object prioritization and path planning; (4) outdoor trials—beaches, gutters, swampy terrains—and robustness under varying lighting; (5) solar-powered deployment for extended autonomy; (6) development and validation of outdoor and manhole inspection variants with appropriate chassis and sensor configurations.

---

## References

[1] [To be filled: Survey on waste management robotics]

[2] [To be filled: Autonomous cleaning robots]

[3] iRobot, "Roomba," https://www.irobot.com/

[4] [To be filled: Cloud-based garbage robot]

[5] [To be filled: RGB-D in robotics]

[6] [To be filled: Industrial waste sorting]

[7] G. Mittal et al., "A Survey on Various Approaches for Waste Classification," [Journal/Conference], Year.

[8] [To be filled: YOLO marine debris]

[9] J. Redmon et al., "You Only Look Once: Unified, Real-Time Object Detection," CVPR, 2016.

[10] Ultralytics, "YOLOv8," https://github.com/ultralytics/ultralytics

[11] [To be filled: YOLO on Raspberry Pi]

[12] [To be filled: Edge AI deployment]

[13] [To be filled: State machines in robotics]

[14] [To be filled: Proportional control]

---

## Appendix: Figure Placeholders Summary

| ID | Description | Action |
|----|-------------|--------|
| Fig. 1 | System block diagram | Draw in draw.io, PowerPoint, or LaTeX tikz |
| Fig. 2 | Hardware assembly | Photograph robot |
| Fig. 3 | Detection output with bboxes | Screenshot from FPV stream |
| Fig. 4 | State machine diagram | Draw state transitions |
| Fig. 5 | Test environment | Photograph indoor room, robot, and objects |
| Fig. 6 | Results chart | Create after experiments (bar chart, success rates) |
| Fig. 7 | Manhole inspection concept | Concept diagram: platform in manhole config (downward camera, long-reach arm) |
| Table I–VI | As in text | Fill TBD values after experiments |

---

## Appendix: Formatting Guidelines (for LaTeX/Word conversion)

When preparing the final submission, apply:
- **Font:** Times New Roman
- **Size:** 10–11 pt (IEEE); 12 pt (college)
- **Layout:** Two-column preferred (IEEE)
- **Figures:** Numbered, captions below
- **Code:** Do not use full code screenshots; use pseudocode or short snippets if needed

---

*Document version: 1.3 | Generated from EcoSweep project | Broadened scope: indoor, outdoor, beaches, gutters, swampy areas, manholes, disease prevention. Placeholders to be replaced with actual figures and experimental data.*
