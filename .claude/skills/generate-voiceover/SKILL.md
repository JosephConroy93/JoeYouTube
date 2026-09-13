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
missing. Do not pick a voice here; auditioning is done in the hosted
ElevenLabs MCP and the id is written to `series.md`.

## What it does

1. **Segment** the script: split at chapter boundaries, merging chapters
   until a segment reaches ~4,500 characters (well inside the model's
   per-request limit; enough context for continuity). Strip markdown, level
   callouts stay as spoken text. Write each segment to
   `claude/voiceover-segments/NN-<label>.txt` — this file is the exact text
   sent, so a filename/content mismatch is detectable later.
2. **Generate** each segment with
   `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps`
   (`xi-api-key` header), `model_id` from config, `previous_text` /
   `next_text` set to the neighbouring segments for continuity, a fixed
   `seed` (stored in `video.md` `notes`) so a regenerated segment matches
   the others, `output_format` `mp3_44100_128`. Save the decoded audio to
   `voiceovers/NN-<label>.mp3` and the alignment (`characters`,
   `character_start_times_seconds`, `character_end_times_seconds`) to
   `claude/transcripts/NN-<label>.alignment.json` for `align-scenes --source api`.
3. **Normalise** each file: measure with `ebur128`, apply gain to
   **−16 LUFS integrated** with `alimiter` (`level=disabled`, otherwise it
   raises rather than tames), true peak ≤ −1.5 dBFS, export
   **48 kHz dual-mono stereo WAV** (`-ac 2` from the mono source) to
   `voiceovers/normalized/NN-<label>.wav`. Re-measure and print integrated
   LUFS, true peak, loudness range and **per-channel RMS** (both channels
   must be within 0.1 dB of each other). A large loudness-range collapse
   means over-compression: back the gain off.
4. Print each segment's duration and total runtime; append the voice used
   to `content/<series>/voice-register.md` and `video.md`.

`--segment NN` regenerates one segment only (same seed). `--dry-run` writes
the segment texts and the request JSON to the scratch dir without calling
the API.

## Rules

- Generate and listen to **one segment first**; only then the rest.
- Gain never changes timing, so alignment stays valid after normalisation.
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
