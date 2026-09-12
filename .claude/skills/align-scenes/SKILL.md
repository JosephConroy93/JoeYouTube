---
name: align-scenes
description: Transcribes a project's per-segment voiceover MP3s directly via the `whisper` CLI (bypassing the davinci-resolve MCP server's `media_analysis.analyze_file` wrapper, which was confirmed 2026-09-11 to hit its own internal 90-second cap unreliably even with the model already downloaded) to get word-level timestamps, then matches each scene's exact `script_bookmark` text against those timestamps to produce a precise per-scene timing manifest — real measured durations instead of the estimated word-count/wpm banding scene-prompter currently plans against. Use once a video's full voiceover is generated (Step 7) and before Step 8 Ken Burns planning, so scene placement on the timeline is built from real audio.
---

# Align scenes — real per-scene timing from real audio

Every scene in a `scene-prompts/level-NN.md` chapter file already carries a
`script_bookmark` — the exact verbatim script text that scene covers. This
skill locates that exact text inside the real generated voiceover audio and
returns precise start/end timestamps, closing the gap between "how long we
*think* a scene should be on screen" (an estimate baked into
`scene-prompter.md`'s word-count bands, calibrated against a single voice
sample) and "how long the real narration for that scene actually takes."

**Origin**: built 2026-09-11 on Pharaoh's Servant after real production data
showed segment-to-segment pacing varying 152.5-164.2 wpm around a ~159.5 wpm
average — consistently under the 170.9wpm calibration figure — making the
estimated bands unreliable for Step 8 editing. Validated end-to-end on real
data before being written up here, per this project's standing "prove it
small before trusting it" rule: `134_not-kind-of-detail-written-down`'s
bookmark was located in its segment's transcript at 164.26s-166.38s via
plain word-sequence matching, with no manual scrubbing.

## Prerequisites

- `openai-whisper` installed (`pip install -U openai-whisper`) and on PATH
  (`whisper --help` to confirm). One-time; the model weights themselves
  also download on first use per model size.
- `content/<series>/<slug>/voiceovers/*.mp3` — one file per script segment,
  in the same order/naming as `claude/voiceover-segments/*.txt` (e.g.
  `01-hook-level1-2.mp3`, `02-level3-4.mp3`, ...). **Verify each file's
  actual content matches its filename before trusting it** — this project
  hit a real mislabeling incident (2026-09-11, logged in
  `content/watcher-pov/voice-register.md`) where a re-downloaded file got
  filed under the wrong segment name purely from request-order assumption.
  A quick spot-check (duration, or a `ffmpeg` frame/transcript skim) before
  transcribing a whole batch is cheap insurance against propagating that
  mistake into every scene's timing.
- The project's `claude/scene-prompts/level-NN.md` chapter files, fully
  written, each row's `script_bookmark` present and accurate.

## Why not the MCP server's `media_analysis` tool

It has a real `transcription` capability (`whisper_cli` backend) and was
tried first. **Confirmed unreliable for anything beyond the shortest
clips**: it enforces its own internal 90-second wall-clock cap per
transcription attempt, and — because each call appears to spin up a fresh
subprocess (fresh PyTorch/numba JIT warmup every time, not just once
per session) — even a ~154s clip succeeded only after a ~7-minute real
wall-clock wait, and a ~223s clip *failed* outright after 6m32s, timing out
repeatedly despite the model already being cached from the prior run.
Calling `whisper` directly in the background sidesteps the 90s cap
entirely and is the confirmed-working path. (The tool is also awkward for
audio-only input regardless — it gates on a visual `sampling_mode` choice
that doesn't apply to a file with no video frames, and defaults to
requesting vision analysis that then fails outright on audio.) Worth
re-testing the MCP path if a future server version changes this; not
worth fighting today.

## Step 1 — Transcribe each segment

