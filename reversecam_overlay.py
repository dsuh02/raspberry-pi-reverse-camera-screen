#!/usr/bin/env python3
import argparse
import sys
import time

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GstApp, GLib  # noqa: E402

import numpy as np  # noqa: E402

Gst.init(None)

def has_prop(obj, name: str) -> bool:
    return obj.find_property(name) is not None

class AliveDetector:
    """
    Similar to your OpenCV detector, but runs on appsink frames.
    DEAD->ALIVE fast, ALIVE->DEAD with hysteresis.
    """
    def __init__(
        self,
        diff_thresh: float = 0.20,
        black_mean_thr: float = 1.0,
        black_std_thr: float = 0.2,
        std_alive_thr: float = 3.0,
        dead_off_n: int = 3,
        hold_alive_s: float = 0.0,
    ):
        self.diff_thresh = diff_thresh
        self.black_mean_thr = black_mean_thr
        self.black_std_thr = black_std_thr
        self.std_alive_thr = std_alive_thr
        self.dead_off_n = dead_off_n
        self.hold_alive_s = hold_alive_s

        self.prev: np.ndarray | None = None
        self.dead_conf = 0
        self.status = "DEAD"
        self.last_alive_evidence_t = 0.0

        self.mean = None
        self.std = None
        self.diff = None
        self.black = True

    def update(self, gray_small: np.ndarray, now: float) -> str:
        self.mean = float(gray_small.mean())
        self.std = float(gray_small.std())
        self.black = (self.mean < self.black_mean_thr) and (self.std < self.black_std_thr)

        self.diff = None
        if self.prev is not None and self.prev.shape == gray_small.shape:
            self.diff = float(np.mean(np.abs(gray_small.astype(np.int16) - self.prev.astype(np.int16))))
        self.prev = gray_small

        alive_evidence_fast = ((self.std is not None and self.std >= self.std_alive_thr) or (self.diff is not None and self.diff >= self.diff_thresh))

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

def parse_render_rect(s: str):
    # Accept "x,y,w,h" or "<(gint)x,(gint)y,(gint)w,(gint)h>"
    s = s.strip()
    if s.startswith("<") and s.endswith(">"):
        s = s[1:-1]
    s = s.replace("(gint)", "").replace(" ", "")
    parts = s.split(",")
    if len(parts) != 4:
        raise ValueError("render-rectangle must be 4 ints: x,y,w,h")
    return tuple(int(p) for p in parts)

class OverlayController:
    def __init__(self, kmssink, show_rect, hide_mode: str):
        self.kmssink = kmssink
        self.show_rect = show_rect  # (x,y,w,h)
        self.hide_mode = hide_mode  # "alpha" or "offscreen"
        self.visible = False

        # Determine supported hide method
        self.can_alpha = has_prop(self.kmssink, "alpha")
        # Some builds use "plane-alpha" or "global-alpha" (rare). We try alpha first.
        self.alpha_prop = "alpha" if self.can_alpha else None

    def set_visible(self, want_visible: bool):
        if want_visible == self.visible:
            return
        if want_visible:
            # show
            if self.hide_mode == "alpha" and self.alpha_prop:
                self.kmssink.set_property(self.alpha_prop, 1.0)
            else:
                x, y, w, h = self.show_rect
                self.kmssink.set_property("render-rectangle", [x, y, w, h])
            self.visible = True
        else:
            # hide
            if self.hide_mode == "alpha" and self.alpha_prop:
                self.kmssink.set_property(self.alpha_prop, 0.0)
            else:
                # Move it offscreen; keep size to avoid renegotiation
                x, y, w, h = self.show_rect
                off = (2000, 2000, w, h)
                x, y, w, h = off
                self.kmssink.set_property("render-rectangle", [x, y, w, h])
            self.visible = False

