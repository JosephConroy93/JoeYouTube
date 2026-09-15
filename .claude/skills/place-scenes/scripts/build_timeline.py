#!/usr/bin/env python
"""build_timeline.py -- FCP7 XML timeline from scene-timing.md and pre-rendered clips.

Usage:
    build_timeline.py <project-path> --staging <dir> --fps N --out <xml>
                      [--hook-order a.mp4,b.mp4,...] [--name NAME] [--cards] [--sfx]
                      [--width 1920 --height 1080] [--count-frames] [--loudness -14]

<project-path> is `<series>/<slug>` (resolved under content/) or a directory.

Reads   claude/scene-timing.md                  scene_id, segment, start_seconds (segment-relative)
        <staging>/voiceovers/<segment>.wav|.mp3 audio per segment; sorted stems = playback order
        <staging>/scenes/<scene_id>.mp4         pre-rendered, exact-frame, at --fps
        <staging>/hook/*.mp4                    optional cold open, played first, in --hook-order
        <staging>/cards/<scene_id>.mp4          --cards: level card over the start of that scene (V2)
        claude/sfx-plan.md + <staging>/sfx/<scene_id>.wav
                                                --sfx: baked spot SFX at scene start + offset_s
Writes  <xml>                                   <xmeml version="5">: one sequence, V1 = hook clips
                                                then scenes, V2 = cards, one audio track per
                                                segment, then SFX tracks (packed, no overlaps)

Every position is a frame number: frames(t) = round(t * fps). A scene runs from its own
start frame to the next scene's start frame (the last one to the end of the audio); the
clip on disk must hold exactly that many frames or the build aborts naming the clip.

Resolve imports every XMEML audio track as a MONO track panned centre, which plays 3 dB
under the file and takes channel 1 only. Each audio clip therefore carries an Audio Levels
filter of +MONO_PAN_LAW_DB (the API cannot set clip volume; the XML can), and the WAVs
must be dual-mono. --loudness lifts every audio clip by the same amount again, from the
voice files' -16 LUFS to the finished video's target, so voice and SFX keep their balance.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote

# ----------------------------------------------------------------------------- inputs


def resolve_project(arg):
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    p = os.path.join(root, "content", *arg.replace("\\", "/").split("/"))
    if not os.path.isdir(p):
        sys.exit(f"ABORT: project folder not found: {p}")
    return p


def read_timing(project):
    """scene-timing.md rows in file order -> [{scene_id, chapter, segment, start, end, match}]."""
    path = os.path.join(project, "claude", "scene-timing.md")
    if not os.path.isfile(path):
        sys.exit(f"ABORT: missing {path}")
    rows = []
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s[1:-1].split("|")]
        sid = cells[0].strip("`")
        if len(cells) < 6 or not re.fullmatch(r"\d{3}_[A-Za-z0-9-]+", sid):
            continue
        rows.append({"scene_id": sid, "chapter": cells[1], "segment": cells[2], "start": float(cells[3]),
                     "end": float(cells[4]), "match": cells[5]})
    if not rows:
        sys.exit("ABORT: scene-timing.md has no scene rows")
    return rows


def ffprobe(path, select, entries):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", select, "-show_entries",
                        "stream=" + entries, "-of", "json", path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ABORT: ffprobe failed on {path}: {r.stderr.strip()}")
    streams = json.loads(r.stdout).get("streams") or []
    if not streams:
        sys.exit(f"ABORT: no {select} stream in {path}")
    return streams[0]


def audio_duration(path):
    """Stream duration, never the container's (containers pad)."""
    return float(ffprobe(path, "a:0", "duration")["duration"])


