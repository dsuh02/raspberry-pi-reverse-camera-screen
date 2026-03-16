# Pi Dash UI + Reverse Camera Overlay (Lexus CT200h)

This repo contains a Raspberry Pi–based always-on dash system:
- A **dash UI app** (base layer) that is always visible.
- A **reverse camera overlay service** that detects when the CVBS camera feed is alive and temporarily pops the camera on top of the UI.

The system is designed for an appliance-like boot flow (no full desktop required).

---

## Hardware / Platform

- Vehicle: Lexus CT200h
- Raspberry Pi 4B (2GB)
- 4.3" DSI capacitive touch display, 800×480
- USB CVBS capture dongle receiving reverse camera via RCA (appears as `/dev/video0`)
- Power: ACC fuse tap → 12V→5.2V buck (+ TVS protection, etc.)
- OS: Raspberry Pi OS (Debian trixie-based)
- Display stack: DRM/KMS (`kmssink`), DSI connector `DSI-1`, connector-id typically **47**

---

## Repository layout (suggested)

```
raspberry-pi-reverse-camera-screen/
  reversecam_overlay.py
  services/
    reversecam-overlay.service
    dash-ui.service                # to be created
  app/
    (dash UI app sources go here)
  docs/
    reversecam_overlay_README.md   # optional if you prefer separate doc
```

---

## High-level architecture

### 1) Reverse camera overlay (always-on service)
The overlay is an always-running GStreamer pipeline that:
- Opens `/dev/video0` exactly once
- Tees frames to:
  - `kmssink` for display (fullscreen overlay)
  - `appsink` for analysis (detects alive vs dead/no-signal)

Why this matters:
- Many CVBS dongles keep producing frames even when “no signal”
- `/dev/video0` is often exclusive; separate OpenCV watchdog + gst display tends to fight for access

Overlay show/hide:
- When ALIVE → set `kmssink` render-rectangle to `0,0,800,480`
- When DEAD → move render-rectangle offscreen (overlay hidden)
- The dash UI remains visible underneath at all times

### 2) Dash UI app (always-on base layer)
The dash UI app is a separate process/service that runs continuously and renders the base UI. The reverse camera overlay sits “above it” when visible.

The camera overlay should not require the UI app to do anything special (no tight coupling).

---

## Shared “language” / stack recommendations

### System-level conventions
- Use **systemd services** for both overlay and UI app
- Log to **journald** (stdout/stderr → `journalctl`)
- Prefer a consistent runtime:
  - Overlay uses **system Python (`/usr/bin/python3`)** because GI/GStreamer bindings are installed via apt.
  - UI app can use whatever is best, but should fit the same appliance boot style.

### Display stack alignment
- The overlay uses DRM/KMS via `kmssink`.
- The UI app should ideally render in a way that plays well with KMS:
  - Avoid having multiple components fight over the same DRM resources.
  - If using a compositor/kiosk browser, plan around that early (tradeoffs below).

### UI tech options (choose one)
**Option A: Native UI app (Qt / SDL / DRM/KMS)**
- Best for appliance feel and minimal overhead.
- Can run without a full desktop.
- Clean layering with KMS overlay approach.

**Option B: Web UI (Chromium kiosk)**
- Fast to develop, but heavier.
- Might require a windowing/compositor layer depending on setup.
- Still compatible with camera overlay, but be mindful of how planes/compositing behave.

**Option C: Python UI**
- Useful if you want to share Python tooling/logging, but choose a rendering approach that doesn’t require a full desktop unless you accept that tradeoff.

---

## Reverse camera overlay: install + run

### Dependencies
```bash
sudo apt update
sudo apt install -y \
  python3-gi \
  python3-gst-1.0 \
  gir1.2-gstreamer-1.0 \
  gir1.2-gst-plugins-base-1.0 \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good
```

### Install service
Copy `services/reversecam-overlay.service` to `/etc/systemd/system/` and enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now reversecam-overlay.service
```

Logs:
```bash
sudo journalctl -u reversecam-overlay.service -f -o short-iso
```

---

## Dash UI app: how it should be deployed

Create a separate systemd service (example name: `dash-ui.service`) that:
- starts after boot,
- restarts on failure,
- logs to journald,
- is always running.

The reverse camera overlay is independent: it will hide/show itself based on camera feed content.

---

## Operational commands

### See what’s holding `/dev/video0`
```bash
sudo fuser -v /dev/video0 || true
sudo lsof /dev/video0 || true
```

### Service status / logs
```bash
systemctl status reversecam-overlay.service --no-pager -l
sudo journalctl -u reversecam-overlay.service -n 200 --no-pager
```

---

## Notes / gotchas discovered

- `kmssink` negotiation on this system prefers caps locked to 800×480; crop/scale should happen upstream so the sink receives exactly 800×480.
- Many dongles output flat color when no signal (mean ~16, std ~0). Detection should account for “flat frames” (stddev-alive threshold) not just “near-zero black.”

---

## Next steps (UI app)
- Decide UI stack (native vs kiosk vs python) based on boot simplicity and performance.
- Ensure UI runs as the base layer and remains visible when camera overlay is hidden.
- Keep services clean:
  - one service owns camera capture (`reversecam-overlay.service`)
  - one service owns UI (`dash-ui.service`)
