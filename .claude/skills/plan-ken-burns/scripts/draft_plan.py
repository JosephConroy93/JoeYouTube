#!/usr/bin/env python
"""draft_plan.py -- write ken-burns-plan.md from the timing, the manifest and the confirmed picks.

Usage:
    draft_plan.py <series>/<slug> --fps N [--out <file>] [--replace] [--film-until <scene_id>]
                  [--pan NNN:right|left|down|up[:note]] ...
                  [--focal NNN:x,y[:note]] ...
                  [--caution NNN:note] ...
                  [--summary-extra "text"]

The judgment stays with the planner: which scenes are Elevated (image-confirmed by subagents)
and which carry a caution. This script applies the mechanical rules of the skill to every
other row, so they hold across 150 scenes:

  Static    hook-clip rows (claude/hook-plan.md), text-card rows, and every row up to
            --film-until (video.md film_open: letterbox bars baked into the clip)
  Pan       static Size 1.20, Transform Center travels +-0.08 (camera right = Center.x falls)
  Focal     pivot at the target, Size 1.00 -> 1.20, EI
  last scene of each chapter      Out + EO (the release)
  "Wide ..." prompt                Out + L
  "Close ..." / "Medium close ..." In + EI
  anything else                    alternates In + EI / Out + L against the previous row
  caution                          Out + L, note kept
  no combo more than 3 rows running (chapter ends and cautions excepted)

dur = the scene's frames in place-scenes' frame plan (start to the next scene's start, across
segment joins) / fps. Refuses to overwrite a plan unless --replace, which archives it first.
"""
import argparse
import glob
import os
import re
import shutil
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "place-scenes", "scripts"))
from build_timeline import audio_duration, frames, read_timing, resolve_project  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
TRAVEL, PAN_SIZE = 0.08, 1.2


def frame_plan(project, fps):
    rows = read_timing(project)
    off, t = {}, 0.0
    for r in rows:
        if r["segment"] not in off:
            off[r["segment"]] = None
    for stem in off:
        wav = os.path.join(project, "voiceovers", "normalized", stem + ".wav")
        if not os.path.isfile(wav):
            sys.exit(f"ABORT: missing {wav}")
        off[stem] = t
        t += audio_duration(wav)
    for r in rows:
        r["start_frame"] = frames(off[r["segment"]] + r["start"], fps)
    for a, b in zip(rows, rows[1:]):
        a["frames"] = b["start_frame"] - a["start_frame"]
    rows[-1]["frames"] = frames(t, fps) - rows[-1]["start_frame"]
    return rows


def manifest(project):
    out = {}
    for f in sorted(glob.glob(os.path.join(project, "claude", "scene-prompts", "*.md"))):
        for line in open(f, encoding="utf-8"):
            m = re.match(r"\|\s*`?(\d{3}_[A-Za-z0-9-]+)`?\s*\|(.*)", line)
            if m:
                c = [x.strip() for x in m.group(2).split("|")]
                out[m.group(1)] = {"type": c[1] if len(c) > 1 else "", "prompt": c[2] if len(c) > 2 else ""}
    return out


def hooks(project):
    path = os.path.join(project, "claude", "hook-plan.md")
    if not os.path.isfile(path):
        return set()
    return {m.group(1) for line in open(path, encoding="utf-8")
            if (m := re.match(r"\|\s*\d+\s*\|\s*`?(\d{3}_[A-Za-z0-9-]+)`?\s*\|", line))}


def headings(project, chapters):
    text = open(os.path.join(project, "claude", "script.md"), encoding="utf-8").read()
    text = re.split(r"^##\s+Handoff notes", text, flags=re.M)[0]
    heads = [m.group(1) for m in re.finditer(r"^##\s+(.+?)\s*$", text, re.M)]
    return heads if len(heads) == len(chapters) else chapters


def split_pick(arg, flag):
    parts = arg.split(":", 2)
    if len(parts) < 2 or not re.fullmatch(r"\d{3}", parts[0]):
        sys.exit(f"ABORT: {flag} {arg!r} is not NNN:value[:note]")
    return parts[0], parts[1], parts[2] if len(parts) > 2 else ""


