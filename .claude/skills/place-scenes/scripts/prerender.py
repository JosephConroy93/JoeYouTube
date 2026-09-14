#!/usr/bin/env python
"""prerender.py -- every visual for build_timeline.py, at exact frame counts.

Usage:
    prerender.py <series>/<slug> --staging <dir> --fps N
                 [--width 1920 --height 1080] [--font C:/Windows/Fonts/Inkfree.ttf]
                 [--overlay-pos <scene_id>=x,y ...] [--jobs 8] [--only id,id]

Reads   claude/scene-timing.md             frame plan (same rule as build_timeline.py)
        voiceovers/normalized/<segment>.wav copied to <staging>/voiceovers/
        scene-generation/<scene_id>.jpg    stills, cropped to 16:9, never downscaled
        claude/hook-plan.md                shot -> scene_id; hook/shot-NN.mp4 replaces that still
        claude/scene-prompts/*.md          `overlay: "<word>"` in a row's notes -> drawn on the carrier
        claude/script.md                   `## Level N. <Rank>.` headings -> level cards
Writes  <staging>/scenes/<scene_id>.mp4    one clip per timing row, exactly its planned frames
        <staging>/cards/<scene_id>.mp4     2 s black level card for each chapter's first scene

Hook clips are scaled to the timeline size, trimmed to the scene's frames or held on
their last frame. Overlay words sit centred unless --overlay-pos gives top-left fractions.
Every output is frame-counted with ffprobe -count_frames; any mismatch exits non-zero.
"""
import argparse
import concurrent.futures as cf
import glob
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_timeline import audio_duration, frames, read_timing, resolve_project  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:6])}...: {r.stderr.strip()[-400:]}")
    return r.stdout


def count_frames(path):
    out = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
               "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path])
    return int(out.strip())


def image_size(path):
    w, h = run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", path]).strip().split(",")
    return int(w), int(h)


def esc_path(p):
    """A path inside an ffmpeg filter argument: forward slashes, escaped drive colon."""
    return p.replace("\\", "/").replace(":", "\\:")


def plan(project, staging, fps):
    rows = read_timing(project)
    stems = []
    for r in rows:
        if r["segment"] not in stems:
            stems.append(r["segment"])
    os.makedirs(os.path.join(staging, "voiceovers"), exist_ok=True)
    offset, off = 0.0, {}
    for stem in stems:
        src = os.path.join(project, "voiceovers", "normalized", stem + ".wav")
        if not os.path.isfile(src):
            sys.exit(f"ABORT: missing {src}")
        dst = os.path.join(staging, "voiceovers", stem + ".wav")
        if not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(src):
            shutil.copy2(src, dst)
        off[stem] = offset
        offset += audio_duration(dst)
    total = frames(offset, fps)
    for r in rows:
        r["start_frame"] = frames(off[r["segment"]] + r["start"], fps)
    for a, b in zip(rows, rows[1:]):
        a["frames"] = b["start_frame"] - a["start_frame"]
    rows[-1]["frames"] = total - rows[-1]["start_frame"]
    bad = [r["scene_id"] for r in rows if r["frames"] <= 0]
    if bad:
        sys.exit(f"ABORT: non-positive frame count for {bad}")
    return rows


def hook_map(project):
    path = os.path.join(project, "claude", "hook-plan.md")
    if not os.path.isfile(path):
        return {}
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*`?(\d{3}_[A-Za-z0-9-]+)`?\s*\|", line)
        if m:
            clip = os.path.join(project, "hook", f"shot-{int(m.group(1)):02d}.mp4")
            if not os.path.isfile(clip):
                sys.exit(f"ABORT: hook-plan names {clip}, not on disk")
            out[m.group(2)] = clip
    return out


def overlays(project):
    out = {}
    for path in glob.glob(os.path.join(project, "claude", "scene-prompts", "*.md")):
        for line in open(path, encoding="utf-8"):
            m = re.match(r"\|\s*`?(\d{3}_[A-Za-z0-9-]+)`?\s*\|", line)
            w = re.search(r'overlay:\s*"([^"]+)"', line)
            if m and w:
                out[m.group(1)] = w.group(1)
    return out


def level_cards(project, rows):
    heads = [m.group(1) for m in re.finditer(r"^##\s+(Level\s+\d+\..*?)\s*$",
                                             open(os.path.join(project, "claude", "script.md"),
                                                  encoding="utf-8").read(), re.M)]
    firsts, seen = [], set()
    for r in rows:
        ch = r.get("chapter")
        if ch not in seen:
            seen.add(ch)
            firsts.append(r)
    if len(heads) != len(firsts):
        sys.exit(f"ABORT: {len(heads)} level headings in script.md, {len(firsts)} chapters in scene-timing.md")
    return list(zip(firsts, heads))


