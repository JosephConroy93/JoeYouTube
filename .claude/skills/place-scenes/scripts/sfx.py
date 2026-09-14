#!/usr/bin/env python
"""sfx.py -- bake a video's spot SFX to level-set clips for build_timeline.py --sfx.

Usage:
    sfx.py <series>/<slug> --staging <dir> --fps N [--library <dir>]

Reads   claude/sfx-plan.md   | scene_id | source | in_s | dur_s | offset_s | lufs | note |
                             source is relative to the library root; dur_s blank = to the end
        content/sfx/sfx-index.md  library root (first backticked path after "Library location")
        claude/scene-timing.md    scene spans (the sound must end inside its scene)
Writes  <staging>/sfx/<scene_id>.wav   48 kHz 16-bit dual-mono, faded, gain set to the row's
                                       integrated LUFS (the API cannot set clip volume; the
                                       timeline's audio tracks are mono, so both channels
                                       are folded into each)

Every output is measured: integrated LUFS within 1 LU of the target, and per-channel RMS
with no silent channel (a mono file on a stereo track plays left-only).
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from prerender import plan, resolve_project  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def read_plan(project):
    path = os.path.join(project, "claude", "sfx-plan.md")
    if not os.path.isfile(path):
        sys.exit(f"ABORT: missing {path}")
    rows = []
    for line in open(path, encoding="utf-8"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        sid = c[0].strip("`") if c else ""
        if len(c) < 6 or not re.fullmatch(r"\d{3}_[A-Za-z0-9-]+", sid):
            continue
        rows.append({"scene_id": sid, "source": c[1].strip("`"), "in": float(c[2] or 0),
                     "dur": float(c[3]) if c[3] else None, "offset": float(c[4] or 0), "lufs": float(c[5])})
    return rows


def library_root(root_dir):
    idx = os.path.join(root_dir, "content", "sfx", "sfx-index.md")
    m = re.search(r"Library location.*?`([^`]+)`", open(idx, encoding="utf-8").read(), re.S)
    if not m:
        sys.exit(f"ABORT: no library location in {idx}")
    return m.group(1)


def measure(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af",
                        "ebur128,astats=measure_perchannel=RMS_level:measure_overall=none",
                        "-f", "null", "-"], capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", r.stderr)
    rms = [float(x) if x != "-inf" else float("-inf") for x in re.findall(r"RMS level dB:\s*(-?[\d.]+|-inf)", r.stderr)]
    return (float(i[-1]) if i and i[-1] != "-inf" else float("-inf")), rms


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                                          "stream=duration", "-of", "csv=p=0", path]).decode().strip())


def bake(src, out, t_in, dur, gain_db):
    fade_out = min(0.4, dur / 3)
    af = (f"aresample=48000,pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,afade=t=in:d={min(0.05, dur / 10):.3f},"
          f"afade=t=out:st={dur - fade_out:.3f}:d={fade_out:.3f},volume={gain_db:.2f}dB")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t_in:.3f}", "-t", f"{dur:.3f}", "-i", src,
                    "-af", af, "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", out], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--staging", required=True)
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--library")
    a = ap.parse_args()

    project = resolve_project(a.project)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    lib = a.library or library_root(root_dir)
    staging = os.path.abspath(a.staging)
    os.makedirs(os.path.join(staging, "sfx"), exist_ok=True)
    spans = {r["scene_id"]: r["frames"] / a.fps for r in plan(project, staging, a.fps)}

    problems = []
    for r in read_plan(project):
        sid = r["scene_id"]
        src = os.path.join(lib, *r["source"].split("/"))
        if sid not in spans:
            problems.append(f"{sid}: not in scene-timing.md")
            continue
        if not os.path.isfile(src):
            problems.append(f"{sid}: source not found: {src}")
            continue
        dur = r["dur"] if r["dur"] else duration(src) - r["in"]
        if r["offset"] + dur > spans[sid] + 1e-6:
            problems.append(f"{sid}: offset {r['offset']} + {dur:.2f} s runs past the scene's {spans[sid]:.2f} s")
            continue
        out = os.path.join(staging, "sfx", sid + ".wav")
        bake(src, out, r["in"], dur, 0.0)
        i0, _ = measure(out)
        bake(src, out, r["in"], dur, r["lufs"] - i0)
        i1, rms = measure(out)
        ok = abs(i1 - r["lufs"]) <= 1.0 and len(rms) == 2 and all(x > -60 for x in rms)
        print(f"{'ok ' if ok else 'BAD'} {sid}: {dur:.2f} s at +{r['offset']:.2f} s, "
              f"I {i1:.1f} LUFS (target {r['lufs']}), RMS L {rms[0] if rms else '?':.1f} / "
              f"R {rms[1] if len(rms) > 1 else float('nan'):.1f} dB")
        if not ok:
            problems.append(f"{sid}: measured I {i1:.1f}, RMS {rms}")
    if problems:
        sys.exit("ABORT:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    main()
