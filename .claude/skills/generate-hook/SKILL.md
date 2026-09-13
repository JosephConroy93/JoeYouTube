---
name: generate-hook
description: Builds a video's animated cold-open hook with Veo 3.1 image-to-video through the Gemini API — one 4–8 s clip per planned shot from an already-generated still, polled and downloaded by scripts/veo.ps1, then trimmed to the narration beats measured by align-scenes and prefixed with the 2 s black level card. Use after the hook stills are validated and the voiceover is aligned (WORKFLOW Step 9, before place-scenes).
---

# generate-hook

Invocation: `generate-hook <series>/<slug> [--model lite|standard|fast] [--dry-run] [--shot N]`.
Layout and credentials: `.claude/conventions.md`. Executed by `scripts/veo.ps1`.

## Inputs

- `claude/hook-plan.md` — one row per shot:
  `| shot | scene_id | motion_prompt | duration_s | beat |`
  `scene_id` names a validated still in `scene-generation/`; `motion_prompt`
  describes only what moves (camera push, a figure walking, water, flame,
  cloth) and never restates the still's content; `duration_s` ∈ {4, 6, 8};
  `beat` is the verbatim script text the shot covers (used to cut it to the
  measured narration).
- `claude/scene-timing.md` — beat timings, once `align-scenes` has run.
- `GEMINI_API_KEY` in the user environment.

Stop if a `scene_id` has no canonical image or the plan has more than 8 shots.

## What it does

1. **Submit** one `predictLongRunning` request per shot to
   `models/<model>:predictLongRunning` with the still as `inlineData`, the
   motion prompt, `aspectRatio 16:9`, `durationSeconds`, `resolution` — then
   **poll** each operation until `done` and **download** the video URI to
   `hook/raw/shot-NN.mp4`. Requests run in parallel; poll every 15 s.
2. **Cut to beats**: when `scene-timing.md` exists, trim each raw clip to the
   measured length of its beat (never stretch; if the beat is longer than the
   clip, hold the last frame and report it) into `hook/shot-NN.mp4`; the
   last shot is never trimmed to fit.
3. **Card**: render the 2 s black level card (`chapter.heading` from
   `series.md`, white small hand-lettered capitals, centred) as
   `hook/00-card.mp4` with ffmpeg `drawtext`.
4. Report per shot: model, duration requested vs delivered, cost.

`--dry-run` writes the request JSON to the scratch dir and exits.
`--shot N` regenerates one shot.

## API facts the public docs get wrong (verified live)

- The image goes as `image: { bytesBase64Encoded, mimeType }`, not `inlineData` (400 otherwise).
- `durationSeconds` must be a JSON number, not a string.
- `personGeneration` must be `allow_adult`; `allow_all` is rejected.
- Output is 24 fps H.264 MP4 (1280×720 at 720p); `place-scenes` re-renders it to the project fps, so nothing else needs to change.

## Rules

- **1080p needs 8 s clips.** For 4–6 s shots either generate 8 s at 1080p and
  trim, or generate 720p and upscale; default is 8 s at 1080p on `lite`
  (≈ £0.50 per shot) so the cut has headroom.
- Motion decays across the hook: real action and a tracking camera in
  shots 1–2, idle motion by the last shot. Cuts, never dissolves.
- The still is the truth: a clip whose character or setting drifts from its
  still fails; regenerate with a tighter motion prompt, never accept.
- Cost per shot (Gemini pricing, £): lite 720p ≈ £0.04/s, lite 1080p ≈
  £0.06/s, fast 1080p ≈ £0.09/s, standard 1080p ≈ £0.31/s. A 7-shot hook at
  8 s on lite 1080p ≈ £3.45.

## Not this skill's job

Writing hook copy (script), generating the stills (`generate-scenes`),
placing clips on the timeline (`place-scenes`), grading (`place-scenes` hook
grade note).

## Status

🟡 Exercised live on one 4 s 720p lite clip (submit, poll, download, probe). Plan mode, beat trimming and the level card are UNTESTED until the Silk Road run.