def video_frames(path, fps, count):
    """Frame count of the video stream; --count-frames decodes to be sure."""
    args = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=nb_frames,nb_read_frames,r_frame_rate", "-of", "json"]
    if count:
        args.insert(1, "-count_frames")
    r = subprocess.run(args + [path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ABORT: ffprobe failed on {path}: {r.stderr.strip()}")
    st = json.loads(r.stdout)["streams"][0]
    num, den = (int(x) for x in st["r_frame_rate"].split("/"))
    if den * fps != num:
        sys.exit(f"ABORT: {os.path.basename(path)} is {st['r_frame_rate']} fps, timeline is {fps}; conform it first")
    n = st.get("nb_read_frames") if count else st.get("nb_frames")
    if n in (None, "N/A"):
        sys.exit(f"ABORT: {path} reports no frame count; rerun with --count-frames")
    return int(n)


MONO_PAN_LAW_DB = 3.0
VOICE_FILE_LUFS = -16.0
LEVEL_DB = MONO_PAN_LAW_DB


def frames(seconds, fps):
    return int(round(seconds * fps))


# ----------------------------------------------------------------------------- plan


def build_cards(staging, scenes, fps, count):
    by_id = {s["scene_id"]: s for s in scenes}
    cards = []
    for p in sorted(glob.glob(os.path.join(staging, "cards", "*.mp4"))):
        sid = os.path.splitext(os.path.basename(p))[0]
        if sid not in by_id:
            sys.exit(f"ABORT: card {p} names no scene in the timing file")
        nf = video_frames(p, fps, count)
        if nf > by_id[sid]["frames"]:
            sys.exit(f"ABORT: card {sid} ({nf} frames) is longer than its scene ({by_id[sid]['frames']})")
        cards.append({"name": "card-" + sid[:3], "path": p, "start_frame": by_id[sid]["start_frame"], "frames": nf})
    if not cards:
        sys.exit("ABORT: --cards given but no clips in <staging>/cards")
    return cards


def build_sfx(project, staging, scenes, fps):
    from sfx import read_plan
    by_id = {s["scene_id"]: s for s in scenes}
    tracks = []
    for r in sorted(read_plan(project), key=lambda r: by_id[r["scene_id"]]["start_frame"]):
        p = os.path.join(staging, "sfx", r["scene_id"] + ".wav")
        if not os.path.isfile(p):
            sys.exit(f"ABORT: sfx clip missing: {p} (run sfx.py)")
        sc = by_id[r["scene_id"]]
        start = sc["start_frame"] + frames(r["offset"], fps)
        nf = frames(audio_duration(p), fps)
        if start + nf > sc["start_frame"] + sc["frames"]:
            sys.exit(f"ABORT: sfx {r['scene_id']} runs past its scene")
        item = {"stem": "sfx-" + r["scene_id"][:3], "path": p, "start_frame": start, "end_frame": start + nf}
        for t in tracks:
            if t[-1]["end_frame"] <= start:
                t.append(item)
                break
        else:
            tracks.append([item])
    return tracks


def build_plan(project, staging, fps, hook_order, count):
    rows = read_timing(project)
    stems = []
    for r in rows:
        if r["segment"] not in stems:
            stems.append(r["segment"])
    if stems != sorted(stems):
        sys.exit(f"ABORT: segments are not in sorted (playback) order in scene-timing.md: {stems}")

    # audio: cumulative offsets from real stream durations
    audio, offset = [], 0.0
    for stem in stems:
        cands = [p for ext in (".wav", ".mp3") for p in glob.glob(os.path.join(staging, "voiceovers", stem + ext))]
        if not cands:
            sys.exit(f"ABORT: no audio for segment {stem} in {os.path.join(staging, 'voiceovers')}")
        dur = audio_duration(cands[0])
        audio.append({"stem": stem, "path": cands[0], "offset": offset, "duration": dur,
                      "start_frame": frames(offset, fps), "end_frame": frames(offset + dur, fps)})
        offset += dur
    total_frames = frames(offset, fps)
    off = {a["stem"]: a["offset"] for a in audio}

    # scenes: global start frames, duration = to the next scene's start
    scenes = []
    for r in rows:
        scenes.append({"scene_id": r["scene_id"], "start_frame": frames(off[r["segment"]] + r["start"], fps),
                       "path": os.path.join(staging, "scenes", r["scene_id"] + ".mp4")})
    for a, b in zip(scenes, scenes[1:]):
        a["frames"] = b["start_frame"] - a["start_frame"]
    scenes[-1]["frames"] = total_frames - scenes[-1]["start_frame"]

    problems = [f"{s['scene_id']}: planned {s['frames']} frames (non-positive)" for s in scenes if s["frames"] <= 0]
    problems += [f"{s['scene_id']}: clip missing at {s['path']}" for s in scenes if not os.path.isfile(s["path"])]
    if problems:
        sys.exit("ABORT:\n  " + "\n  ".join(problems))
    for s in scenes:
        s["clip_frames"] = video_frames(s["path"], fps, count)
        if s["clip_frames"] != s["frames"]:
            problems.append(f"{s['scene_id']}: clip has {s['clip_frames']} frames, plan needs {s['frames']}")
    if problems:
        sys.exit("ABORT: pre-rendered clips do not match the plan --\n  " + "\n  ".join(problems))

    # hook: fills frame 0 .. first scene start, in the given order
    hook_dir = os.path.join(staging, "hook")
    names = hook_order or sorted(os.path.basename(p) for p in glob.glob(os.path.join(hook_dir, "*.mp4")))
    hook, pos = [], 0
    for n in names:
        p = os.path.join(hook_dir, n)
        if not os.path.isfile(p):
            sys.exit(f"ABORT: hook clip not found: {p}")
        nf = video_frames(p, fps, count)
        hook.append({"name": os.path.splitext(n)[0], "path": p, "start_frame": pos, "frames": nf})
        pos += nf
    first = scenes[0]["start_frame"]
    if pos != first:
        sys.exit(f"ABORT: hook clips total {pos} frames but the first scene starts at frame {first} "
                 f"({'gap' if pos < first else 'overlap'} of {abs(first - pos)}); recut the hook to the beats")
    if not hook_order and len(hook) > 1:
        print(f"note: hook order taken from filenames ({', '.join(names)}); pass --hook-order if the beats differ")

    # contiguity assertions
    assert all(a["start_frame"] + a["frames"] == b["start_frame"] for a, b in zip(hook + scenes, (hook + scenes)[1:]))
    assert scenes[-1]["start_frame"] + scenes[-1]["frames"] == total_frames == audio[-1]["end_frame"]
    assert all(a["end_frame"] == b["start_frame"] for a, b in zip(audio, audio[1:]))
    return hook, scenes, audio, total_frames


# ----------------------------------------------------------------------------- xml


def pathurl(path):
    return "file://localhost/" + quote(os.path.abspath(path).replace("\\", "/"), safe="/:")


def sub(parent, tag, text=None):
    e = ET.SubElement(parent, tag)
    if text is not None:
        e.text = str(text)
    return e


def rate(parent, fps):
    r = sub(parent, "rate")
    sub(r, "timebase", fps)
    sub(r, "ntsc", "FALSE")
    return r


def file_elem(parent, fid, path, fps, dur, width, height, audio):
    f = sub(parent, "file")
    f.set("id", fid)
    sub(f, "name", os.path.basename(path))
    sub(f, "pathurl", pathurl(path))
    rate(f, fps)
    sub(f, "duration", dur)
    media = sub(f, "media")
    if audio:
        a = sub(media, "audio")
        sc = sub(a, "samplecharacteristics")
        sub(sc, "depth", 16)
        sub(sc, "samplerate", 48000)
        sub(a, "channelcount", 2)
    else:
        v = sub(media, "video")
        sc = sub(v, "samplecharacteristics")
        rate(sc, fps)
        sub(sc, "width", width)
        sub(sc, "height", height)


def clipitem(track, cid, name, path, fps, start, nframes, width, height, audio):
    c = sub(track, "clipitem")
    c.set("id", cid)
    sub(c, "name", name)
    sub(c, "enabled", "TRUE")
    sub(c, "duration", nframes)
    rate(c, fps)
    sub(c, "start", start)
    sub(c, "end", start + nframes)
    sub(c, "in", 0)
    sub(c, "out", nframes)
    file_elem(c, cid + "-file", path, fps, nframes, width, height, audio)
    if audio:
        st = sub(c, "sourcetrack")
        sub(st, "mediatype", "audio")
        sub(st, "trackindex", 1)
        flt = sub(c, "filter")
        sub(flt, "enabled", "TRUE")
        sub(flt, "start", 0)
        sub(flt, "end", nframes)
        eff = sub(flt, "effect")
        for tag, text in (("name", "Audio Levels"), ("effectid", "audiolevels"), ("effecttype", "audiolevels"),
                          ("mediatype", "audio"), ("effectcategory", "audiolevels")):
            sub(eff, tag, text)
        par = sub(eff, "parameter")
        sub(par, "name", "Level")
        sub(par, "parameterid", "level")
        sub(par, "value", f"{10 ** (LEVEL_DB / 20):.7f}")
        sub(par, "valuemin", "1e-05")
        sub(par, "valuemax", "31.6228")


def write_xml(out, name, fps, width, height, hook, scenes, audio, total_frames, cards=(), sfx=()):
    root = ET.Element("xmeml", version="5")
    seq = sub(root, "sequence")
    sub(seq, "name", name)
    sub(seq, "duration", total_frames)
    rate(seq, fps)
    media = sub(seq, "media")
    video = sub(media, "video")
    fmt = sub(video, "format")
    sc = sub(fmt, "samplecharacteristics")
    rate(sc, fps)
    sub(sc, "width", width)
    sub(sc, "height", height)
    vt = sub(video, "track")
    for k, h in enumerate(hook):
        clipitem(vt, f"hook-{k + 1}", h["name"], h["path"], fps, h["start_frame"], h["frames"], width, height, False)
    for s in scenes:
        clipitem(vt, s["scene_id"], s["scene_id"], s["path"], fps, s["start_frame"], s["frames"], width, height, False)
    if cards:
        ct = sub(video, "track")
        for c in cards:
            clipitem(ct, c["name"], c["name"], c["path"], fps, c["start_frame"], c["frames"], width, height, False)
    aud = sub(media, "audio")
    for a in audio:
        at = sub(aud, "track")
        clipitem(at, "vo-" + a["stem"], a["stem"], a["path"], fps, a["start_frame"],
                 a["end_frame"] - a["start_frame"], width, height, True)
    for t in sfx:
        at = sub(aud, "track")
        for a in t:
            clipitem(at, a["stem"], a["stem"], a["path"], fps, a["start_frame"],
                     a["end_frame"] - a["start_frame"], width, height, True)
    tree = ET.ElementTree(root)
    ET.indent(tree)
    with open(out, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)


def validate(out, total_frames):
    """Re-parse the written file and check the ends line up."""
    seq = ET.parse(out).getroot().find("sequence")
    v = seq.find("media/video/track").findall("clipitem")
    a = seq.findall("media/audio/track/clipitem")
    v_end = max(int(c.findtext("end")) for c in v)
    a_end = max(int(c.findtext("end")) for c in a)
    v_frames = sum(int(c.findtext("duration")) for c in v)
    if not (v_end == a_end == total_frames == v_frames):
        sys.exit(f"ABORT: written XML disagrees: video end {v_end}, audio end {a_end}, "
                 f"video frames {v_frames}, planned {total_frames}")
    return len(v), len(a), v_frames


def timecode(n, fps):
    s, f = divmod(n, fps)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--staging", required=True, help="local staging folder with hook/, scenes/, voiceovers/")
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--out", required=True, help="path of the FCP7 XML to write")
    ap.add_argument("--hook-order", help="comma-separated hook clip filenames in beat order")
    ap.add_argument("--name", help="sequence name (default: <slug> v1)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--count-frames", action="store_true", help="decode every clip to count frames (slow, exact)")
    ap.add_argument("--cards", action="store_true", help="place <staging>/cards/<scene_id>.mp4 on V2")
    ap.add_argument("--sfx", action="store_true", help="place claude/sfx-plan.md clips from <staging>/sfx/")
    ap.add_argument("--loudness", type=float, default=VOICE_FILE_LUFS, help="finished video's integrated LUFS")
    a = ap.parse_args()
    global LEVEL_DB
    LEVEL_DB = MONO_PAN_LAW_DB + a.loudness - VOICE_FILE_LUFS

    project = resolve_project(a.project)
    staging = os.path.abspath(a.staging)
    if not os.path.isdir(staging):
        sys.exit(f"ABORT: staging folder not found: {staging}")
    hook_order = [n.strip() for n in a.hook_order.split(",")] if a.hook_order else None
    name = a.name or f"{os.path.basename(project)} v1"

    hook, scenes, audio, total = build_plan(project, staging, a.fps, hook_order, a.count_frames)
    cards = build_cards(staging, scenes, a.fps, a.count_frames) if a.cards else []
    sfx = build_sfx(project, staging, scenes, a.fps) if a.sfx else []
    write_xml(a.out, name, a.fps, a.width, a.height, hook, scenes, audio, total, cards, sfx)
    nv, na, vf = validate(a.out, total)
    print(f"wrote {a.out}")
    print(f"  sequence '{name}' @ {a.fps} fps: {total} frames ({timecode(total, a.fps)})")
    print(f"  video: {len(hook)} hook + {len(scenes)} scenes = {nv} items, {vf} frames; "
          f"first scene at frame {scenes[0]['start_frame']}, last ends {scenes[-1]['start_frame'] + scenes[-1]['frames']}")
    print(f"  audio: {len(audio)} voice tracks, ends frame {audio[-1]['end_frame']}; "
          f"{sum(len(t) for t in sfx)} sfx on {len(sfx)} tracks; clip level +{LEVEL_DB:.1f} dB")
    for c in cards:
        print(f"  {c['name']}: V2 frames {c['start_frame']}-{c['start_frame'] + c['frames']}")
    for h in hook:
        print(f"  hook {h['name']}: frames {h['start_frame']}-{h['start_frame'] + h['frames']}")


if __name__ == "__main__":
    main()