def pan_coords(direction):
    a, b = f"{0.5 + TRAVEL:.2f}", f"{0.5 - TRAVEL:.2f}"
    return {"right": f"Pan right ({a},0.50)→({b},0.50)", "left": f"Pan left ({b},0.50)→({a},0.50)",
            "down": f"Pan down (0.50,{a})→(0.50,{b})", "up": f"Pan up (0.50,{b})→(0.50,{a})"}[direction]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--out")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--pan", action="append", default=[])
    ap.add_argument("--focal", action="append", default=[])
    ap.add_argument("--caution", action="append", default=[])
    ap.add_argument("--summary-extra", default="")
    ap.add_argument("--film-until", help="video.md film_open: last scene_id with baked letterbox bars")
    a = ap.parse_args()

    project = resolve_project(a.project)
    out = a.out or os.path.join(project, "claude", "ken-burns-plan.md")
    if os.path.exists(out):
        if not a.replace:
            sys.exit(f"ABORT: {out} exists (the operator may have edited it); pass --replace to archive and rewrite")
        arch = os.path.join(os.path.dirname(out), "_archive")
        os.makedirs(arch, exist_ok=True)
        n = len(glob.glob(os.path.join(arch, "ken-burns-plan.*.md"))) + 1
        shutil.move(out, os.path.join(arch, f"ken-burns-plan.{n}.md"))

    rows, man, hook = frame_plan(project, a.fps), manifest(project), hooks(project)
    missing = [r["scene_id"] for r in rows if r["scene_id"] not in man]
    if missing:
        sys.exit(f"ABORT: timing rows with no manifest row: {missing}")
    elev = {}
    for p in a.pan:
        n, d, note = split_pick(p, "--pan")
        if d not in ("right", "left", "down", "up"):
            sys.exit(f"ABORT: --pan direction {d!r}")
        elev[n] = (pan_coords(d), "L", note or f"Pan {d}, no zoom.")
    for p in a.focal:
        n, xy, note = split_pick(p, "--focal")
        x, y = (float(v) for v in xy.split(","))
        elev[n] = (f"Focal ({x:.2f},{y:.2f})", "EI", note or "Focal push to the target.")
    caution = {}
    for c in a.caution:
        n, note, rest = split_pick(c, "--caution")
        caution[n] = note + (":" + rest if rest else "")

    ids = [r["scene_id"] for r in rows]
    if a.film_until and a.film_until not in ids:
        sys.exit(f"ABORT: --film-until {a.film_until} is not in the frame plan")
    film = set(ids[: ids.index(a.film_until) + 1]) if a.film_until else set()
    chapter = {r["scene_id"]: re.sub(r"(\d+)[a-z]\.md$", r"\1.md", r["chapter"]) for r in rows}
    last_of = {}
    for r in rows:
        last_of[chapter[r["scene_id"]]] = r["scene_id"]
    plan, prev = [], []
    for r in rows:
        sid, n = r["scene_id"], r["scene_id"][:3]
        prompt, note = man[sid]["prompt"].lower(), ""
        if sid in hook:
            zoom, ease, note = "Static", "", "Hook clip (the footage already moves)."
        elif sid in film:
            zoom, ease, note = "Static", "", "Film open: letterbox bars baked in."
        elif man[sid]["type"] == "text-card":
            zoom, ease, note = "Static", "", "Text-card; overlay word drawn at the edit."
        elif n in elev:
            zoom, ease, note = elev[n]
        else:
            if sid == last_of[chapter[sid]]:
                zoom, ease = "Out", "EO"
            elif prompt.startswith("wide"):
                zoom, ease = "Out", "L"
            elif prompt.startswith("close") or prompt.startswith("medium close"):
                zoom, ease = "In", "EI"
            else:
                zoom, ease = ("In", "EI") if not prev or prev[-1][0] != "In" else ("Out", "L")
            if n in caution:
                zoom, ease, note = "Out", "L", "Caution: " + caution[n]
            elif len(prev) >= 3 and all(x == (zoom, ease) for x in prev[-3:]) and sid != last_of[r["chapter"]]:
                zoom, ease = ("Out", "L") if zoom == "In" else ("In", "EI")
        prev.append((zoom.split()[0], ease))
        plan.append((r, zoom, ease, note))

    chapters = list(dict.fromkeys(r["chapter"] for r in rows))
    heads = dict(zip(chapters, headings(project, chapters)))
    L = [f"# Ken Burns plan (`{a.project}`)", "",
         f"Schema: `.claude/conventions.md` (\"ken-burns-plan.md\"). {a.fps} fps; `dur` in seconds from the frame plan "
         "(scene start to the next scene's start). Drafted by `plan-ken-burns/scripts/draft_plan.py` from image-confirmed picks; "
         "the operator watches the cut and overrides.", "",
         "**Legend.** `In` = Size 1.00→1.15 about the centre; `Out` = 1.15→1.00; combos limited to Out+L, In+EI, Out+EO. "
         "`Focal (x,y)` = pivot at the target (top-left image fractions), Size 1.00→1.20, EI. "
         f"`Pan <dir> (x,y)→(x,y)` = Transform `Center` start→end in top-left fractions (`apply-fusion` flips Y), static Size {PAN_SIZE:.2f} "
         f"for headroom (travel ±{TRAVEL:.2f}), linear, no animated zoom; camera travelling right = `Center.x` falling. "
         "Static = hook clips and text-cards."]
    cur = None
    for i, (r, zoom, ease, note) in enumerate(plan, 1):
        if r["chapter"] != cur:
            cur = r["chapter"]
            L += ["", f"## {heads[cur]}", "", "| # | scene_id | dur | zoom | ease | transition | note |", "|---|---|---|---|---|---|---|"]
        L.append(f"| {i} | `{r['scene_id']}` | {r['frames'] / a.fps:.2f} | {zoom} | {ease} |  | {note} |")
    kinds = Counter(z.split()[0] for _, z, _, _ in plan)
    static, elevated = kinds["Static"], kinds["Pan"] + kinds["Focal"]
    n_all = len(plan)
    cautions = [r["scene_id"][:3] for r, _, _, note in plan if note.startswith("Caution")]
    summary = (f"{n_all} scenes: Baseline {kinds['In'] + kinds['Out']} (In {kinds['In']}, Out {kinds['Out']}), "
               f"Static {static} ({100 * static / n_all:.0f}%), Elevated {elevated} ({100 * elevated / n_all:.1f}%: "
               f"{kinds['Pan']} pans, {kinds['Focal']} focal), no particle effects, no transitions. Each chapter ends on Out+EO. "
               f"Caution notes: {', '.join(cautions) or 'none'}.")
    L += ["", "## Summary", "", (summary + " " + a.summary_extra).strip()]
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    if elevated > 0.1 * n_all:
        print(f"WARNING: Elevated {elevated} is over 10% of {n_all}")
    print(f"wrote {out}: " + summary)


if __name__ == "__main__":
    main()
