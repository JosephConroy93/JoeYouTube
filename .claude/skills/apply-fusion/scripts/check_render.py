#!/usr/bin/env python
"""check_render.py -- measure a rendered range of a video's edit against its plans.

Usage:
    check_render.py <series>/<slug> --staging <dir> --fps N --render <file.mp4> --mark-in F [--mark-out F]

The render must start at timeline frame --mark-in. Checks, each printed with its numbers:
  frames   video frame count equals mark-out - mark-in + 1 (when --mark-out is given)
  audio    integrated LUFS within 1.5 LU of --lufs (when given), and per-channel RMS: no
           silent channel, L and R within 1 dB
  motion   every scene wholly in range: SSIM between an early and a late frame. A moving row
           (In/Out/Focal/Pan) must change (SSIM < 0.97); a Static still must not (> 0.99);
           hook clips are reported only. Level-card scenes are sampled after the card.
  cards    every level card in range: mean luma of its middle frame < 0.15
  sfx      every sfx-plan row in range: the render minus the voiceover, lag and gain fitted on
           the neighbouring second (before or after) that carries more voice, is louder inside
           the sound's window than in that second by 6 dB+
Exits non-zero naming every failed check. A metric proves change, not the right change:
still look at the frames.
"""
import argparse
import glob
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "place-scenes", "scripts"))
from prerender import hook_map, plan, resolve_project  # noqa: E402
from sfx import read_plan  # noqa: E402

SR = 48000


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def frame_png(render, n, out, fps):
    """Frame n by input seek (a select filter decodes from the start: minutes per frame on a full render)."""
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, (n - 0.25) / fps):.4f}", "-i", render, "-frames:v", "1", out])
    return out


def ssim(a, b):
    m = re.search(r"All:([\d.]+)", run(["ffmpeg", "-nostats", "-i", a, "-i", b, "-lavfi", "ssim", "-f", "null", "-"]).stderr)
    return float(m.group(1)) if m else float("nan")


def luma(png):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-vf", "scale=1:1:flags=area,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return raw[0] / 255 if raw else float("nan")


def pcm(path, start=None, dur=None, mono=True):
    args = ["ffmpeg", "-v", "error"]
    if start is not None:
        args += ["-ss", f"{start:.4f}"]
    if dur is not None:
        args += ["-t", f"{dur:.4f}"]
    args += ["-i", path, "-f", "f32le", "-ac", "1" if mono else "2", "-ar", str(SR), "-"]
    data = np.frombuffer(subprocess.run(args, capture_output=True).stdout, dtype=np.float32)
    return data if mono else data.reshape(-1, 2)


def db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)