def build_pipeline(args):
    # Branch A: display (NV12 800x480) -> kmssink
    # Branch B: analysis -> GRAY8 small -> appsink
    #
    # Use your crop params, and force 800x480 to satisfy kmssink path caps.
    pipeline_desc = f"""
        v4l2src device={args.device} io-mode={args.io_mode} !
          video/x-raw,format=YUY2,width=720,height=480,framerate=30/1 !
          queue max-size-buffers=1 leaky=downstream !
          videocrop left={args.crop_left} right={args.crop_right} top={args.crop_top} bottom={args.crop_bottom} !
          videoconvert ! videoscale !
          video/x-raw,format=NV12,width={args.out_w},height={args.out_h} !
          tee name=t

        t. ! queue max-size-buffers=1 leaky=downstream !
          kmssink name=kmss sync=false connector-id={args.connector_id} force-modesetting=true

        t. ! queue max-size-buffers=1 leaky=downstream !
          videoconvert !
          videoscale !
          video/x-raw,format=GRAY8,width={args.an_w},height={args.an_h} !
          appsink name=apps emit-signals=true max-buffers=1 drop=true sync=false
    """
    pipeline = Gst.parse_launch(pipeline_desc)
    kmss = pipeline.get_by_name("kmss")
    apps = pipeline.get_by_name("apps")
    return pipeline, kmss, apps

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="/dev/video0")
    ap.add_argument("--connector-id", type=int, default=47)
    ap.add_argument("--io-mode", type=int, default=2)

    ap.add_argument("--crop-left", type=int, default=8)
    ap.add_argument("--crop-right", type=int, default=8)
    ap.add_argument("--crop-top", type=int, default=29)
    ap.add_argument("--crop-bottom", type=int, default=29)

    ap.add_argument("--out-w", type=int, default=800)
    ap.add_argument("--out-h", type=int, default=480)

    # analysis stream size (small = fast)
    ap.add_argument("--an-w", type=int, default=96)
    ap.add_argument("--an-h", type=int, default=64)

    # detection thresholds
    ap.add_argument("--diff-thresh", type=float, default=0.20)
    ap.add_argument("--std-alive-thr", type=float, default=3.0, help="Stddev threshold to consider feed alive (filters flat no-signal screens)")
    ap.add_argument("--black-mean-thr", type=float, default=1.0)
    ap.add_argument("--black-std-thr", type=float, default=0.2)
    ap.add_argument("--dead-off-n", type=int, default=3)
    ap.add_argument("--hold-alive-s", type=float, default=0.0)

    # overlay behavior
    ap.add_argument("--show-rect", default="0,0,800,480", help="x,y,w,h on the screen when visible")
    ap.add_argument("--hide-mode", choices=["auto", "alpha", "offscreen"], default="auto")
    ap.add_argument("--alive-on-n", type=int, default=2, help="Require N consecutive ALIVE to show overlay")
    ap.add_argument("--dead-off-n2", type=int, default=6, help="Require N consecutive DEAD to hide overlay")

    ap.add_argument("--log-every", type=float, default=0.25)

    args = ap.parse_args()

    show_rect = parse_render_rect(args.show_rect)

    pipeline, kmss, apps = build_pipeline(args)
    if kmss is None or apps is None:
        print("ERROR: failed to create kmssink/appsink from pipeline", file=sys.stderr)
        sys.exit(1)

    # Choose hide method
    can_alpha = has_prop(kmss, "alpha")
    if args.hide_mode == "auto":
        hide_mode = "alpha" if can_alpha else "offscreen"
    else:
        hide_mode = args.hide_mode
        if hide_mode == "alpha" and not can_alpha:
            print("WARN: kmssink has no 'alpha' property; falling back to offscreen", file=sys.stderr)
            hide_mode = "offscreen"

    overlay = OverlayController(kmss, show_rect, hide_mode)

    det = AliveDetector(
        diff_thresh=args.diff_thresh,
        black_mean_thr=args.black_mean_thr,
        black_std_thr=args.black_std_thr,
        std_alive_thr=args.std_alive_thr,
        dead_off_n=args.dead_off_n,
        hold_alive_s=args.hold_alive_s,
    )

    alive_streak = 0
    dead_streak = 0
    last_log = 0.0

    def on_sample(appsink: GstApp.AppSink):
        nonlocal alive_streak, dead_streak, last_log
        sample = appsink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.OK

        buf = sample.get_buffer()
        # Appsink caps are forced in pipeline; avoid GI StructureWrapper differences

        w = args.an_w

        h = args.an_h

        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.OK
        try:
            data = mapinfo.data  # bytes-like
            # GRAY8: size = w*h
            arr = np.frombuffer(data, dtype=np.uint8)
            if arr.size >= w * h:
                gray = arr[: w * h].reshape((h, w))
            else:
                return Gst.FlowReturn.OK
        finally:
            buf.unmap(mapinfo)

        now = time.time()
        status = det.update(gray, now)

        if status == "ALIVE":
            alive_streak += 1
            dead_streak = 0
        else:
            dead_streak += 1
            alive_streak = 0

        # Show/hide with hysteresis
        if alive_streak >= args.alive_on_n:
            overlay.set_visible(True)
        if dead_streak >= args.dead_off_n2:
            overlay.set_visible(False)

        # Periodic logging
        if (now - last_log) >= args.log_every:
            last_log = now
            print(
                f"[overlay] status={status} vis={overlay.visible} aliveN={alive_streak} deadN={dead_streak} "
                f"mean={det.mean:.2f} std={det.std:.2f} diff={(det.diff if det.diff is not None else None)} "
                f"black={det.black} hide_mode={overlay.hide_mode}",
                flush=True,
            )

        return Gst.FlowReturn.OK

    apps.connect("new-sample", on_sample)

    # Start hidden until proven alive
    overlay.set_visible(False)

    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: pipeline failed to start", file=sys.stderr)
        sys.exit(1)

    # Bus watch for errors
    bus = pipeline.get_bus()
    bus.add_signal_watch()

    def on_bus_message(bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, dbg = message.parse_error()
            print(f"[overlay] GST ERROR: {err} debug={dbg}", file=sys.stderr, flush=True)
        elif t == Gst.MessageType.EOS:
            print("[overlay] GST EOS", flush=True)

    bus.connect("message", on_bus_message)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()
