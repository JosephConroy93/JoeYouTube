---
name: generate-voiceover
description: Generates a video's narration with ElevenLabs from the locked script — splits script.md into segments, writes the exact text sent per segment, calls the with-timestamps endpoint with the series voice, saves MP3 + character alignment, then normalises to −16 LUFS dual-mono 48 kHz WAV ready for align-scenes and place-scenes. Use right after the script is locked (WORKFLOW Step 5), before scene prompts.
---

# generate-voiceover

Invocation: `generate-voiceover <series>/<slug> [--segment NN] [--dry-run]`.
Layout and schemas: `.claude/conventions.md`. Everything below is executed
by `scripts/tts.ps1`; this file says what it does and what must be true.

## Inputs

- `claude/script.md` — locked (Mode 3 passed). Chapter headings or `---`
  lines mark segment boundaries.
- `series.md` → `voice.id`, `voice.model`, `voice.name`; `video.md` may
  override `voice`.
- `ELEVENLABS_API_KEY` in the user environment (conventions.md). Never in a file.

Stop if the script is not locked, the voice id is unset, or the key is
missing. The operator picks the voice from audition takes (below) or the
hosted ElevenLabs MCP; the id and settings are written to `series.md` or
`video.md`.

## What it does

1. **Segment** the script: split at chapter boundaries. With `voice.chapter_gap`
   set (seconds; `-ChapterGap`), every chapter is its own segment and its
   normalised WAV ends on that much silence (not the last), so each chapter
   card gets a breath before it on the timeline; otherwise merge chapters
   until a segment reaches ~4,500 characters (well inside the model's
   per-request limit; enough context for continuity). Strip markdown; chapter headings are
   spoken unless `chapter.spoken: no` (then the card carries them). Write each segment to
   `claude/voiceover-segments/<slug>_voice_NN.txt` — this file is the exact text
   sent, so a filename/content mismatch is detectable later.
2. **Generate** each segment with
   `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps`
   (`xi-api-key` header), `model_id` from config, `previous_text` /
   `next_text` set to the neighbouring segments for continuity, a fixed
   `seed` (stored in `video.md` `notes`) so a regenerated segment matches
   the others, `output_format` `mp3_44100_128`. Save the decoded audio to
   `voiceovers/<slug>_voice_NN.mp3` and the alignment (`characters`,
   `character_start_times_seconds`, `character_end_times_seconds`) to
   `claude/transcripts/<slug>_voice_NN.alignment.json` for `align-scenes --source api`,
   which keeps it only where it agrees with whisper; it is not a timing
   authority on its own (the `eleven_v3` alignment drifts).
3. **Normalise** each file: measure with `ebur128`, apply gain to
   **−16 LUFS integrated** with `alimiter` (`level=disabled`, otherwise it
   raises rather than tames), true peak ≤ −1.5 dBFS, export
   **48 kHz dual-mono stereo WAV** (`-ac 2` from the mono source) to
   `voiceovers/normalized/<slug>_voice_NN.wav`. Re-measure and print integrated
   LUFS, true peak, loudness range and **per-channel RMS** (both channels
   must be within 0.1 dB of each other). A large loudness-range collapse
   means over-compression: back the gain off.
4. Print each segment's duration and total runtime; append the voice used
   to `content/<series>/voice-register.md` and `video.md`.

`--segment NN` regenerates one segment only (same seed). Speed comes from
`voice.speed` in `video.md` or `series.md` unless `--speed` is given; `--tag
x` suffixes test takes (`<slug>_voice_NN_x`) so they never overwrite the real
segment. **Audition** (Step 5, before the full run): two to four tagged
takes of segment 1, varying one of `-VoiceId`, `-Model`, `-Stability`,
`-Style` or `-Speed` per take; the operator listens, and the winner's
values go into `video.md` as `voice.*` keys so the full run reads them.
`eleven_v3` ignores `speed` and rejects neighbouring-text context: set its
pace with `-Tempo` / `voice.tempo`, which stretches the audio at
normalisation (pitch kept) and writes `<label>.alignment.json` with times
divided by the tempo; the delivered alignment stays in
`<label>.alignment.raw.json`. `-SkipGenerate -Tempo x` re-times an existing
take without new credits. The raw MP3 is the source of record; only the normalised WAV goes
to the timeline. `--dry-run` writes
the segment texts and the request JSON to the scratch dir without calling
the API.

## Rules

- Generate and listen to **one segment first**; only then the rest.
- **After a script edit, re-voice only what changed**: write the segment texts
  with `--dry-run`, diff them against the previous run's copies, and pass
  `--segment NN` for each one that differs. A whole-script regeneration for a
  few edited lines burns the month's characters.
- Gain never changes timing; tempo does, which is why the timeline
  alignment is rewritten whenever `voice.tempo` is not 1.
- Never send the script in one request: segment boundaries are what let a
  single flubbed passage be regenerated cheaply.
- Cost: Creator tier ≈ £17/month for ~121k characters; a ~24k-character
  script ≈ £3.40. Check remaining credits before a full run.

## Not this skill's job

Choosing the voice (MCP + `series.md`), scene timing (`align-scenes`),
placing audio on the timeline (`place-scenes`).

## Status

🟡 Live-tested on one segment (generate, alignment, normalise). Full
multi-segment run and `align-scenes --source api` still to be exercised on the
next video. `scripts/voices.ps1` lists account voices, searches the shared
library and adds a library voice; `--skip-generate` re-normalises existing MP3s.
