---
name: align-scenes
description: Measures where every scene's `script_bookmark` falls in the real voiceover audio and writes `claude/scene-timing.md` (segment-relative start/end seconds per scene). Timing comes from the TTS character alignment when it exists, otherwise from whisper word timestamps; unmatched scenes are interpolated from their neighbours and flagged. Use once the voiceover exists and the scene manifest is written, before `place-scenes` and `plan-ken-burns`.
---

# align-scenes

Invocation: `align-scenes <series>/<slug> [--source whisper|api]`. Layout and
schemas: `.claude/conventions.md`. The work is done by `scripts/align.py`;
this file says what it reads, writes, and what must be true.

## Inputs

- `claude/scene-prompts.md` and the chapter files it names, in index
  order — `scene_id` and `script_bookmark` per row.
- `voiceovers/<slug>_voice_NN.mp3` — sorted filename order is playback order.
  A `claude/voiceover-segments/*.txt` with no matching audio is ignored
  and reported.
- Timing source, one of:
  - `api`: `claude/transcripts/<slug>_voice_NN.alignment.json` from
    `generate-voiceover` (`characters`, `character_start_times_seconds`,
    `character_end_times_seconds`), converted to word timestamps in the
    script. Missing files abort.
  - `whisper` (default): `claude/transcripts/<slug>_voice_NN.json`. A segment
    without one is transcribed by the `whisper` CLI with `--model tiny
    --word_timestamps True --output_format json` — only the timing
    matters, not the spelling. Run the script in the background; a
    segment can take minutes. Never use the MCP `media_analysis` wrapper:
    it has an internal 90 s cap and starts a fresh subprocess per call.

## Output

`claude/scene-timing.md`, one row per manifest scene, in manifest order:

`| scene_id | chapter | segment | start_seconds | end_seconds | match |`

Seconds are **segment-relative**; `place-scenes` adds the cumulative
offsets. `match` is `exact`, `fuzzy(NN%)`, `interpolated` or `api`.
`--out PATH` writes elsewhere (regression runs).

## Run

```
python .claude/skills/align-scenes/scripts/align.py <series>/<slug> [--source api] [--fps N] [--out PATH]
```

1. Parses every chapter row **by column boundary, never by quote pair**
   (bookmarks contain nested quotes). Rows parsed must equal rows present
   and the index's declared counts; a mismatch aborts naming the missing
   ids. Duplicate ids abort.
2. Normalises both sides: lowercase, surrounding punctuation stripped,
   empty tokens dropped, spelled-out numbers made digits
   (`three hundred` → `300`, `twenty six` → `26`).
3. Matches each bookmark: exact token sequence across every segment; if
   it occurs more than once, the single occurrence lying between its
   matched neighbours in playback order; else the best fixed-window fuzzy
   position at or above `--fuzzy-min` (0.7).
4. Splits each still-unmatched run equally between the nearest matched
   neighbours **in the same segment** (`interpolated`); a run at a
   segment's edge uses the segment bounds; neighbours in different
   segments abort.
5. Prints flags (no match, ambiguous match, interpolated span over 12 s)
   and a frame report at the project fps (`video.md` `fps`, else
   `series.md` `fps_default`): overlaps of more than one frame, each
   segment's last-word frame.

Read the flags. An unmatched bookmark usually means the manifest text
drifted from the script, or a proper noun was misheard as several tokens;
fix the bookmark or accept the interpolation knowingly.

## Must be true before `place-scenes`

- Row count equals the manifest's; every `segment` names a real audio file.
- No abort, no unreviewed flag.
- Each segment's audio matches its filename (spot-check a duration or a
  transcript line on any re-downloaded file).

## Known limits

- Fuzzy matching is same-length positional: an insertion or deletion in
  the transcript defeats it and the row falls to interpolation.
- Standalone small numbers (`seven`) are not always digits in whisper
  output.
- **Check the `api` alignment against the audio before trusting it:** its
  last character end must sit within ~5 s of the timeline WAV's duration.
  An `eleven_v3` segment returned an alignment 37 s shorter than its audio
  and cut scenes up to ~2 s off the narration; any segment that fails goes
  through `--source whisper` instead.

## Not this skill's job

Cumulative offsets and timeline placement (`place-scenes`); judging
whether a measured duration reads well on screen.
