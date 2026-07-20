# EcoSweep Robot Control — Documentation

This folder holds project documentation. Add new `.md` files here and link them below so everything stays findable.

## Index

| Document | Description |
|----------|-------------|
| [project-understanding.md](project-understanding.md) | High-level project understanding, architecture, screens, protocol, hardware |
| [architecture.md](architecture.md) | Technical architecture, data flow, and folder structure |
| [protocol.md](protocol.md) | Bluetooth protocol: commands and telemetry format |
| [screens.md](screens.md) | All screens, navigation, and responsibilities |
| [hardware-components.md](hardware-components.md) | All components and technical hardware (Arduino, Pi, motors, sensors, etc.) |
| [hardware-review.md](hardware-review.md) | Review of hardware folder, Arduino sketch, and Pi bridge code |
| [android-build-fix.md](android-build-fix.md) | flutter_bluetooth_serial namespace + Gradle/AGP/Kotlin upgrade fix |
| [roadmap-ai-camera-automation.md](roadmap-ai-camera-automation.md) | Master plan: camera, AI, autonomy, voice; where things run; phased steps |
| [next-steps-checklist.md](next-steps-checklist.md) | Checklist for Phase 1–4 (camera, AI, autonomy, voice) |

### Phase folders (detailed guides)

| Folder | Description |
|--------|--------------|
| [phase-1-camera/](phase-1-camera/) | **Phase 1:** Full guide — USB webcam on Pi, stream (mjpg-streamer or Flask), app FPV |
| [phase-2-ai/](phase-2-ai/) | **Phase 2:** TFLite guide + **YOLO guide** (Pi 4 4GB: YOLOv8 Nano) |
| [phase-3-autonomy/](phase-3-autonomy/) | **Phase 3:** Full guide — autonomy state machine, targeting, safety |
| [phase-3-autonomy/ECOSWEEP-PI-COMPLETE-SETUP-GUIDE.md](phase-3-autonomy/ECOSWEEP-PI-COMPLETE-SETUP-GUIDE.md) | **Pi setup:** File copy, nano commands, autostart |
| [phase-3-autonomy/ECOSWEEP-PI-FIX-LAYOUT.md](phase-3-autonomy/ECOSWEEP-PI-FIX-LAYOUT.md) | **Pi layout:** Fix paths, verify folders, your layout (ecosweep-phase2) |
| [phase-3-autonomy/ECOSWEEP-PI-CLEANUP.md](phase-3-autonomy/ECOSWEEP-PI-CLEANUP.md) | **Pi cleanup:** Archive old files, keep only what you need |
| [phase-3-autonomy/AUTONOMOUS-MODE-IMPROVEMENT-PLAN.md](phase-3-autonomy/AUTONOMOUS-MODE-IMPROVEMENT-PLAN.md) | **Autonomy:** Improvement plan for movement, arm, obstacles |
| [phase-4-voice/](phase-4-voice/) | Phase 4: Voice assistant (later) |

## Conventions

- Use **Markdown** (`.md`) for all docs.
- Keep filenames lowercase with hyphens (e.g. `project-understanding.md`).
- When adding a new doc, add a row to the **Index** table above.
