#!/usr/bin/env python
"""align.py -- per-scene timing from real voiceover audio.

Usage:
    align.py <project-path> [--source whisper|api] [--fps N] [--out PATH]
             [--model tiny] [--fuzzy-min 0.7]

<project-path> is `<series>/<slug>` (resolved under content/) or a directory.

Reads   claude/scene-prompts.md                 index -> chapter files, in order
        claude/scene-prompts/<chapter>.md       rows: scene_id, script_bookmark
        voiceovers/<stem>.mp3                   segment stems, sorted = playback order
        claude/transcripts/<stem>.json          whisper JSON  (--source whisper)
        claude/transcripts/<stem>.alignment.json TTS alignment (--source api)  # UNTESTED end-to-end
        (an mp3 with no whisper JSON is transcribed here: whisper CLI, --model tiny)
Writes  claude/scene-timing.md                  (or --out)

Schema: | scene_id | chapter | segment | start_seconds | end_seconds | match |
match = exact | fuzzy(NN%) | interpolated | api ; seconds are segment-relative.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

# ----------------------------------------------------------------------------- paths


def resolve_project(arg):
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    p = os.path.join(root, "content", *arg.replace("\\", "/").split("/"))
    if not os.path.isdir(p):
        sys.exit(f"ABORT: project folder not found: {p}")
    return p


def split_row(line):
    """Split a markdown table row by column boundary. None if not a row."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|") and len(s) > 1):
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def read_kv_table(path):
    """`| key | value |` rows -> dict. Missing file -> {}."""
    out = {}
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding="utf-8"):
        cells = split_row(line)
        if cells and len(cells) >= 2:
            out[cells[0].strip("`").strip()] = cells[1].strip().strip("`")
    return out


# ----------------------------------------------------------------------------- manifest

SCENE_ID = re.compile(r"^\d{3}_[A-Za-z0-9-]+$")
ROW_START = re.compile(r"^\|\s*`?(\d{3}_[A-Za-z0-9-]+)`?\s*\|")   # scene ids with or without backticks


def chapter_files(project):
    """Chapter files named in the manifest index, in index order, plus any declared scene counts."""
    index = os.path.join(project, "claude", "scene-prompts.md")
    if not os.path.isfile(index):
        sys.exit(f"ABORT: manifest index missing: {index}")
    folder = os.path.join(project, "claude", "scene-prompts")
    found, declared = [], {}
    for line in open(index, encoding="utf-8"):
        cells = split_row(line)
        if not cells:
            continue
        names = [n for n in re.findall(r"([\w.-]+\.md)", " ".join(cells))
                 if os.path.isfile(os.path.join(folder, n))]
        if not names or names[0] in found:
            continue
        found.append(names[0])
        ints = [c for c in cells if re.fullmatch(r"\d+", c)]
        if ints:
            declared[names[0]] = int(ints[0])
    if not found:
        sys.exit("ABORT: no chapter files referenced in claude/scene-prompts.md")
    return found, declared


def strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in "\"“" and s[-1] in "\"”":
        return s[1:-1]
    return s


def parse_chapter(path):
    """Rows -> [(scene_id, bookmark)] plus the ids present. Parse by column, never by quote pair."""
    rows, present = [], []
    for line in open(path, encoding="utf-8"):
        m = ROW_START.match(line)
        if m:
            present.append(m.group(1))
        cells = split_row(line)
        if not cells or len(cells) < 2:
            continue
        sid = cells[0].strip("`").strip()
        if SCENE_ID.match(sid):
            rows.append((sid, strip_quotes(cells[1])))
    return rows, present


def load_manifest(project):
    files, declared = chapter_files(project)
    scenes, problems = [], []
    for name in files:
        rows, present = parse_chapter(os.path.join(project, "claude", "scene-prompts", name))
        ids = [r[0] for r in rows]
        if len(rows) != len(present):
            missing = [i for i in present if i not in ids]
            problems.append(f"{name}: {len(present)} scene rows present, {len(rows)} parsed; missing {missing}")
        if name in declared and declared[name] != len(rows):
            problems.append(f"{name}: index declares {declared[name]} scenes, file yields {len(rows)}")
        for sid, bm in rows:
            if not bm:
                problems.append(f"{name}: {sid} has an empty script_bookmark")
            scenes.append({"scene_id": sid, "chapter": name, "bookmark": bm})
    if problems:
        sys.exit("ABORT: manifest row-count mismatch --\n  " + "\n  ".join(problems))
    seen, dupes = set(), set()
    for s in scenes:
        (dupes if s["scene_id"] in seen else seen).add(s["scene_id"])
    if dupes:
        sys.exit(f"ABORT: duplicate scene ids: {sorted(dupes)}")
    return scenes