def plan_rows(project):
    rows = {}
    for line in open(os.path.join(project, "claude", "ken-burns-plan.md"), encoding="utf-8"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 7 and re.fullmatch(r"`?\d{3}_[A-Za-z0-9-]+`?", c[1]):
            rows[c[1].strip("`")] = c[3].split()[0]
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--staging", required=True)
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--render", required=True)
    ap.add_argument("--mark-in", type=int, required=True)
    ap.add_argument("--mark-out", type=int)
    ap.add_argument("--lufs", type=float, help="expected integrated LUFS of the range (the voice file's, same span)")
    ap.add_argument("--skip-motion", action="store_true", help="skip the per-scene motion and card checks")
    a = ap.parse_args()

    project = resolve_project(a.project)
    staging, fps, m_in = os.path.abspath(a.staging), a.fps, a.mark_in
    tmp = os.path.join(staging, "checks", "_frames")
    os.makedirs(tmp, exist_ok=True)
    scenes = plan(project, staging, fps)
    zoom = plan_rows(project)
    hooks = set(hook_map(project))
    fails = []

    counted = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                   "stream=nb_read_frames", "-of", "csv=p=0", a.render]).stdout.split()
    if not counted:
        sys.exit("FAILED: the render has no video stream (render settings exported audio only; "
                 "verify_output still reports verified)")
    n = int(counted[0])
    m_out = m_in + n - 1
    if a.mark_out is not None:
        ok = n == a.mark_out - m_in + 1
        print(f"frames  {'ok ' if ok else 'BAD'} {n} (expected {a.mark_out - m_in + 1})")
        if not ok:
            fails.append("frame count")
        m_out = a.mark_out

    err = run(["ffmpeg", "-nostats", "-i", a.render, "-af", "ebur128,astats=measure_perchannel=RMS_level:measure_overall=none",
               "-f", "null", "-"]).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    rms = [float(x) for x in re.findall(r"RMS level dB:\s*(-?[\d.]+)", err)]
    ok = len(rms) == 2 and min(rms) > -60 and abs(rms[0] - rms[1]) <= 1.0
    if a.lufs is not None:
        ok = ok and bool(lufs) and abs(float(lufs[-1]) - a.lufs) <= 1.5
    print(f"audio   {'ok ' if ok else 'BAD'} I {lufs[-1] if lufs else '?'} LUFS, RMS L {rms[0] if rms else '?'} / R {rms[1] if len(rms) > 1 else '?'} dB")
    if not ok:
        fails.append("audio level or channels")

    cards = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(staging, "cards", "*.mp4"))}
    for s in ([] if a.skip_motion else scenes):
        sid, s0, nf = s["scene_id"], s["start_frame"], s["frames"]
        if s0 < m_in or s0 + nf - 1 > m_out:
            continue
        kind = zoom.get(sid, "?")
        first = s0 - m_in + (2 * fps + 2 if sid in cards else 1)
        last = s0 - m_in + nf - 2
        if last - first < fps:
            continue
        v = ssim(frame_png(a.render, first, os.path.join(tmp, "a.png"), fps), frame_png(a.render, last, os.path.join(tmp, "b.png"), fps))
        if sid in hooks:
            print(f"motion  --  {sid[:3]} hook clip SSIM {v:.3f}")
            continue
        moving = kind in ("In", "Out", "Focal", "Pan")
        ok = v < 0.97 if moving else v > 0.99
        print(f"motion  {'ok ' if ok else 'BAD'} {sid[:3]} {kind:6s} SSIM {v:.3f}")
        if not ok:
            fails.append(f"motion {sid[:3]}")
        if sid in cards:
            y = luma(frame_png(a.render, s0 - m_in + fps, os.path.join(tmp, "c.png"), fps))
            ok = y < 0.15
            print(f"card    {'ok ' if ok else 'BAD'} {sid[:3]} mean luma {y:.3f}")
            if not ok:
                fails.append(f"card {sid[:3]}")

    by_id = {s["scene_id"]: s for s in scenes}
    vo = sorted(glob.glob(os.path.join(staging, "voiceovers", "*.wav")))
    vo_all = np.concatenate([pcm(p) for p in vo])
    for r in read_plan(project):
        s = by_id[r["scene_id"]]
        t0 = s["start_frame"] / fps + r["offset"]
        dur = min(r["dur"] or 2.0, s["frames"] / fps - r["offset"])
        if t0 - 1.0 < m_in / fps or t0 + dur > (m_out + 1) / fps:
            continue
        span0, span1 = t0 - 1.0, min(t0 + dur + 1.0, (m_out + 1) / fps)
        rend = pcm(a.render, span0 - m_in / fps, span1 - span0)
        ref_full = vo_all[int((span0 - 0.1) * SR): int((span1 + 0.1) * SR)]
        # calibrate lag and gain on whichever neighbouring second carries more voice:
        # a near-silent second cancels to nothing and proves little
        win0, win1 = SR, int((t0 + dur - span0) * SR)
        before_e = db(vo_all[int(span0 * SR): int(span0 * SR) + SR])
        after_e = db(vo_all[int((t0 + dur) * SR): int((t0 + dur) * SR) + SR]) if len(rend) - win1 >= SR else -120.0
        c0 = 0 if before_e >= after_e else win1
        cal = rend[c0: c0 + SR]
        L = SR + int(0.2 * SR)
        seg = ref_full[c0: c0 + L]
        corr = np.fft.irfft(np.fft.rfft(seg, n=L) * np.conj(np.fft.rfft(cal, n=L)), n=L)
        k = int(np.argmax(corr[: int(0.2 * SR)]))
        ref = ref_full[k: k + len(rend)]
        n_ok = min(len(rend), len(ref))
        g = float(np.dot(cal, ref[c0: c0 + SR]) / (np.dot(ref[c0: c0 + SR], ref[c0: c0 + SR]) + 1e-12))
        res = rend[:n_ok] - g * ref[:n_ok]
        side, inside = db(res[c0: c0 + SR]), db(res[win0: min(win1, n_ok)])
        ok = inside - side >= 6
        print(f"sfx     {'ok ' if ok else 'BAD'} {r['scene_id'][:3]} residual {inside:.1f} dB in window vs {side:.1f} dB "
              f"{'before' if c0 == 0 else 'after'} (voice there {max(before_e, after_e):.1f} dB)")
        if not ok:
            fails.append(f"sfx {r['scene_id'][:3]}")

    if fails:
        sys.exit("FAILED: " + ", ".join(fails))
    print("all checks passed")


if __name__ == "__main__":
    main()
