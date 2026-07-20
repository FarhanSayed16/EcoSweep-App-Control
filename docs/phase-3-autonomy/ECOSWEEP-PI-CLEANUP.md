# EcoSweep Pi — Cleanup Guide

Your Pi has many ecosweep files. This guide cleans it up and keeps only what you need.

---

## What You Need (Keep)

| Path | Purpose |
|------|---------|
| `/home/pi/ecosweep_manual_final.py` | Bridge (Bluetooth + Arduino + autonomy) |
| `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` | YOLO + camera stream |

---

## What to Remove or Archive

| Path | Action |
|------|--------|
| `/home/pi/ecosweep_bridge.py` | Old bridge |
| `/home/pi/ecosweep_fpv.py` | Old FPV |
| `/home/pi/ecosweep_stable.py` | Old |
| `/home/pi/ecosweep_usb.py` | Old |
| `/home/pi/ecosweep-phase1/` | Old phase |
| `/home/pi/ecosweep-phase2/yolo_fpv_stream.py` | Old YOLO |
| `/home/pi/ecosweep-phase2/yolo_fpv_stream.py.save` | Backup (can remove) |
| `/home/pi/ecosweep-phase3/` | Old phase |
| `/home/pi/ecosweep/` | Empty or redundant |
| `/home/pi/ai_core/ecosweep_master.py` | Check if needed for AI; if not, archive |

---

## Step 1: Create Archive (Safe First)

Run on Pi. This moves old files into an archive folder instead of deleting.

```bash
mkdir -p /home/pi/ecosweep_archive

mv /home/pi/ecosweep_bridge.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep_fpv.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep_stable.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep_usb.py /home/pi/ecosweep_archive/

mv /home/pi/ecosweep-phase1 /home/pi/ecosweep_archive/
mv /home/pi/ecosweep-phase3 /home/pi/ecosweep_archive/
mv /home/pi/ecosweep /home/pi/ecosweep_archive/ 2>/dev/null || true

mv /home/pi/ecosweep-phase2/yolo_fpv_stream.py /home/pi/ecosweep_archive/ 2>/dev/null || true
mv /home/pi/ecosweep-phase2/yolo_fpv_stream.py.save /home/pi/ecosweep_archive/ 2>/dev/null || true
```

---

## Step 2: Final Layout (After Cleanup)

```
/home/pi/
├── ecosweep_manual_final.py          ← Bridge
├── ecosweep-phase2/
│   └── yolo_fpv_stream_optimized.py  ← YOLO
├── ecosweep-phase2/systemd/          ← Create for service files
│   ├── ecosweep-yolo.service
│   └── ecosweep-bridge.service
└── ecosweep_archive/                 ← Old files (can delete later)
```

---

## Step 3: Create systemd Folder and Services

```bash
mkdir -p /home/pi/ecosweep-phase2/systemd
```

Then create the two service files as in [ECOSWEEP-PI-FIX-LAYOUT.md](ECOSWEEP-PI-FIX-LAYOUT.md) (Step 3.2 and 3.3).

---

## Step 4: (Optional) Delete Archive Later

After everything works for a while:

```bash
rm -rf /home/pi/ecosweep_archive
```

---

## Summary — Run These on Pi

```bash
# 1. Archive old files
mkdir -p /home/pi/ecosweep_archive
mv /home/pi/ecosweep_bridge.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep_fpv.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep_stable.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep_usb.py /home/pi/ecosweep_archive/
mv /home/pi/ecosweep-phase1 /home/pi/ecosweep_archive/
mv /home/pi/ecosweep-phase3 /home/pi/ecosweep_archive/
mv /home/pi/ecosweep /home/pi/ecosweep_archive/ 2>/dev/null || true
mv /home/pi/ecosweep-phase2/yolo_fpv_stream.py /home/pi/ecosweep_archive/ 2>/dev/null || true
mv /home/pi/ecosweep-phase2/yolo_fpv_stream.py.save /home/pi/ecosweep_archive/ 2>/dev/null || true

# 2. Create systemd folder
mkdir -p /home/pi/ecosweep-phase2/systemd

# 3. Verify what remains
ls -la /home/pi/ecosweep_manual_final.py
ls -la /home/pi/ecosweep-phase2/
ls -la /home/pi/ecosweep_archive/
```

**Note:** Leave `/home/pi/ai_core/` as is unless you are sure it is not used.
