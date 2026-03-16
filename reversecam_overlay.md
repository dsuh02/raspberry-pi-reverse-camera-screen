# Reverse Camera Overlay (Pi DSI + USB CVBS)

Always-on reverse camera overlay for a Raspberry Pi dash setup. It keeps the dash UI visible underneath, and “pops” the camera feed on top when the CVBS feed looks alive. When the feed looks dead/no-signal (often a flat gray/blue frame from the USB dongle), it hides the overlay.

## Hardware / Environment

- Raspberry Pi 4B (2GB)
- 4.3" DSI capacitive touch display, 800×480 @ ~60 Hz
- USB CVBS capture dongle (reverse camera via yellow RCA), appears as `/dev/video0`
- DRM/KMS display stack via `kmssink`
- DSI connector: `DSI-1`, `connector-id=47` (verified via `modetest -c`)
- OS: Raspberry Pi OS (Debian trixie-based)

## Why this design

The USB capture device is often present and streaming even when the camera signal is “off” (no-signal screen / flat color). Also, `/dev/video0` is typically **exclusive access**: you can’t reliably open it from OpenCV while a GStreamer pipeline is already using it.

So this overlay is implemented as a **single GStreamer pipeline** that:
- opens `/dev/video0` exactly once,
- **tees** frames to:
  1) `kmssink` (display branch) for fullscreen overlay
  2) `appsink` (analysis branch) for camera-alive detection in-process

The overlay is hidden/shown without stopping the pipeline:
- show: move `kmssink` `render-rectangle` to `0,0,800,480`
- hide: move `render-rectangle` offscreen (e.g., `2000,2000,800,480`)

This keeps the base UI always visible.

## Dependencies (apt)

Install GStreamer + GI bindings:

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

Optional (only if you later see “missing element” errors):
```bash
sudo apt install -y gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
```

Note: This overlay should run with **system Python** (`/usr/bin/python3`) because `gi` is installed via apt.

## How it works (pipeline + detection)

### Pipeline
- Input: `v4l2src device=/dev/video0 io-mode=2` with `YUY2 720×480@30`
- Crop: `videocrop left=8 right=8 top=29 bottom=29`
- Convert/scale: `videoconvert ! videoscale`
- Display branch:
  - force caps to `NV12 800×480` for `kmssink`
- Analysis branch:
  - convert/scale to `GRAY8` at a small size (e.g. 96×64)
  - `appsink` consumes frames for detection

### Detection rule (high level)
CVBS dongles often output a **flat “no signal” frame** (example: mean ~16, std ~0). So “black-only” detection is not sufficient.

The overlay uses a **stddev-alive threshold**:
- ALIVE evidence when `std >= std_alive_thr` OR `diff >= diff_thresh`
- Hysteresis prevents flicker:
  - `alive_on_n`: consecutive ALIVE frames to show overlay
  - `dead_off_n2`: consecutive DEAD frames to hide overlay

Typical good values for the common flat-gray no-signal case:
- `std_alive_thr=3.0`
- `alive_on_n=2`
- `dead_off_n2=6`

## Manual run (for testing)

Stop anything holding `/dev/video0` first:
```bash
sudo fuser -k /dev/video0 2>/dev/null || true
```

Run:
```bash
sudo /usr/bin/python3 /home/jpi/project/raspberry-pi-reverse-camera-screen/reversecam_overlay.py \
  --device /dev/video0 \
  --connector-id 47 \
  --show-rect 0,0,800,480 \
  --hide-mode offscreen \
  --std-alive-thr 3.0 \
  --diff-thresh 0.20 \
  --alive-on-n 2 \
  --dead-off-n2 6 \
  --log-every 0.25
```

You’ll see log lines like:
- `status=DEAD vis=False ... mean=16 std=0 diff=0` (no-signal)
- `status=ALIVE vis=True ... std≈50+` (real camera feed)

## Systemd service install

Create the service file:

`/etc/systemd/system/reversecam-overlay.service`

```ini
[Unit]
Description=Reverse Camera Overlay (GStreamer capture + in-process signal detection)
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
User=root

# Use system python (gi is installed via apt, not a venv)
ExecStart=/usr/bin/python3 /home/jpi/project/raspberry-pi-reverse-camera-screen/reversecam_overlay.py \
  --device /dev/video0 \
  --connector-id 47 \
  --show-rect 0,0,800,480 \
  --hide-mode offscreen \
  --std-alive-thr 3.0 \
  --diff-thresh 0.20 \
  --alive-on-n 2 \
  --dead-off-n2 6 \
  --log-every 0.25

Restart=always
RestartSec=0.2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable + start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now reversecam-overlay.service
```

### Logs
```bash
sudo journalctl -u reversecam-overlay.service -f -o short-iso
```

### Status
```bash
systemctl status reversecam-overlay.service --no-pager -l
```

## Tuning / Troubleshooting

### Overlay stays visible when camera is off
- Increase `--std-alive-thr` (e.g. 3 → 5)
- Increase `--dead-off-n2` to require more consecutive DEAD frames

### Overlay flickers when camera is on
- Increase `--alive-on-n` (e.g. 2 → 4)

### /dev/video0 “Device or resource busy”
Something else is holding the device:
```bash
sudo fuser -v /dev/video0
```

Stop the culprit service (old gst/watchdog services, etc.).

### Wrong connector id / no output
Confirm connector-id:
```bash
modetest -c | grep -n "DSI" -n
```

### Elements missing
If the script logs missing plugins/elements, install additional gstreamer plugin sets:
```bash
sudo apt install -y gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
```

## Notes for integration with the dash UI app

- The dash UI app should run as a separate always-on service (base layer).
- The overlay service is responsible only for the camera plane visibility.
- When hidden, the camera overlay is moved offscreen; the dash UI remains visible underneath.