One `whisper` call per segment MP3, **backgrounded** (a single segment can
take several minutes; never block on it, and never loop-poll — background
it and wait for the completion notification, same discipline this
project's Gemini Batch API jobs already use). Batch every pending segment
into **one** backgrounded shell command (a simple `for` loop over the
files) rather than one job per file, so there's a single completion signal
for the whole set instead of juggling N.

```bash
mkdir -p "content/<series>/<slug>/claude/transcripts"
for f in content/<series>/<slug>/voiceovers/*.mp3; do
  name=$(basename "$f" .mp3)
  whisper "$f" --model tiny --word_timestamps True \
    --output_format json \
    --output_dir "content/<series>/<slug>/claude/transcripts"
done
```

Run this with `run_in_background: true`. **Use the `tiny` model** — it was
the validated choice here, not for transcription accuracy (it visibly
mishears some words, e.g. "Djer" → "Jair" throughout the Pharaoh's Servant
test) but because only *timing* matters: we already know the correct text
from `script_bookmark`, we're not trusting Whisper's spelling, only where
in time each word falls. A larger model would be slower for no benefit
this skill actually uses. If a future use case needs the transcribed text
itself to be accurate (not just timed), reconsider the model size then.

Output: `claude/transcripts/<segment-name>.json`, one per segment, each
with a `segments[].words[]` array of `{word, start, end, probability}`.

## Step 2 — Match each scene's `script_bookmark` to a timestamp

For each scene row across every chapter file, locate its `script_bookmark`
text inside the transcripts. **Search across all segment transcripts, not
just the one you assume covers that scene** — this is deliberately
segmentation-agnostic (don't hard-code which segment covers which chapter;
that mapping is an artifact of how the VO happened to be chunked for a
given video, not a stable fact worth encoding here).

### ⚠️ Parse the row first, and reconcile the row count — a real silent-loss bug

**Found 2026-09-11, after this skill's first real run shipped a
`scene-timing.md` that silently omitted 3 scenes.** The bookmark field was
captured with a naive `"([^"]+)"`-style pattern, which terminates at the
first *inner* double quote. Pharaoh's Servant has exactly 3 rows in 198
whose `script_bookmark` contains nested quotes — `"ancient Egypt"`,
`"continued service"`, `"Egypt"` — and those are exactly the 3 rows that
went missing (`005_close-to-the-beginning`,
`123_continued-service-see-her-again`,
`168_word-egypt-means-something-different`). They were dropped at *parse*
time, so they never reached the matching stage, were never flagged, and
the output confidently claimed "195/195 scenes have real timing... 0 still
flagged" when the truth was 195/**198**. Three real scenes would have been
missing from the finished video.

Two rules, both cheap:

1. **Capture the bookmark by table column, not by quote pair.** Split the
   row on `|` and take the field positionally, then strip surrounding
   quotes — nested quotes inside the text are then harmless.
2. **Reconcile counts before writing anything**: rows parsed must equal
   rows present in the chapter files (`grep -c` the `scene_id` pattern).
   If they differ, stop and name the missing `scene_id`s. A count check is
   what turns this class of bug from silent into loud — the same reason
   `scene-prompter` Mode 4b gained its trailing-delimiter self-check.

Matching approach, proven on real data (Pharaoh's Servant: 182/195 *parsed*
scenes matched, 131 exact + 51 fuzzy, 13 interpolated — plus the 3 rows
above that never got parsed at all, see the warning):

1. Normalize: lowercase, strip surrounding punctuation from both the
   bookmark's words and the transcript's words. **Drop any token that
   normalizes to an empty string** (a standalone em-dash split out by
   whitespace tokenization is the common case — it isn't a real word and
   the transcript will never have a corresponding token for it; matching
   against it as if it were a word breaks every bookmark containing one).
2. **Normalize spelled-out numbers to digits in the bookmark tokens**
   (`"three hundred"` → `"300"`, `"a hundred"` → `"100"`, `"twenty-six"` →
   `"26"`) — Whisper's JSON output renders numbers as digits, not words,
   so a bookmark's spelled-out number will never exact-match without this.
   This alone fixed roughly half of Pharaoh's Servant's initial failures.
   Real residual gap: Whisper doesn't apply this consistently for every
   number (a small single-digit number word standing alone, e.g. "seven"
   in "at least seven young lions," isn't reliably converted) — worth
   extending this normalizer if the same pattern recurs on a future video,
   rather than treating the current one as complete.
3. Exact sliding-window match: slide the bookmark's word sequence across
   each segment's flattened word list; a full match gives the scene's
   `start` (first matched word's `start`) and `end` (last matched word's
   `end`) directly.
4. **If no exact match** (expected for any bookmark containing a name or
   word Whisper is liable to mishear — proper nouns especially), fall back
   to fuzzy matching: fixed-window, same-length positional comparison
   (what word how much of the target matches at each possible alignment
   in the segment), taking the best-scoring position above a threshold
   (0.7 worked well). Don't silently skip an unmatched scene — log it
   plainly (scene_id + bookmark text + which segment was expected) so a
   human can resolve it, the same "flag, don't guess" convention this
   project uses everywhere else (visual gaps, research gaps, QC failures).
5. A scene's bookmark should match in **exactly one** segment. If it
   matches in more than one (possible for short, generic bookmark text),
   flag it rather than silently picking one — ambiguous matches need a
   human call, not a guess.
6. **Known real limitation, not yet solved**: fixed-window fuzzy matching
   assumes the target and transcript have the same word *count* at the
   aligned position — it can't handle a single word getting split into
   multiple garbled tokens (Pharaoh's Servant: "Abydos" transcribed as
   three separate tokens, "a", "by", "-doss" — an insertion, not a
   substitution). These stay genuinely unmatched and need a real
   sequence-alignment approach (edit-distance-based, tolerating
   insertions/deletions, e.g. `difflib.SequenceMatcher` over the whole
   word list rather than a fixed window) to close — flagged as a next
   improvement rather than solved here, since the current fixed-window
   approach already accounts for most failures.

Reference implementation — the real algorithm run end-to-end on Pharaoh's
Servant's full 195-scene manifest (182 matched: 131 exact + 51 fuzzy, 13
flagged, all for the "Abydos"-class insertion case above):

```python
import json, re, glob

NUM_WORDS = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
    "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,
    "fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,
    "thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90}

def norm(s):
    return s.strip().lower().strip(".,;:!?\"'’—-")

def numeralize(tokens):
    # "three hundred" -> "300", "a hundred" -> "100", "twenty six" -> "26"
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in NUM_WORDS or t == "a":
            base = NUM_WORDS.get(t, 1 if t == "a" else None)
            j = i + 1
            if base is not None and j < len(tokens) and tokens[j] == "hundred":
                total, j = base * 100, j + 1
                if j < len(tokens) and tokens[j] in NUM_WORDS and NUM_WORDS[tokens[j]] < 100:
                    total += NUM_WORDS[tokens[j]]; j += 1
                out.append(str(total)); i = j; continue
            if t in ("twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety") \
               and j < len(tokens) and tokens[j] in NUM_WORDS and NUM_WORDS[tokens[j]] < 10:
                out.append(str(NUM_WORDS[t] + NUM_WORDS[tokens[j]])); i = j + 1; continue
        out.append(t); i += 1
    return out

def tokenize(text):
    return numeralize([w for w in (norm(t) for t in text.split()) if w])

def exact_match(words, target):
    n = len(target)
    for i in range(len(words) - n + 1):
        if all(words[i+j]["norm"] == target[j] for j in range(n)):
            return words[i]["start"], words[i+n-1]["end"], 1.0
    return None

def fuzzy_match(words, target, min_ratio=0.7):
    n = len(target)
    best, best_score = None, 0
    for i in range(len(words) - n + 1):
        ratio = sum(1 for j in range(n) if words[i+j]["norm"] == target[j]) / n
        if ratio > best_score:
            best_score, best = ratio, (words[i]["start"], words[i+n-1]["end"], ratio)
    return best if best and best_score >= min_ratio else None

# Load every segment's transcript, flattened to normalized {raw,norm,start,end} words.
# Parse every chapter's `| \`scene_id\` | "bookmark" |` rows.
# For each scene: try exact_match against every segment; if none, try fuzzy_match
# against every segment and keep the best; if still nothing, flag as unmatched.
```

## Step 2.5 — Interpolate whatever's still unmatched (Joe's fix, 2026-09-11)

Exact + fuzzy matching alone got Pharaoh's Servant to 182/195 (93%) — the
remaining 13 were all the "Abydos"-class insertion case (§Step 2.6 below),
genuinely unreachable by word-matching. **Rather than leave those as gaps,
interpolate them from their matched neighbours**: since scenes are already
in strict sequential order within each chapter (and chapters are processed
in file order — `level-01.md` before `level-02.md`, etc. — so simple list
position already reflects true video order, no need to parse or sort on
the numeric `scene_id` prefix), any run of consecutive unmatched scenes
sits between two *matched* scenes in the same list. Take the immediately
preceding matched scene's `end` and the immediately following matched
scene's `start` (**only if both are in the same segment** — interpolating
across a segment boundary isn't meaningful), and split that span
proportionally across the unmatched run (equal division is fine; word-count
weighting is a refinement, not required — it wasn't needed here). Mark
these rows `interpolated` in the output, distinct from `exact`/`fuzzy`, so
it's always visible which timings are measured versus inferred.

This closed Pharaoh's Servant to **195/195 (100%)** — including two cases
of *consecutive* unmatched scenes (a run of 2), which the proportional
split handles the same way as a lone gap.

**Edge case, not yet hit but worth knowing**: a run of unmatched scenes at
the very start or end of a segment (no matched neighbour on one side within
that segment) has no anchor to interpolate from on that side. Fall back to
the segment's own bounds (`0` / the segment's full duration) rather than
leaving it unmatched — didn't come up on this run, so treat as untested
until it does.

## Step 2.6 — What genuinely can't be closed this way

Fixed-window fuzzy matching (and by extension interpolation, which relies
on *some* matched anchor existing nearby) still can't rescue a chapter
where Whisper mishears something badly enough, and consistently enough
across every nearby scene, that there's no nearby anchor at all — not hit
on Pharaoh's Servant (every unmatched run had a matched neighbour close
by), but plausible on a name-dense chapter in a future video. If
interpolation ever produces a very wide span for a single scene (a
red flag the anchors were far apart), surface that rather than trusting it
silently — same "flag, don't guess" principle as everywhere else.

## Step 3 — Output: a per-scene timing manifest

Write `content/<series>/<slug>/claude/scene-timing.md` — one row per scene,
covering every chapter, not just the ones touched in a given invocation:

| scene_id | segment | start_seconds | end_seconds | match |
|---|---|---|---|---|
| `134_...` | `04-level7-8` | 164.26 | 166.38 | exact |

`start_seconds`/`end_seconds` are **segment-relative** — this skill does
not compute full-video cumulative offsets, since that depends on the final
segment concatenation order and any gaps/transitions inserted between them
at edit time (the hook's native snap-zoom transition, for one), which is
an editing decision, not a transcription fact. Whoever builds the actual
Resolve timeline (a future placement/stitching skill or a manual pass)
adds each segment's cumulative start offset on top of these
segment-relative numbers.

## What this skill does not do

- **Does not place or time clips on the Resolve timeline itself** — it
  only produces the timing data. Turning `scene-timing.md` into actual
  timeline edits is a separate, not-yet-built step (the natural next
  piece, once this data exists for real).
- **Does not judge whether a scene's *planned* duration is dramatically
  off from its *measured* one** — that's an editing/pacing decision for
  whoever's driving the session, not this skill's call.
- **Does not handle audio concatenation** — assumes the segment MP3s will
  be laid end-to-end in their existing order; if that order changes, this
  data must be regenerated or re-offset accordingly.