def still_job(r, jpg, out, fps, W, H, word, pos, font):
    iw, ih = image_size(jpg)
    if iw * 9 > ih * 16:
        cw, ch = (ih * 16 // 9) // 2 * 2, ih // 2 * 2
    else:
        cw, ch = iw // 2 * 2, (iw * 9 // 16) // 2 * 2
    vf = [f"crop={cw}:{ch}"]
    if cw < W:
        vf.append(f"scale={W}:{H}:flags=lanczos")
        cw, ch = W, H
    if word:
        x, y = pos or (0.5, 0.5)
        txt = out + ".txt"
        open(txt, "w", encoding="utf-8").write(word)
        vf.append(f"drawtext=fontfile='{esc_path(font)}':textfile='{esc_path(txt)}':fontcolor=0x2a1d14:"
                  f"fontsize={int(ch * 0.11)}:x={x}*w-text_w/2:y={y}*h-text_h/2")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(fps), "-i", jpg,
         "-vf", ",".join(vf), "-frames:v", str(r["frames"]), "-r", str(fps),
         "-c:v", "libx264", "-crf", "18", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-an", out])


def hook_job(r, clip, out, fps, W, H):
    have = count_frames(clip)
    hold = max(0, r["frames"] - have) / fps + 0.5
    run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-vf",
         f"scale={W}:{H}:flags=lanczos,fps={fps},tpad=stop_mode=clone:stop_duration={hold:.3f}",
         "-frames:v", str(r["frames"]), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-an", out])
    return have


def card_job(text, out, fps, W, H, font):
    txt = out + ".txt"
    open(txt, "w", encoding="utf-8").write(text.upper())
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}",
         "-vf", f"drawtext=fontfile='{esc_path(font)}':textfile='{esc_path(txt)}':fontcolor=white:"
                f"fontsize={int(H * 0.06)}:x=(w-text_w)/2:y=(h-text_h)/2",
         "-frames:v", str(2 * fps), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--staging", required=True)
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--font", default="C:/Windows/Fonts/Inkfree.ttf")
    ap.add_argument("--overlay-pos", action="append", default=[], help="scene_id=x,y (top-left fractions)")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--only", help="comma-separated scene ids (cards for them too)")
    a = ap.parse_args()

    project = resolve_project(a.project)
    staging = os.path.abspath(a.staging)
    if "onedrive" in staging.lower():
        sys.exit("ABORT: staging must sit outside OneDrive")
    for d in ("scenes", "cards"):
        os.makedirs(os.path.join(staging, d), exist_ok=True)
    rows = plan(project, staging, a.fps)
    hooks, words = hook_map(project), overlays(project)
    pos = {}
    for p in a.overlay_pos:
        sid, xy = p.split("=")
        pos[sid] = tuple(float(v) for v in xy.split(","))
    only = set(a.only.split(",")) if a.only else None
    W, H, fps = a.width, a.height, a.fps

    jobs = {}
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for r in rows:
            sid = r["scene_id"]
            if only and sid not in only:
                continue
            out = os.path.join(staging, "scenes", sid + ".mp4")
            if sid in hooks:
                jobs[ex.submit(hook_job, r, hooks[sid], out, fps, W, H)] = (sid, out, r["frames"], "hook")
            else:
                jpg = os.path.join(project, "scene-generation", sid + ".jpg")
                if not os.path.isfile(jpg):
                    sys.exit(f"ABORT: missing {jpg}")
                jobs[ex.submit(still_job, r, jpg, out, fps, W, H, words.get(sid), pos.get(sid), a.font)] = \
                    (sid, out, r["frames"], "overlay" if sid in words else "still")
        for r, head in level_cards(project, rows):
            if only and r["scene_id"] not in only:
                continue
            if r["frames"] < 2 * fps:
                sys.exit(f"ABORT: {r['scene_id']} is shorter than its 2 s level card")
            out = os.path.join(staging, "cards", r["scene_id"] + ".mp4")
            jobs[ex.submit(card_job, head, out, fps, W, H, a.font)] = (r["scene_id"], out, 2 * fps, "card")

        problems, n = [], {"hook": 0, "still": 0, "overlay": 0, "card": 0}
        for f in cf.as_completed(jobs):
            sid, out, want, kind = jobs[f]
            try:
                res = f.result()
                got = count_frames(out)
            except Exception as e:  # noqa: BLE001
                problems.append(f"{kind} {sid}: {e}")
                continue
            if got != want:
                problems.append(f"{kind} {sid}: {got} frames, plan needs {want}")
            n[kind] += 1
            if kind == "hook" and res < want:
                print(f"hook {sid}: source {res} frames, last frame held {want - res}")
    for t in glob.glob(os.path.join(staging, "*", "*.txt")):
        os.remove(t)
    print(f"rendered {n} into {staging}")
    if words:
        print("overlays: " + ", ".join(f"{k}={v!r}" for k, v in sorted(words.items())))
    if problems:
        sys.exit("ABORT:\n  " + "\n  ".join(sorted(problems)))
    print("all clips frame-exact")


if __name__ == "__main__":
    main()