# ----------------------------------------------------------------------------- text normalisation

NUM_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
             "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
             "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
TENS = {"twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"}
PUNCT = ".,;:!?\"'’—-"


def norm(s):
    return s.strip().lower().strip(PUNCT)


def numeralize(tokens):
    """'three hundred' -> '300', 'a hundred' -> '100', 'twenty six' -> '26'."""
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in NUM_WORDS or t == "a":
            base = NUM_WORDS.get(t, 1 if t == "a" else None)
            j = i + 1
            if base is not None and j < len(tokens) and tokens[j] == "hundred":
                total, j = base * 100, j + 1
                if j < len(tokens) and tokens[j] in NUM_WORDS and NUM_WORDS[tokens[j]] < 100:
                    total += NUM_WORDS[tokens[j]]
                    j += 1
                out.append(str(total))
                i = j
                continue
            if t in TENS and j < len(tokens) and tokens[j] in NUM_WORDS and NUM_WORDS[tokens[j]] < 10:
                out.append(str(NUM_WORDS[t] + NUM_WORDS[tokens[j]]))
                i = j + 1
                continue
        out.append(t)
        i += 1
    return out


def tokenize(text):
    return numeralize([w for w in (norm(t) for t in text.split()) if w])


# ----------------------------------------------------------------------------- timing sources


def segment_stems(project):
    """Playback order = sorted voiceovers/*.mp3 stems (the audio is the authority);
    segment .txt files without audio are reported, never timed."""
    def stems_in(*parts, ext):
        return sorted(os.path.splitext(os.path.basename(p))[0]
                      for p in glob.glob(os.path.join(project, *parts, "*" + ext)))
    stems = stems_in("voiceovers", ext=".mp3")
    texts = stems_in("claude", "voiceover-segments", ext=".txt")
    if not stems:
        stems = texts
    if not stems:
        sys.exit("ABORT: no segments found (voiceovers/*.mp3 or claude/voiceover-segments/*.txt)")
    orphans = [t for t in texts if t not in stems]
    if orphans:
        print("note: segment text without audio, ignored: " + ", ".join(orphans))
    return stems


def words_from_whisper(data):
    out = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            n = norm(w["word"])
            if n:
                out.append({"norm": n, "start": float(w["start"]), "end": float(w["end"])})
    return out


def words_from_api(data):
    """TTS alignment (characters + per-character start/end seconds) -> word list.
    Checked on a synthetic alignment only; not yet run on a real TTS file."""
    al = data.get("alignment") or data.get("normalized_alignment") or data
    try:
        chars, starts, ends = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    except (KeyError, TypeError):
        sys.exit("ABORT: alignment JSON lacks characters / character_start_times_seconds / character_end_times_seconds")
    out, buf = [], []

    def flush():
        if buf:
            n = norm("".join(c for c, _, _ in buf))
            if n:
                out.append({"norm": n, "start": float(buf[0][1]), "end": float(buf[-1][2])})
        buf.clear()

    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            flush()
        else:
            buf.append((ch, s, e))
    flush()
    return out


def transcribe(project, stems, model):
    """One sequential whisper loop over every stem lacking a JSON. Run this script in the background.
    # UNTESTED in this script (the same command line was used by hand to make the existing JSONs)"""
    tdir = os.path.join(project, "claude", "transcripts")
    os.makedirs(tdir, exist_ok=True)
    for stem in stems:
        mp3 = os.path.join(project, "voiceovers", stem + ".mp3")
        if not os.path.isfile(mp3):
            sys.exit(f"ABORT: no transcript and no audio for segment {stem} ({mp3})")
        print(f"whisper: {stem} ...", flush=True)
        r = subprocess.run(["whisper", mp3, "--model", model, "--word_timestamps", "True",
                            "--output_format", "json", "--output_dir", tdir])
        if r.returncode != 0:
            sys.exit(f"ABORT: whisper failed on {stem} (exit {r.returncode})")


