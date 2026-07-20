# Phase 4: Voice Assistant — Full Guide

**Goal:** Control EcoSweep and get spoken feedback using voice: e.g. “start cleaning”, “stop”, “where are you?”, with the robot (or app) replying via text-to-speech.

Phase 4 was deferred until Phase 1–3 were solid. With camera, YOLO detection, and autonomy in place, you can start Phase 4 when you’re ready.

---

## Overview

| Step | Where | What to do |
|------|--------|------------|
| **4.1** | Pi | Add microphone input; run **speech-to-text (STT)** (e.g. Vosk offline, or Google/cloud API). Map recognized phrases → commands (MODE:AUTO_ON, M:0,0, “status”, etc.). |
| **4.2** | Pi or App | **Text-to-speech (TTS)** for status: “Cleaning started”, “Garbage detected”, “Stopped”. Can run on Pi (e.g. `espeak`/`pyttsx3`) or send text to the app to speak. |
| **4.3** | Protocol | Use existing `DATA:SPEAK:<text>` from Arduino/Pi to app for feedback; optionally add `VOICE:command` from app to Pi if voice runs on the app. |

---

## Step 4.1: Speech-to-Text (STT) on the Pi

- **Hardware:** USB microphone or Pi-compatible mic (e.g. Respeaker, or a simple USB mic).
- **Options:**
  - **Vosk** (offline, runs on Pi): Good for “start”, “stop”, “go”, “left”, “right” with a small model. No internet required.
  - **Cloud API** (Google, Azure, etc.): Better accuracy; needs network and API key.
- **Flow:** Mic → STT → intent/phrase → map to:
  - `MODE:AUTO_ON` / `MODE:AUTO_OFF`
  - `M:0,0` (stop)
  - Optional: `M:100,0`, “status”, etc.
- **Integration:** Run the STT loop in a thread or separate process; when a command is recognized, push it into your bridge (e.g. same queue as app commands, or send over Bluetooth if you expose a “voice command” channel). Your existing bridge already handles `MODE:AUTO_ON` and `M:` from the app—treat voice as another source of those same commands.

---

## Step 4.2: Text-to-Speech (TTS) for Feedback

- **On Pi:** Use `espeak` (lightweight) or `pyttsx3` to speak status when:
  - Autonomy starts/stops
  - Garbage detected
  - Person detected (safety stop)
  - Low battery (if you have BATT telemetry)
- **On App:** If the Pi sends `DATA:SPEAK:Cleaning started` (or similar) over Bluetooth, the app can show it in a log and optionally use a TTS engine to read it aloud.
- **Protocol:** Reuse `DATA:SPEAK:<text>` in the stream from Pi → app so the app can display and optionally speak the same messages.

---

## Step 4.3: Protocol and Wiring

- **Pi → App:** Keep using your existing telemetry stream; add or reuse a line like `DATA:SPEAK:<message>` for voice/status messages so the app can show and optionally speak them.
- **Voice commands → Pi:** Either:
  - Run STT on the Pi and inject commands into the bridge (same path as app commands), or
  - Run STT on the app and send a dedicated `VOICE:<command>` (or reuse `MODE:AUTO_ON`, `M:0,0`, etc.) over Bluetooth. Your bridge already accepts MODE and M:; no protocol change needed if voice on Pi sends the same strings.

---

## Prerequisites

- Phase 1–3 working (camera, YOLO, autonomy in production bridge).
- Microphone connected to the Pi (or use the app’s mic if you do STT on the app).
- Decide where STT runs: **Pi** (offline with Vosk) or **App** (cloud or on-device STT).

---

## Checklist — Phase 4

- [ ] **4.1** Mic + STT on Pi (or app); map phrases to MODE:AUTO_ON/OFF, M:0,0, etc.
- [ ] **4.2** TTS for status messages (Pi or app); optional `DATA:SPEAK:` for app display/speak.
- [ ] **4.3** Commands from voice reach the bridge; feedback (if any) uses existing protocol.

When these are done, EcoSweep can be controlled and optionally announced via voice; you can then refine phrases and add more commands as needed.
