#!/usr/bin/env python
"""check-hook.py -- hard QC on Veo hook clips: no hang, no glitch.

Usage:
    check-hook.py <series>/<slug> [--dir raw|hook] [--step 0.25] [--hang 0.5]
                  [--glitch 5.0] [--fps N] [--root <project root>] [--file <one.mp4>]

Samples every clip every --step seconds and differences consecutive samples
(mean absolute grey, 0-255). Two failures, both hard:

  hang    a run of samples that do not change (< STATIC), lasting --hang
          seconds or more. This is the fault a clip shorter than its beat
          produces once trim-hook holds the last frame, and the one the
          operator sees as "it hangs for two seconds".
  glitch  a single step whose difference exceeds --glitch x the clip's own
          median step and sits above GLITCH_FLOOR: a teleport, a hard cut
          or a element popping in or out mid-clip.

A clip's own median is the baseline, so a fast clip and a slow one are
judged the same way. Prints every clip's numbers, then exits non-zero
naming each failure.
"""
import argparse
import glob
import os
import statistics
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

STATIC = 0.5        # mean abs grey below this = the picture did not change
GLITCH_FLOOR = 18.0  # a spike under this is motion, however sharp the ratio


def samples(path, step, fps):
    """Mean abs grey difference between frames step seconds apart, whole clip."""
    d = tempfile.mkdtemp(prefix="hookqc")
    try:
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", path,
                               "-vf", f"fps={1.0/step},scale=320:-1", "-fps_mode", "passthrough",
                               os.path.join(d, "f%04d.png")])
        from PIL import Image, ImageChops, ImageStat
        fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        out = []
        for a, b in zip(fs, fs[1:]):
            A = Image.open(os.path.join(d, a)).convert("L")
            B = Image.open(os.path.join(d, b)).convert("L")
            out.append(ImageStat.Stat(ImageChops.difference(A, B)).mean[0])
        return out
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)


def runs_of_static(diffs, step):
    """(start_seconds, seconds) for every run of no-change steps."""
    out, i = [], 0
    while i < len(diffs):
        if diffs[i] < STATIC:
            j = i
            while j < len(diffs) and diffs[j] < STATIC:
                j += 1
            out.append((i * step, (j - i) * step))
            i = j
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default="")
    ap.add_argument("--dir", default="staged", choices=["staged", "hook", "raw"])
    ap.add_argument("--staging", default="")
    ap.add_argument("--step", type=float, default=0.25)
    ap.add_argument("--hang", type=float, default=0.5)
    ap.add_argument("--glitch", type=float, default=5.0)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--file", default="")
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
    a = ap.parse_args()

    if a.file:
        clips = [a.file]
    elif a.dir == "staged":
        # the picture that actually ships: place-scenes' clip for each hook scene,
        # card hold and all. Anything else overstates the hang on a card-landing
        # shot, because place-scenes re-times it round the card.
        if not a.staging:
            sys.exit("--dir staged needs --staging <dir>")
        series, slug = a.project.replace("\\", "/").split("/")
        plan = os.path.join(a.root, "content", series, slug, "claude", "hook-plan.md")
        import re as _re
        ids = [l.split("|")[2].strip().strip("`") for l in open(plan, encoding="utf-8")
               if _re.match(r"\|\s*\d+\s*\|", l)]
        clips = [os.path.join(a.staging, "scenes", i + ".mp4") for i in ids]
        missing = [c for c in clips if not os.path.exists(c)]
        if missing:
            sys.exit("not pre-rendered yet: " + ", ".join(os.path.basename(m) for m in missing))
    else:
        series, slug = a.project.replace("\\", "/").split("/")
        base = os.path.join(a.root, "content", series, slug, "hook")
        base = base if a.dir == "hook" else os.path.join(base, "raw")
        clips = sorted(glob.glob(os.path.join(base, "shot-*.mp4")))
    if not clips:
        sys.exit("no clips found")

    fails = []
    for c in clips:
        diffs = samples(c, a.step, a.fps)
        if len(diffs) < 2:
            print(f"{os.path.basename(c)}: too short to judge"); continue
        med = statistics.median(diffs)
        # a static run starting at 0 on a staged clip is the chapter card held over
        # the first frame, which is the design, not a hang.
        hangs = [(s, d) for s, d in runs_of_static(diffs, a.step)
                 if d >= a.hang and not (a.dir == "staged" and s == 0.0)]
        spikes = [(i * a.step, v) for i, v in enumerate(diffs)
                  if med > 0 and v > a.glitch * med and v > GLITCH_FLOOR]
        name = os.path.basename(c)
        mark = "FAIL" if (hangs or spikes) else "ok  "
        print(f"{mark} {name}: {len(diffs)+1} samples, median step {med:.2f}, "
              f"range {min(diffs):.2f}-{max(diffs):.2f}")
        for s, d in hangs:
            print(f"       hang {d:.2f} s from {s:.2f} s (picture static)")
            fails.append(f"{name}: hang of {d:.2f} s at {s:.2f} s")
        for s, v in spikes:
            print(f"       glitch at {s:.2f} s (step {v:.1f} vs median {med:.2f})")
            fails.append(f"{name}: glitch at {s:.2f} s")

    if fails:
        print("\nFAILED:")
        for f in fails:
            print("  " + f)
        return 1
    print("\nno hang, no glitch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