def load_segments(project, source, model):
    stems = segment_stems(project)
    tdir = os.path.join(project, "claude", "transcripts")
    suffix = ".alignment.json" if source == "api" else ".json"
    missing = [s for s in stems if not os.path.isfile(os.path.join(tdir, s + suffix))]
    if missing:
        if source == "api":
            sys.exit("ABORT: --source api needs claude/transcripts/<stem>.alignment.json for: " + ", ".join(missing))
        transcribe(project, missing, model)
    segments = []
    for stem in stems:
        data = json.load(open(os.path.join(tdir, stem + suffix), encoding="utf-8"))
        words = words_from_api(data) if source == "api" else words_from_whisper(data)
        if not words:
            sys.exit(f"ABORT: transcript for {stem} has no words")
        segments.append({"stem": stem, "words": words, "duration": words[-1]["end"]})
    return segments


# ----------------------------------------------------------------------------- matching


def exact_hits(words, target):
    """Every position where the full token sequence occurs -> [(start, end)]."""
    n, hits = len(target), []
    for i in range(len(words) - n + 1):
        if all(words[i + j]["norm"] == target[j] for j in range(n)):
            hits.append((words[i]["start"], words[i + n - 1]["end"]))
    return hits


def fuzzy_match(words, target, min_ratio):
    n = len(target)
    best, best_score = None, 0
    for i in range(len(words) - n + 1):
        ratio = sum(1 for j in range(n) if words[i + j]["norm"] == target[j]) / n
        if ratio > best_score:
            best_score, best = ratio, (words[i]["start"], words[i + n - 1]["end"], ratio)
    return best if best and best_score >= min_ratio else None


def match_all(scenes, segments, fuzzy_min, source):
    """Steps 1-5: exact hits across every segment; an ambiguous exact is resolved by
    playback order (the one hit between its matched neighbours), else best fuzzy;
    still nothing -> left for interpolation and flagged."""
    flags, seg_index = [], {s["stem"]: k for k, s in enumerate(segments)}
    kind = "api" if source == "api" else "exact"
    pending = []
    for sc in scenes:
        sc.update(segment=None, start=None, end=None, match=None)
        target = tokenize(sc["bookmark"])
        if not target:
            flags.append(f"{sc['scene_id']}: bookmark has no matchable words")
            continue
        hits = [(k, s, e) for k, seg in enumerate(segments) for s, e in exact_hits(seg["words"], target)]
        if len(hits) == 1:
            k, s, e = hits[0]
            sc.update(segment=segments[k]["stem"], start=s, end=e, match=kind)
        else:
            pending.append((sc, target, hits))

    def pos(sc, edge):
        return (seg_index[sc["segment"]], sc[edge]) if sc["match"] else None

    for sc, target, hits in pending:
        if len(hits) > 1:
            i = scenes.index(sc)
            prev = next((pos(p, "end") for p in reversed(scenes[:i]) if p["match"]), None)
            nxt = next((pos(n, "start") for n in scenes[i + 1:] if n["match"]), None)
            ok = [h for h in hits if (prev is None or (h[0], h[1]) >= prev) and (nxt is None or (h[0], h[2]) <= nxt)]
            if len(ok) == 1:
                k, s, e = ok[0]
                sc.update(segment=segments[k]["stem"], start=s, end=e, match=kind)
                continue
            flags.append(f"{sc['scene_id']}: exact match at {len(hits)} positions, {len(ok)} in playback order "
                         "-- interpolated instead; resolve by hand")
            continue
        best = None
        for seg in segments:
            f = fuzzy_match(seg["words"], target, fuzzy_min)
            if f and (best is None or f[2] > best[1][2]):
                best = (seg, f)
        if best:
            seg, (s, e, r) = best
            sc.update(segment=seg["stem"], start=s, end=e,
                      match="api" if source == "api" else f"fuzzy({round(r * 100)}%)")
        else:
            flags.append(f"{sc['scene_id']}: no exact or fuzzy match -- \"{sc['bookmark']}\"")
    return flags


def interpolate(scenes, segments, wide_span=12.0):
    """Split each unmatched run equally between its matched neighbours (same segment only)."""
    seg_dur = {s["stem"]: s["duration"] for s in segments}
    flags, i, n = [], 0, len(scenes)
    while i < n:
        if scenes[i]["match"]:
            i += 1
            continue
        j = i
        while j < n and not scenes[j]["match"]:
            j += 1
        run, prev, nxt = scenes[i:j], (scenes[i - 1] if i > 0 else None), (scenes[j] if j < n else None)
        if prev and nxt and prev["segment"] == nxt["segment"]:
            stem, lo, hi = prev["segment"], prev["end"], nxt["start"]
        elif prev and not nxt:  # UNTESTED: run at the very end of the last segment
            stem, lo, hi = prev["segment"], prev["end"], seg_dur[prev["segment"]]
        elif nxt and not prev:  # UNTESTED: run at the very start of the first segment
            stem, lo, hi = nxt["segment"], 0.0, nxt["start"]
        else:
            ids = ", ".join(s["scene_id"] for s in run)
            sys.exit(f"ABORT: unmatched run straddles a segment boundary, cannot interpolate: {ids}")
        hi = max(hi, lo)
        step = (hi - lo) / len(run)
        for k, sc in enumerate(run):
            sc.update(segment=stem, start=lo + k * step, end=lo + (k + 1) * step, match="interpolated")
            if step > wide_span:
                flags.append(f"{sc['scene_id']}: interpolated span {step:.1f}s is suspiciously wide")
        i = j
    return flags


