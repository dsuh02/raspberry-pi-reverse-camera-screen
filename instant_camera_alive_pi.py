#!/usr/bin/env python3
"""
instant_camera_alive_pi.py

Raspberry Pi (Linux) instant camera-alive detector for a USB composite capture device (/dev/videoX).

Design goals:
- Keep the capture device open (no polling by spawning processes).
- Detect DEAD->ALIVE as fast as possible (typically 1–2 frames).
- Detect ALIVE->DEAD quickly but without flicker.
- Works well with "OFF = solid black" and "ON = real video" cases.

Requirements:
  sudo apt install -y python3-opencv python3-numpy
  (or use a venv and pip install opencv-python numpy)

Usage:
  python3 instant_camera_alive_pi.py --device /dev/video0 --dashboard
  python3 instant_camera_alive_pi.py --device /dev/video0            # event mode (prints on state changes)

Tips:
  - Find device: v4l2-ctl --list-devices ; ls /dev/video*
  - Preview: ffplay /dev/video0
"""

import argparse
import sys
import time

import cv2
import numpy as np


def is_black_frame(gray_small: np.ndarray, mean_thr: float, std_thr: float) -> bool:
    mean = float(gray_small.mean())
    std = float(gray_small.std())
    return (mean < mean_thr) and (std < std_thr)


class AliveDetector:
    """
    Asymmetric hysteresis detector:
      - DEAD -> ALIVE: instant on first "alive evidence"
      - ALIVE -> DEAD: requires dead_off_n consecutive "dead evidence" and optional hold time
    Evidence rule:
      - alive_evidence_fast = (not black) OR (diff >= diff_thresh)
    """

    def __init__(
        self,
        downsample: int = 8,
        diff_thresh: float = 0.20,
        black_mean_thr: float = 1.0,
        black_std_thr: float = 0.2,
        stale_ms: int = 250,
        dead_off_n: int = 3,
        hold_alive_s: float = 0.0,
    ):
        self.downsample = downsample
        self.diff_thresh = diff_thresh
        self.black_mean_thr = black_mean_thr
        self.black_std_thr = black_std_thr
        self.stale_ms = stale_ms
        self.dead_off_n = dead_off_n
        self.hold_alive_s = hold_alive_s

        self.prev_small: np.ndarray | None = None
        self.last_frame_time: float = 0.0
        self.last_alive_evidence_t: float = 0.0
        self.dead_conf: int = 0
        self.status: str = "DEAD"

        # last computed stats
        self.mean: float | None = None
        self.std: float | None = None
        self.diff: float | None = None
        self.black: bool = True

    def update(self, gray: np.ndarray, now: float) -> str:
        """Update detector with a new grayscale frame. Returns current status."""
        self.last_frame_time = now

        # Downsample for speed
        small = gray[:: self.downsample, :: self.downsample]

        # Stats
        self.mean = float(small.mean())
        self.std = float(small.std())
        self.black = is_black_frame(small, self.black_mean_thr, self.black_std_thr)

        # Temporal diff
        self.diff = None
        if self.prev_small is not None and self.prev_small.shape == small.shape:
            self.diff = float(np.mean(np.abs(small.astype(np.int16) - self.prev_small.astype(np.int16))))
        self.prev_small = small

        # Fast-rise evidence
        alive_evidence_fast = (not self.black) or (self.diff is not None and self.diff >= self.diff_thresh)

        if alive_evidence_fast:
            self.last_alive_evidence_t = now
            self.dead_conf = 0
        else:
            self.dead_conf += 1

        # State machine
        if self.status == "DEAD":
            if alive_evidence_fast:
                self.status = "ALIVE"
                self.dead_conf = 0
        else:
            if (now - self.last_alive_evidence_t) >= self.hold_alive_s and self.dead_conf >= self.dead_off_n:
                self.status = "DEAD"

        return self.status

    def update_stale(self, now: float) -> str:
        """Call when we fail to read frames; enforces stale timeout."""
        if self.last_frame_time == 0.0:
            # never received a frame => stay dead
            self.status = "DEAD"
            return self.status

        age_ms = (now - self.last_frame_time) * 1000.0
        if age_ms > self.stale_ms:
            self.status = "DEAD"
            # reset evidence counters so we can rise instantly when frames return
            self.dead_conf = 0
            self.prev_small = None
        return self.status

    def age_ms(self, now: float) -> float | None:
        if self.last_frame_time == 0.0:
            return None
        return (now - self.last_frame_time) * 1000.0


