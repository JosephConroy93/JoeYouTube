#!/usr/bin/env python
"""captions.py -- publish/captions.srt: the script's own words, timed by whisper on the timeline audio.

Usage:
    captions.py <series>/<slug> [--max-line 42] [--out PATH]

Reads   claude/voiceover-segments/<stem>.txt     the exact text voiced per segment (sorted = playback order)
        claude/transcripts/<stem>.json           whisper word timestamps of the timeline WAV (align.py)
        voiceovers/normalized/<stem>.wav         segment durations -> timeline offsets
Writes  publish/captions.srt

Each script word takes the time of the whisper word it lines up with (difflib over normalised
tokens); unmatched words are interpolated between matched neighbours. Cues are sentence pieces
of at most two lines of --max-line characters, split at commas when a sentence is too long.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from align import resolve_project, tokenize, words_from_whisper  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def seconds(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                                 "stream=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def timed_words(text, heard):
    raw = text.split()
    toks, owner = [], []
    for k, w in enumerate(raw):
        for t in tokenize(w):
            toks.append(t)
            owner.append(k)
    times = [None] * len(raw)
    sm = difflib.SequenceMatcher(None, toks, [h["norm"] for h in heard], autojunk=False)
    for b in sm.get_matching_blocks():
        for i in range(b.size):
            k, h = owner[b.a + i], heard[b.b + i]
            if times[k] is None:
                times[k] = [h["start"], h["end"]]
            else:
                times[k][1] = h["end"]
    known = [k for k, t in enumerate(times) if t]
    if not known:
        sys.exit("ABORT: no script word matched the transcript")
    for k in range(len(raw)):
        if times[k] is None:
            lo = max((j for j in known if j < k), default=None)
            hi = min((j for j in known if j > k), default=None)
            if lo is None:
                times[k] = [times[hi][0], times[hi][0]]
            elif hi is None:
                times[k] = [times[lo][1], times[lo][1]]
            else:
                a, b = times[lo][1], times[hi][0]
                f = (k - lo) / (hi - lo)
                times[k] = [a + (b - a) * f, a + (b - a) * f]
    return list(zip(raw, times))


def cues(words, max_line):
    """Group words into sentence pieces no longer than two lines."""
    out, cur = [], []
    limit = 2 * max_line
    for w, t in words:
        if cur and len(" ".join(x for x, _ in cur + [(w, t)])) > limit:
            cut = max((i for i, (x, _) in enumerate(cur) if x.endswith((",", ";", ":"))), default=len(cur) - 1)
            out.append(cur[:cut + 1])
            cur = cur[cut + 1:]
        cur.append((w, t))
        if w.endswith((".", "?", "!", '."', '?"', '!"', ".”")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def wrap(text, max_line):
    if len(text) <= max_line:
        return text
    words, best = text.split(), None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a + "\n" + b)
    return best[1]


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--max-line", type=int, default=42)
    ap.add_argument("--out")
    a = ap.parse_args()
    project = resolve_project(a.project)
    seg_dir = os.path.join(project, "claude", "voiceover-segments")
    stems = sorted(os.path.splitext(f)[0] for f in os.listdir(seg_dir) if f.endswith(".txt"))
    all_cues, offset = [], 0.0
    for stem in stems:
        wav = os.path.join(project, "voiceovers", "normalized", stem + ".wav")
        tj = os.path.join(project, "claude", "transcripts", stem + ".json")
        if not os.path.isfile(wav) or not os.path.isfile(tj):
            sys.exit(f"ABORT: {stem} needs {wav} and {tj} (run align.py first)")
        data = json.load(open(tj, encoding="utf-8"))
        if data.get("timed_audio") != f"voiceovers/normalized/{stem}.wav":
            sys.exit(f"ABORT: {tj} was not timed on the timeline WAV (run align.py)")
        text = open(os.path.join(seg_dir, stem + ".txt"), encoding="utf-8").read()
        text = re.sub(r"\[[^\]]*\]", " ", text)  # v3 audio tags are not spoken
        for c in cues(timed_words(text, words_from_whisper(data)), a.max_line):
            all_cues.append([offset + c[0][1][0], offset + c[-1][1][1], " ".join(w for w, _ in c)])
        offset += seconds(wav)
    for i, c in enumerate(all_cues):
        nxt = all_cues[i + 1][0] if i + 1 < len(all_cues) else c[1] + 2
        c[1] = min(max(c[1] + 0.3, c[0] + 1.0), nxt - 0.05)
    out = a.out or os.path.join(project, "publish", "captions.srt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for i, (s, e, t) in enumerate(all_cues, 1):
            f.write(f"{i}\n{stamp(s)} --> {stamp(e)}\n{wrap(t, a.max_line)}\n\n")
    print(f"wrote {out}: {len(all_cues)} cues, {offset:.1f} s of narration")


if __name__ == "__main__":
    main()
