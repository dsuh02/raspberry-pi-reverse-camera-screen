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

New machine-readable modes for watchdogs:
  python3 instant_camera_alive_pi.py --device /dev/video0 --once-json
  python3 instant_camera_alive_pi.py --device /dev/video0 --once-kv
"""

import argparse
import json
import sys
import time
from typing import Optional

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

        self.prev_small: Optional[np.ndarray] = None
        self.last_frame_time: float = 0.0
        self.last_alive_evidence_t: float = 0.0
        self.dead_conf: int = 0
        self.status: str = "DEAD"

        # last computed stats
        self.mean: Optional[float] = None
        self.std: Optional[float] = None
        self.diff: Optional[float] = None
        self.black: bool = True
        self.last_alive_evidence_fast: bool = False

    def update(self, gray: np.ndarray, now: float) -> str:
        self.last_frame_time = now

        small = gray[:: self.downsample, :: self.downsample]

        self.mean = float(small.mean())
        self.std = float(small.std())
        self.black = is_black_frame(small, self.black_mean_thr, self.black_std_thr)

        self.diff = None
        if self.prev_small is not None and self.prev_small.shape == small.shape:
            self.diff = float(np.mean(np.abs(small.astype(np.int16) - self.prev_small.astype(np.int16))))
        self.prev_small = small

        alive_evidence_fast = (not self.black) or (self.diff is not None and self.diff >= self.diff_thresh)
        self.last_alive_evidence_fast = bool(alive_evidence_fast)

        if alive_evidence_fast:
            self.last_alive_evidence_t = now
            self.dead_conf = 0
        else:
            self.dead_conf += 1

        if self.status == "DEAD":
            if alive_evidence_fast:
                self.status = "ALIVE"
                self.dead_conf = 0
        else:
            if (now - self.last_alive_evidence_t) >= self.hold_alive_s and self.dead_conf >= self.dead_off_n:
                self.status = "DEAD"

        return self.status

    def update_stale(self, now: float) -> str:
        if self.last_frame_time == 0.0:
            self.status = "DEAD"
            return self.status

        age_ms = (now - self.last_frame_time) * 1000.0
        if age_ms > self.stale_ms:
            self.status = "DEAD"
            self.dead_conf = 0
            self.prev_small = None
            self.diff = None
            self.mean = None
            self.std = None
            self.black = True
            self.last_alive_evidence_fast = False
        return self.status

    def age_ms(self, now: float) -> Optional[float]:
        if self.last_frame_time == 0.0:
            return None
        return (now - self.last_frame_time) * 1000.0


def open_capture(device: str, width: Optional[int], height: Optional[int], fps: Optional[int]) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps:
        cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def _fmt_float(v: Optional[float], fmt: str) -> str:
    return "N/A" if v is None else format(v, fmt)


def _reason(status: str, black: bool, diff: Optional[float], diff_thresh: float, stale: bool) -> str:
    if stale:
        return "stale_timeout"
    if status == "ALIVE":
        if not black:
            return "not_black"
        if diff is not None and diff >= diff_thresh:
            return "diff_high"
        return "alive"
    if black and (diff is None or diff < diff_thresh):
        return "black_or_diff_low"
    return "dead"


def main():
    ap = argparse.ArgumentParser(description="Instant camera alive detector (Raspberry Pi / Linux / V4L2)")
    ap.add_argument("--device", default="/dev/video0")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=30)

    ap.add_argument("--downsample", type=int, default=8)
    ap.add_argument("--diff_thresh", type=float, default=0.20)

    ap.add_argument("--black_mean_thr", type=float, default=1.0)
    ap.add_argument("--black_std_thr", type=float, default=0.2)

    ap.add_argument("--stale_ms", type=int, default=250)
    ap.add_argument("--dead_off_n", type=int, default=3)
    ap.add_argument("--hold_alive_s", type=float, default=0.0)

    ap.add_argument("--dashboard", action="store_true")
    ap.add_argument("--interval", type=float, default=0.02)
    ap.add_argument("--show", action="store_true")

    # machine-readable + debug
    ap.add_argument("--once-json", action="store_true", help="Print one JSON status line and exit")
    ap.add_argument("--once-kv", action="store_true", help="Print one KEY=VALUE status line and exit")
    ap.add_argument("--debug", action="store_true", help="Emit newline debug logs even with --dashboard")
    ap.add_argument("--log-every", type=float, default=0.0, help="Emit a newline status line every N seconds")

    args = ap.parse_args()
    if args.once_json and args.once_kv:
        print("ERROR: choose only one of --once-json or --once-kv", file=sys.stderr)
        sys.exit(2)

    cap = open_capture(args.device, args.width, args.height, args.fps)
    if not cap.isOpened():
        print(f"ERROR: Could not open {args.device}", file=sys.stderr)
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

    last_frames = 0
    last_t = time.time()
    fps_meas = 0.0
    frames_total = 0

    prev_status = None
    last_log_t = 0.0

    def emit_newline(status: str, age_ms: Optional[float], stale: bool):
        age_txt = "N/A" if age_ms is None else f"{age_ms:0.0f}ms"
        mean_txt = _fmt_float(det.mean, "0.1f")
        std_txt = _fmt_float(det.std, "0.2f")
        diff_txt = _fmt_float(det.diff, "0.3f")
        reason = _reason(status, det.black, det.diff, args.diff_thresh, stale)
        print(
            f"{time.strftime('%H:%M:%S')} STATUS={status} age={age_txt} fps={fps_meas:0.1f} frames={frames_total} "
            f"mean={mean_txt} std={std_txt} diff={diff_txt} black={det.black} deadN={det.dead_conf} reason={reason}",
            flush=True,
        )

    def emit_once(status: str, age_ms: Optional[float], stale: bool):
        payload = {
            "ts": time.time(),
            "device": args.device,
            "status": status,
            "alive": (status == "ALIVE"),
            "age_ms": None if age_ms is None else float(age_ms),
            "fps_meas": float(fps_meas),
            "frames_total": int(frames_total),
            "mean": det.mean,
            "std": det.std,
            "diff": det.diff,
            "black": bool(det.black),
            "dead_conf": int(det.dead_conf),
            "alive_evidence_fast": bool(det.last_alive_evidence_fast),
            "reason": _reason(status, det.black, det.diff, args.diff_thresh, stale),
            "stale": bool(stale),
        }

        if args.once_json:
            print(json.dumps(payload), flush=True)
        else:
            def kv(k, v):
                if v is None:
                    return f"{k}=N/A"
                if isinstance(v, bool):
                    return f"{k}={'true' if v else 'false'}"
                if isinstance(v, float):
                    return f"{k}={v:.3f}"
                return f"{k}={v}"
            print(" ".join(kv(k, payload[k]) for k in payload.keys()), flush=True)

    try:
        while True:
            now = time.time()
            ok, frame = cap.read()
            stale = False

            if ok and frame is not None:
                frames_total += 1

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
                    if (cv2.waitKey(1) & 0xFF) == 27:
                        break
            else:
                stale = True
                status = det.update_stale(now)

            age_ms = det.age_ms(now)

            if args.once_json or args.once_kv:
                emit_once(status, age_ms, stale)
                return

            if args.log_every and args.log_every > 0 and (now - last_log_t) >= args.log_every:
                emit_newline(status, age_ms, stale)
                last_log_t = now

            if args.dashboard:
                age_txt = "N/A" if age_ms is None else f"{age_ms:0.0f}ms"
                mean_txt = _fmt_float(det.mean, "0.1f")
                std_txt = _fmt_float(det.std, "0.2f")
                diff_txt = _fmt_float(det.diff, "0.3f")
                reason = _reason(status, det.black, det.diff, args.diff_thresh, stale)

                line = (
                    f"STATUS={status:<5} age={age_txt:<6} fps={fps_meas:0.1f} frames={frames_total:<8} "
                    f"mean={mean_txt:<6} std={std_txt:<6} diff={diff_txt:<7} black={str(det.black):<5} "
                    f"deadN={det.dead_conf:<2} reason={reason}"
                )
                sys.stdout.write("\r" + line + " " * 10)
                sys.stdout.flush()

                if args.debug and status != prev_status:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    emit_newline(status, age_ms, stale)
                    prev_status = status
            else:
                if status != prev_status:
                    emit_newline(status, age_ms, stale)
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
