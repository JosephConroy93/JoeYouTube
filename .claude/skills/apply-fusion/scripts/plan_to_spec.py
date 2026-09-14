#!/usr/bin/env python
"""plan_to_spec.py -- ken-burns-plan.md -> the flat JSON spec apply_baseline.lua reads.

Usage:
    plan_to_spec.py <series>/<slug> --fps N --out <spec.json> [--only 012,044] [--kinds in,out,focal,pan]

Frames come from the plan's `dur` (seconds, frame-exact at the timeline fps). Static rows are
skipped. In = Size 1.00 -> 1.15, Out = 1.15 -> 1.00, pivot at the centre. Focal (x,y) = pivot at
the target, Size 1.00 -> 1.20, EI. Pan (x0,y0)->(x1,y1) = static Size 1.20, Center keyframed from
(x0,y0) to (x1,y1). Every coordinate stays top-left; the Lua does the Fusion Y-flip.
"""
import argparse
import json
import os
import re
import sys

IN, OUT, FOCAL, PAN_SIZE = (1.0, 1.15), (1.15, 1.0), (1.0, 1.2), 1.2
PT = r"\((-?[\d.]+),\s*(-?[\d.]+)\)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma-separated 3-digit scene numbers")
    ap.add_argument("--kinds", default="in,out,focal,pan")
    a = ap.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    plan = os.path.join(root, "content", *a.project.split("/"), "claude", "ken-burns-plan.md")
    kinds = set(a.kinds.split(","))
    only = set(a.only.split(",")) if a.only else None
    scenes, problems = [], []
    for line in open(plan, encoding="utf-8"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 7 or not re.fullmatch(r"`?\d{3}_[A-Za-z0-9-]+`?", c[1]):
            continue
        sid, dur, zoom, ease = c[1].strip("`"), float(c[2]), c[3], c[4]
        if only and sid[:3] not in only:
            continue
        frames = int(round(dur * a.fps))
        rec = {"scene_id": sid, "frames": frames, "ease": ease or "L"}
        kind = zoom.split()[0].lower()
        if kind == "static" or kind not in kinds:
            continue
        if kind in ("in", "out"):
            s0, s1 = IN if kind == "in" else OUT
            rec.update(size_start=s0, size_end=s1, center_x=0.5, center_y=0.5)
        elif kind == "focal":
            m = re.search(PT, zoom)
            rec.update(size_start=FOCAL[0], size_end=FOCAL[1], center_x=float(m.group(1)), center_y=float(m.group(2)))
        elif kind == "pan":
            pts = re.findall(PT, zoom)
            if len(pts) != 2:
                problems.append(f"{sid}: pan needs two points: {zoom}")
                continue
            (x0, y0), (x1, y1) = [(float(x), float(y)) for x, y in pts]
            if PAN_SIZE < 1 + 2 * max(abs(v - 0.5) for v in (x0, y0, x1, y1)) + 0.02:
                problems.append(f"{sid}: pan travel exceeds the Size {PAN_SIZE} headroom")
                continue
            rec.update(pan=1, size_start=PAN_SIZE, size_end=PAN_SIZE, center_x=0.5, center_y=0.5,
                       cx0=x0, cy0=y0, cx1=x1, cy1=y1)
        else:
            problems.append(f"{sid}: unknown zoom {zoom!r}")
            continue
        scenes.append(rec)
    if problems:
        sys.exit("ABORT:\n  " + "\n  ".join(problems))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write('{"expected": %d, "scenes": [\n' % len(scenes))
        f.write(",\n".join("  " + json.dumps(s) for s in scenes))
        f.write("\n]}\n")
    print(f"wrote {len(scenes)} records to {a.out}: " +
          ", ".join(f"{k} {sum(1 for s in scenes if (('pan' in s) and k == 'pan') or (k == 'focal' and s['center_x'] != 0.5 and 'pan' not in s) or (k == 'zoom' and s['center_x'] == 0.5 and 'pan' not in s))}"
                    for k in ("zoom", "focal", "pan")))


if __name__ == "__main__":
    main()
