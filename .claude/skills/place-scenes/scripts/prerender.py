#!/usr/bin/env python
"""prerender.py -- every visual for build_timeline.py, at exact frame counts.

Usage:
    prerender.py <series>/<slug> --staging <dir> --fps N
                 [--width 1920 --height 1080] [--font C:/Windows/Fonts/Inkfree.ttf]
                 [--overlay-pos <scene_id>=x,y ...] [--jobs 8] [--only id,id]
                 [--grade <lut.cube> --grade-mix 0.5] [--film-until <scene_id>]

Reads   claude/scene-timing.md             frame plan (same rule as build_timeline.py)
        voiceovers/normalized/<segment>.wav copied to <staging>/voiceovers/
        scene-generation/<scene_id>.jpg    stills, cropped to 16:9, never downscaled
        claude/hook-plan.md                shot -> scene_id; hook/shot-NN.mp4 replaces that still
        claude/scene-prompts/*.md          `overlay: "<word>"` in a row's notes -> drawn on the carrier
        claude/script.md                   `## ` chapter headings (before Handoff notes) -> chapter cards
        ../series.md                       `thumbnail.*` colours and font for the cards
Writes  <staging>/scenes/<scene_id>.mp4    one clip per timing row, exactly its planned frames
        <staging>/cards/<scene_id>.mp4     2.2 s chapter card landing on that scene

A chapter card is the thumbnail layout: cream ground, `CHAPTER N` and the chapter name on
the left, the scene it lands on as a tilted outlined card on the right. The card grows,
straightens and fills the frame, its last frame identical to the scene's frame under it.
It lands on the chapter's first scene (or the first scene after --film-until when the
chapter opens inside the film); an all-hook chapter (the cold open) gets none. The landing
scene holds still under the card, then pushes in (text-card rows stay still).

--grade mixes a 3D LUT over every hook clip and still (never card grounds) at --grade-mix.
--film-until gives every visual up to and including that scene the film look (gate weave,
flicker, vignette, grain, grey edge falloff, 2.39:1 letterbox); the next scene opens its
bars over 0.6 s once its card has landed.

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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


BAR_OPEN_S = 0.6
CARD_S, PUSH = 2.2, 0.08


def letterbox_bar(W, H):
    return (H - round(W / 2.39 / 2) * 2) // 2


def grade_chain(cube, mix):
    return (f"format=gbrp,split[ga][gb];[gb]lut3d=file='{esc_path(cube)}'[gl];"
            f"[ga][gl]blend=all_mode=normal:all_opacity={mix}")


def falloff_png(staging, W, H):
    ph = H - 2 * letterbox_bar(W, H)
    path = os.path.join(staging, "film", f"falloff-{W}x{ph}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fall = Image.radial_gradient("L").resize((W, ph)).point(lambda v: int(max(0, v - 90) * 0.75))
    grey = Image.new("RGBA", (W, ph), (70, 72, 70, 0))
    grey.putalpha(fall)
    grey.save(path)
    return path


def film_chain(W, H, falloff):
    bar = letterbox_bar(W, H)
    return (f"scale={W + 40}:{H + 22},crop={W}:{H}:x='20+2.2*sin(n*0.9)+1.3*sin(n*2.3)':"
            "y='11+1.6*sin(n*1.3)+1.1*sin(n*3.1)',"
            "eq=brightness='0.012*sin(t*21)+0.007*sin(t*47)':eval=frame,vignette=PI/4.2,"
            f"noise=alls=34:allf=t,gblur=sigma=0.9,crop={W}:{H - 2 * bar}[fb];"
            f"movie='{esc_path(falloff)}',format=rgba[fg];[fb][fg]overlay=format=auto,pad={W}:{H}:0:{bar}")


def bars_open_chain(fps, W, H, delay=0.0):
    bar = letterbox_bar(W, H)
    e = f"(1-pow(1-clip((t-{delay:.3f})/{BAR_OPEN_S},0,1),3))"
    return (f"null[ob];color=black:s={W}x{bar}:r={fps}[ot];color=black:s={W}x{bar}:r={fps}[ou];"
            f"[ob][ot]overlay=y='-{bar}*{e}':shortest=1[oc];[oc][ou]overlay=y='{H - bar}+{bar}*{e}':shortest=1")


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
    text = open(os.path.join(project, "claude", "script.md"), encoding="utf-8").read()
    text = re.split(r"^##\s+Handoff notes", text, flags=re.M)[0]
    heads = [m.group(1) for m in re.finditer(r"^##\s+(.+?)\s*$", text, re.M)]
    firsts, seen = [], set()
    for r in rows:
        ch = re.sub(r"(\d+)[a-z]\.md$", r"\1.md", r.get("chapter") or "")
        if ch not in seen:
            seen.add(ch)
            firsts.append(r)
    if len(heads) != len(firsts):
        sys.exit(f"ABORT: {len(heads)} chapter headings in script.md, {len(firsts)} chapters in scene-timing.md")
    return list(zip(firsts, heads))


def card_targets(project, rows, hooks, film_until=None):
    """[(landing row, heading)]: one card per chapter, none for an all-hook chapter."""
    ids = [r["scene_id"] for r in rows]
    film_end = ids.index(film_until) if film_until else -1
    chap = {r["scene_id"]: re.sub(r"(\d+)[a-z]\.md$", r"\1.md", r.get("chapter") or "") for r in rows}
    out = []
    for r, head in level_cards(project, rows):
        if all(s in hooks for s, c in chap.items() if c == chap[r["scene_id"]]):
            continue
        out.append((rows[max(ids.index(r["scene_id"]), film_end + 1)], head))
    return out


def series_look(project):
    keys = {}
    for line in open(os.path.join(os.path.dirname(project), "series.md"), encoding="utf-8"):
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            code = re.search(r"`([^`]+)`", m.group(2))
            keys[m.group(1)] = code.group(1) if code else m.group(2)
    need = ["thumbnail.background", "thumbnail.ink", "thumbnail.accent", "thumbnail.font"]
    if any(k not in keys for k in need):
        sys.exit(f"ABORT: series.md needs {', '.join(need)} for the chapter cards")
    rgb = lambda v: tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))  # noqa: E731
    return rgb(keys[need[0]]), rgb(keys[need[1]]), rgb(keys[need[2]]), keys[need[3]]


def card_text(W, H, head, look):
    bg, ink, accent, font = look
    k = W / 1920
    m = re.match(r"^(\w+\s+\d+)\.\s*(.+?)\.?$", head)
    label, name = (m.group(1).upper(), m.group(2).upper()) if m else ("", head.rstrip(".").upper())
    layer = Image.new("RGBA", (W, H), bg + (0,))
    d = ImageDraw.Draw(layer)
    x, width, lead = round(90 * k), round(760 * k), round(14 * k)
    small = ImageFont.truetype(font, round(58 * k))
    size = round(170 * k)
    while True:
        f = ImageFont.truetype(font, size)
        lines, cur = [], ""
        for w in name.split():
            t = (cur + " " + w).strip()
            if cur and d.textbbox((0, 0), t, font=f)[2] > width:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        if max(d.textbbox((0, 0), ln, font=f)[2] for ln in lines) <= width and len(lines) <= 3:
            break
        size -= 4
    boxes = [d.textbbox((0, 0), ln, font=f) for ln in lines]
    gap = round(30 * k) if label else 0
    lh = d.textbbox((0, 0), label, font=small)[3] if label else 0
    y = (H - (lh + gap + sum(b[3] - b[1] for b in boxes) + lead * (len(lines) - 1))) / 2
    if label:
        sb = d.textbbox((0, 0), label, font=small)
        d.text((x - sb[0], y - sb[1]), label, font=small, fill=accent)
        y += lh + gap
    for ln, b in zip(lines, boxes):
        d.text((x - b[0], y - b[1]), ln, font=f, fill=ink)
        y += b[3] - b[1] + lead
    return layer


def card_frame(still, text, p, look):
    bg, ink = look[0], look[1]
    W, H = still.size
    k = W / 1920
    ar = 1.23 + (W / H - 1.23) * p
    pw = round(880 * k + (W - 880 * k) * p)
    ph = round(pw / ar) if p < 1 else H
    cw = min(W, round(H * ar))
    x0 = (W - cw) // 2
    pic = still.crop((x0, 0, x0 + cw, H)).resize((pw, ph), Image.LANCZOS)
    if p >= 1:
        return pic
    b = round(14 * k * (1 - p))
    card = Image.new("RGBA", (pw + 2 * b, ph + 2 * b), ink + (255,))
    card.paste(pic, (b, b))
    card = card.rotate(-3 * (1 - p), resample=Image.BICUBIC, expand=True)
    cx = 1370 * k + (W / 2 - 1370 * k) * p
    pos = (round(cx - card.width / 2), round(H / 2 - card.height / 2))
    canvas = Image.new("RGB", (W, H), bg)
    shade = round(90 * (1 - p))
    if shade:
        s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s.paste((0, 0, 0, shade), (pos[0] + round(18 * k), pos[1] + round(24 * k)), card.split()[3])
        s = s.filter(ImageFilter.GaussianBlur(20 * k))
        canvas.paste(s, (0, 0), s)
    fade = min(1.0, max(0.0, 1 - (p - 0.2) / 0.3))
    if fade:
        t = text.copy()
        t.putalpha(t.split()[3].point(lambda v: int(v * fade)))
        canvas.paste(t, (round(-160 * k * (1 - fade)), 0), t)
    canvas.paste(card, pos, card)
    return canvas


def card_job(head, scene_clip, land, out, fps, W, H, look):
    pic = out + ".land.png"
    run(["ffmpeg", "-v", "error", "-y", "-i", scene_clip, "-vf", f"select='eq(n,{land})',scale={W}:{H}:flags=lanczos",
         "-frames:v", "1", pic])
    still = Image.open(pic).convert("RGB")
    still.load()
    os.remove(pic)
    text = card_text(W, H, head, look)
    n = round(CARD_S * fps)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                             "-an", out], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for i in range(n):
        u = i / (n - 1)
        s = u * u * (3 - 2 * u)
        proc.stdin.write(card_frame(still, text, s ** 3, look).tobytes())
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait():
        raise RuntimeError(f"card encode: {err[-400:]}")


def push_job(r, jpg, out, fps, cw, ch, hold, look, crop):
    """Held still for `hold` frames, then an eased push-in about the centre, drawn with subpixel
    precision (ffmpeg's per-frame scale and zoompan both step visibly on a slow zoom)."""
    im = Image.open(jpg).convert("RGB")
    (iw, ih), (kw, kh) = im.size, crop
    im = im.crop(((iw - kw) // 2, (ih - kh) // 2, (iw - kw) // 2 + kw, (ih - kh) // 2 + kh))
    if im.size != (cw, ch):
        im = im.resize((cw, ch), Image.LANCZOS)
    args = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{cw}x{ch}", "-r", str(fps),
            "-i", "-"]
    if look:
        args += ["-filter_complex", ",".join(look)]
    proc = subprocess.Popen(args + ["-frames:v", str(r["frames"]), "-c:v", "libx264", "-crf", "18", "-pix_fmt",
                                    "yuv420p", "-an", out], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    held = im.tobytes()
    span = r["frames"] - 1 - hold
    for i in range(r["frames"]):
        if i <= hold:
            proc.stdin.write(held)
            continue
        z = 1 + PUSH * ((i - hold) / span) ** 2
        a = 1 / z
        proc.stdin.write(im.transform((cw, ch), Image.AFFINE, (a, 0, cw / 2 * (1 - a), 0, a, ch / 2 * (1 - a)),
                                      resample=Image.BICUBIC).tobytes())
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait():
        raise RuntimeError(f"push encode {r['scene_id']}: {err[-400:]}")


def still_job(r, jpg, out, fps, W, H, word, pos, font, look, hold=0):
    iw, ih = image_size(jpg)
    if iw * 9 > ih * 16:
        cw, ch = (ih * 16 // 9) // 2 * 2, ih // 2 * 2
    else:
        cw, ch = iw // 2 * 2, (iw * 9 // 16) // 2 * 2
    vf = [f"crop={cw}:{ch}"]
    crop = (cw, ch)
    if cw < W:
        vf.append(f"scale={W}:{H}:flags=lanczos")
        cw, ch = W, H
    look = [x(cw, ch) if callable(x) else x for x in look]
    if hold and not word and r["frames"] > hold + 1:
        return push_job(r, jpg, out, fps, cw, ch, hold, look, crop)
    if word:
        x, y = pos or (0.5, 0.5)
        txt = out + ".txt"
        open(txt, "w", encoding="utf-8").write(word)
        vf.append(f"drawtext=fontfile='{esc_path(font)}':textfile='{esc_path(txt)}':fontcolor=0x2a1d14:"
                  f"fontsize={int(ch * 0.11)}:x={x}*w-text_w/2:y={y}*h-text_h/2")
    tune = [] if look else ["-tune", "stillimage"]
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(fps), "-i", jpg,
         "-filter_complex", ",".join(vf + look), "-frames:v", str(r["frames"]), "-r", str(fps),
         "-c:v", "libx264", "-crf", "18", *tune, "-pix_fmt", "yuv420p", "-an", out])


def hook_job(r, clip, out, fps, W, H, look):
    look = [x(W, H) if callable(x) else x for x in look]
    have = count_frames(clip)
    hold = max(0, r["frames"] - have) / fps + 0.5
    run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-filter_complex",
         ",".join([f"scale={W}:{H}:flags=lanczos,fps={fps},tpad=stop_mode=clone:stop_duration={hold:.3f}"] + look),
         "-frames:v", str(r["frames"]), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-an", out])
    return have


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
    ap.add_argument("--grade", help="3D LUT (.cube) mixed over every hook clip and still")
    ap.add_argument("--grade-mix", type=float, default=1.0)
    ap.add_argument("--film-until", help="last scene_id with the film look and letterbox")
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
    if a.grade and not os.path.isfile(a.grade):
        sys.exit(f"ABORT: missing LUT {a.grade}")
    ids = [r["scene_id"] for r in rows]
    if a.film_until and a.film_until not in ids:
        sys.exit(f"ABORT: --film-until {a.film_until} is not in scene-timing.md")
    film_end = ids.index(a.film_until) if a.film_until else -1
    falloff = falloff_png(staging, W, H) if a.film_until else None
    targets = {r["scene_id"]: head for r, head in card_targets(project, rows, hooks, a.film_until)}
    card_frames = round(CARD_S * fps)
    card_look = series_look(project)

    def look(i):
        parts = [grade_chain(a.grade, a.grade_mix)] if a.grade else []
        if i <= film_end:
            parts.append(film_chain(W, H, falloff))
        elif i == film_end + 1 and a.film_until:
            delay = card_frames / fps if rows[i]["scene_id"] in targets else 0.0
            parts.append(lambda w, h: bars_open_chain(fps, w, h, delay))
        return parts

    problems, n = [], {"hook": 0, "still": 0, "overlay": 0, "card": 0}

    def collect(jobs):
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

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        jobs = {}
        for i, r in enumerate(rows):
            sid = r["scene_id"]
            if only and sid not in only:
                continue
            out = os.path.join(staging, "scenes", sid + ".mp4")
            hold = card_frames if sid in targets else 0
            if sid in hooks:
                jobs[ex.submit(hook_job, r, hooks[sid], out, fps, W, H, look(i))] = (sid, out, r["frames"], "hook")
            else:
                jpg = os.path.join(project, "scene-generation", sid + ".jpg")
                if not os.path.isfile(jpg):
                    sys.exit(f"ABORT: missing {jpg}")
                jobs[ex.submit(still_job, r, jpg, out, fps, W, H, words.get(sid), pos.get(sid), a.font, look(i),
                               hold)] = (sid, out, r["frames"], "overlay" if sid in words else "still")
        collect(jobs)

        jobs = {}
        for r in rows:
            sid = r["scene_id"]
            if sid not in targets or (only and sid not in only):
                continue
            clip = os.path.join(staging, "scenes", sid + ".mp4")
            if not os.path.isfile(clip):
                problems.append(f"card {sid}: its scene clip is missing")
                continue
            land = min(card_frames, r["frames"]) - 1
            out = os.path.join(staging, "cards", sid + ".mp4")
            jobs[ex.submit(card_job, targets[sid], clip, land, out, fps, W, H, card_look)] = \
                (sid, out, card_frames, "card")
        collect(jobs)
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
