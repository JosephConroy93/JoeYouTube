#!/usr/bin/env python
"""check_kb.py -- compare report_kb.lua's readback with the Ken Burns spec.

Usage:
    check_kb.py --spec <ken-burns-spec.json> --report <kb-report.tsv>

Every spec record must have a KB tool on its item with Size at frame 0 and the last frame
within 0.005 of the spec, Size mid-scene between the two ends (no overshoot), the Pivot on
the (Y-flipped) target, and for a pan Center at both ends on the flipped start and end.
Items not in the spec must carry no KB tool. Exits non-zero naming every mismatch.
"""
import argparse
import csv
import json
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()

    spec = {r["scene_id"]: r for r in json.load(open(a.spec, encoding="utf-8"))["scenes"]}
    rows = list(csv.DictReader(open(a.report, encoding="utf-8"), delimiter="\t"))
    tol = 0.005
    bad, seen = [], set()

    def close(x, y):
        return x != "" and abs(float(x) - y) <= tol

    for r in rows:
        sid = r["name"].rsplit(".", 1)[0]
        s = spec.get(sid)
        if not s:
            if r["kb"] == "1":
                bad.append(f"{sid}: KB tool present but not in the spec")
            continue
        seen.add(sid)
        if r["kb"] != "1":
            bad.append(f"{sid}: no KB tool")
            continue
        if int(r["frames"]) != s["frames"]:
            bad.append(f"{sid}: item {r['frames']} frames, spec {s['frames']}")
        if not (close(r["size0"], s["size_start"]) and close(r["size_last"], s["size_end"])):
            bad.append(f"{sid}: Size {r['size0']} -> {r['size_last']}, spec {s['size_start']} -> {s['size_end']}")
        lo, hi = sorted((s["size_start"], s["size_end"]))
        if r["size_mid"] == "" or not (lo - tol <= float(r["size_mid"]) <= hi + tol):
            bad.append(f"{sid}: Size mid-scene {r['size_mid']} outside {lo}..{hi}")
        if not (close(r["pivot_x"], s["center_x"]) and close(r["pivot_y"], 1 - s["center_y"])):
            bad.append(f"{sid}: Pivot ({r['pivot_x']},{r['pivot_y']}), spec ({s['center_x']},{1 - s['center_y']})")
        if s.get("pan"):
            ok = (close(r["center0_x"], s["cx0"]) and close(r["center0_y"], 1 - s["cy0"]) and
                  close(r["center_last_x"], s["cx1"]) and close(r["center_last_y"], 1 - s["cy1"]))
            if not ok:
                bad.append(f"{sid}: Center ({r['center0_x']},{r['center0_y']}) -> ({r['center_last_x']},{r['center_last_y']}), "
                           f"spec ({s['cx0']},{1 - s['cy0']}) -> ({s['cx1']},{1 - s['cy1']})")
    missing = sorted(set(spec) - seen)
    if missing:
        bad.append(f"spec scenes with no timeline item: {missing}")
    kb = sum(1 for r in rows if r["kb"] == "1")
    print(f"{len(rows)} items, {kb} with KB, {len(spec)} in spec, {len(bad)} mismatches")
    if bad:
        sys.exit("\n".join(bad))


if __name__ == "__main__":
    main()