def open_capture(device: str, width: int | None, height: int | None, fps: int | None) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps:
        cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def main():
    ap = argparse.ArgumentParser(description="Instant camera alive detector (Raspberry Pi / Linux / V4L2)")
    ap.add_argument("--device", default="/dev/video0", help="V4L2 device path, e.g. /dev/video0")
    ap.add_argument("--width", type=int, default=640, help="Requested capture width (best-effort)")
    ap.add_argument("--height", type=int, default=480, help="Requested capture height (best-effort)")
    ap.add_argument("--fps", type=int, default=30, help="Requested FPS (best-effort)")

    ap.add_argument("--downsample", type=int, default=8)
    ap.add_argument("--diff_thresh", type=float, default=0.20)

    ap.add_argument("--black_mean_thr", type=float, default=1.0, help="Mean threshold for 'black/off' frame")
    ap.add_argument("--black_std_thr", type=float, default=0.2, help="Stddev threshold for 'black/off' frame")

    ap.add_argument("--stale_ms", type=int, default=250, help="No frames for this long => DEAD")
    ap.add_argument("--dead_off_n", type=int, default=3, help="Consecutive dead evidences to switch ALIVE->DEAD")
    ap.add_argument("--hold_alive_s", type=float, default=0.0, help="Hold ALIVE at least this long since last alive evidence")

    ap.add_argument("--dashboard", action="store_true", help="Live updating single-line dashboard")
    ap.add_argument("--interval", type=float, default=0.02, help="UI update interval seconds (0 = as fast as possible)")
    ap.add_argument("--show", action="store_true", help="Show preview window (requires desktop); ESC to exit")

    args = ap.parse_args()

    cap = open_capture(args.device, args.width, args.height, args.fps)
    if not cap.isOpened():
        print(f"ERROR: Could not open {args.device}", file=sys.stderr)
        print("Tip: v4l2-ctl --list-devices ; ls /dev/video*", file=sys.stderr)
        sys.exit(1)

    det = AliveDetector(
        downsample=args.downsample,
        diff_thresh=args.diff_thresh,
        black_mean_thr=args.black_mean_thr,
        black_std_thr=args.black_std_thr,
        stale_ms=args.stale_ms,
        dead_off_n=args.dead_off_n,
        hold_alive_s=args.hold_alive_s,
    )

    # FPS measurement (actual)
    last_frames = 0
    last_t = time.time()
    fps_meas = 0.0
    frames_total = 0

    prev_status = None

    try:
        while True:
            now = time.time()
            ok, frame = cap.read()

            if ok and frame is not None:
                frames_total += 1

                # Measure FPS over sliding-ish window
                dt = now - last_t
                if dt >= 0.25:
                    df = frames_total - last_frames
                    fps_meas = (df / dt) if dt > 0 else fps_meas
                    last_frames = frames_total
                    last_t = now

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                status = det.update(gray, now)

                if args.show:
                    cv2.imshow("capture", frame)
                    if (cv2.waitKey(1) & 0xFF) == 27:  # ESC
                        break

            else:
                # no frame read: apply stale logic
                status = det.update_stale(now)

            # Output
            age_ms = det.age_ms(now)
            age_txt = "N/A" if age_ms is None else f"{age_ms:0.0f}ms"
            mean_txt = "N/A" if det.mean is None else f"{det.mean:0.1f}"
            std_txt = "N/A" if det.std is None else f"{det.std:0.2f}"
            diff_txt = "N/A" if det.diff is None else f"{det.diff:0.3f}"

            if args.dashboard:
                line = (
                    f"STATUS={status:<5} age={age_txt:<6} fps={fps_meas:0.1f} frames={frames_total:<8} "
                    f"mean={mean_txt:<6} std={std_txt:<6} diff={diff_txt:<7} black={str(det.black):<5} "
                    f"deadN={det.dead_conf:<2}"
                )
                sys.stdout.write("\r" + line + " " * 10)
                sys.stdout.flush()
            else:
                # event mode: print only on status changes
                if status != prev_status:
                    print(f"{time.strftime('%H:%M:%S')} {status} (diff={det.diff})")
                    prev_status = status

            if args.interval > 0:
                time.sleep(args.interval)

    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()