# ----------------------------------------------------------------------------- output


def frame_report(scenes, segments, fps):
    lines, by_seg = [], {}
    for sc in scenes:
        by_seg.setdefault(sc["segment"], []).append(sc)
    for seg in segments:
        rows = by_seg.get(seg["stem"], [])
        if not rows:
            lines.append(f"  {seg['stem']}: no scenes matched here -- check the manifest")
            continue
        for a, b in zip(rows, rows[1:]):
            overlap = round(a["end"] * fps) - round(b["start"] * fps)
            if overlap > 1:
                lines.append(f"  {seg['stem']}: {a['scene_id']} overlaps {b['scene_id']} by {overlap} frames")
        lines.append(f"  {seg['stem']}: {len(rows)} scenes, last word at frame {round(seg['duration'] * fps)}")
    return lines


def match_counts(scenes):
    counts = {}
    for sc in scenes:
        key = sc["match"].split("(")[0]
        counts[key] = counts.get(key, 0) + 1
    return counts


def write_timing(path, scenes, source):
    summary = ", ".join(f"{v} {k}" for k, v in sorted(match_counts(scenes).items()))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Scene timing\n\n")
        f.write(f"Written by `align-scenes` (`--source {source}`). Seconds are segment-relative; "
                f"`match` = `exact` / `fuzzy(NN%)` / `interpolated` / `api`. "
                f"{len(scenes)} scenes: {summary}.\n\n")
        f.write("| scene_id | chapter | segment | start_seconds | end_seconds | match |\n")
        f.write("|---|---|---|---|---|---|\n")
        for sc in scenes:
            f.write(f"| `{sc['scene_id']}` | {sc['chapter']} | {sc['segment']} | "
                    f"{sc['start']:.2f} | {sc['end']:.2f} | {sc['match']} |\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--source", choices=["whisper", "api"], default="whisper")
    ap.add_argument("--fps", type=int, help="frame-overlap report only; default from video.md / series.md")
    ap.add_argument("--out", help="write here instead of claude/scene-timing.md")
    ap.add_argument("--model", default="tiny", help="whisper model (timing only, accuracy of text is irrelevant)")
    ap.add_argument("--fuzzy-min", type=float, default=0.7)
    a = ap.parse_args()

    project = resolve_project(a.project)
    # config cells may carry a note after the number ("24 (Veo clips are native 24 fps)")
    fps_cell = (read_kv_table(os.path.join(project, "video.md")).get("fps") or
                read_kv_table(os.path.join(os.path.dirname(project), "series.md")).get("fps_default") or "0")
    fps = a.fps or int(re.match(r"\s*`?(\d+)", fps_cell).group(1))

    scenes = load_manifest(project)
    print(f"manifest: {len(scenes)} scenes across {len({s['chapter'] for s in scenes})} chapter files")
    segments = load_segments(project, a.source, a.model)
    print("segments: " + ", ".join(f"{s['stem']} ({len(s['words'])} words)" for s in segments))

    flags = match_all(scenes, segments, a.fuzzy_min, a.source)
    flags += interpolate(scenes, segments)
    unresolved = [s["scene_id"] for s in scenes if not s["match"]]
    if unresolved:
        sys.exit("ABORT: rows without timing: " + ", ".join(unresolved))

    out = a.out or os.path.join(project, "claude", "scene-timing.md")
    write_timing(out, scenes, a.source)
    if fps:
        print(f"frames @ {fps} fps:")
        print("\n".join(frame_report(scenes, segments, fps)))
    if flags:
        print("flags:")
        print("\n".join("  " + f for f in flags))
    print(f"wrote {out}: {len(scenes)} rows {match_counts(scenes)}")


if __name__ == "__main__":
    main()
