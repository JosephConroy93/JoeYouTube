---
name: generate-hook
description: Builds a video's animated cold-open hook with Veo 3.1 image-to-video through the Gemini API — one 4–8 s clip per planned shot from an already-generated still, polled and downloaded by scripts/veo.ps1, then trimmed to the narration beats measured by align-scenes and prefixed with the 2 s black level card. Use at the end of Step 8, after every chapter's scenes are validated and align-scenes has run, before place-scenes.
---

# generate-hook

Invocation: `generate-hook <series>/<slug> [--model lite|standard|fast] [--dry-run] [--shot N]`.
Layout and credentials: `.claude/conventions.md`. Executed by `scripts/veo.ps1`.

## Inputs

- `claude/hook-plan.md` — written by `scene-prompter` Mode 2 with the first
  chapter; one row per shot:
  `| shot | scene_id | motion_prompt | duration_s | beat |`
  `scene_id` names a validated still in `scene-generation/`; `motion_prompt`
  describes only what moves (camera push, a figure walking, water, flame,
  cloth) and never restates the still's content; `duration_s` ∈ {4, 6, 8};
  `beat` is the verbatim script text the shot covers (used to cut it to the
  measured narration).
- Beat timings: `claude/scene-timing.md`. Runs at the end of Step 8, after
  every chapter is validated and `align-scenes` has run; never earlier.
- `GEMINI_API_KEY` in the user environment.

Stop if a `scene_id` has no canonical image or the plan has more than 8 shots.

## What it does

1. **Submit** one `predictLongRunning` request per shot to
   `models/<model>:predictLongRunning` with the still as `inlineData`, the
   motion prompt, `aspectRatio 16:9`, `durationSeconds`, `resolution` — then
   **poll** each operation until `done` and **download** the video URI to
   `hook/raw/shot-NN.mp4`. Requests run in parallel; poll every 15 s.
2. **Cut to beats**: trim each raw clip to the measured length of its beat (never stretch; if the beat is longer than the
   clip, hold the last frame and report it) into `hook/shot-NN.mp4`; the
   last shot is never trimmed to fit.
3. Report per shot: model, duration requested vs delivered, cost.

`--dry-run` writes the request JSON to the scratch dir and exits.
`--shot N` regenerates one shot.

## API facts the public docs get wrong (verified live)

- The image goes as `image: { bytesBase64Encoded, mimeType }`, not `inlineData` (400 otherwise).
- `durationSeconds` must be a JSON number, not a string.
- `personGeneration` must be `allow_adult`; `allow_all` is rejected.
- `negativePrompt` is rejected by `veo-3.1-lite`: any negative (no new characters, no text, background stays still) goes in the prompt text.
- Output is 24 fps H.264 MP4 with a generated audio track (1280×720 at 720p). **Always strip the audio** (`ffmpeg -i in.mp4 -map 0:v -c copy -an out.mp4`, lossless); set the video's timeline to **24 fps** (`video.md` `fps`) so hook clips need no frame-rate conversion; `place-scenes` upscales 720p to 1080p.

## Rules

- **Default: lite at 720p.** 720p allows 4, 6 or 8 s clips cut to the beat; 1080p forces 8 s and costs half as much again. A 720p lite clip upscaled to 1080p held up on Eggline's flat colour.
- Motion decays across the hook: real action and a tracking camera in
  shots 1–2, idle motion by the last shot. Cuts, never dissolves.
- The still is the truth: a clip whose character or setting drifts from its
  still fails; regenerate with a tighter motion prompt, never accept.
- **Motion-prompt discipline** (from the first live clips): confine every
  gesture to the joint that moves and say what stays put ("index finger taps
  the map twice; forearm stays on the table; other hand stays on the hip");
  let faces live: mouth movement and changing expressions are welcome (the
  operator prefers them) because the clip's audio is always stripped, but
  steer the emotion when it matters ("he mutters, frowning") or the model
  picks one, e.g. anger; ask for a
  "continuous, constant-speed push-in over the whole clip" or the push
  front-loads and stalls; never request an action the still already shows.
- Cost (Gemini list price, £): lite 720p ≈ £0.04/s, lite 1080p ≈ £0.06/s,
  fast 1080p ≈ £0.09/s, standard ≈ £0.31/s. A 7-shot hook of about 35 s on
  lite 720p ≈ £1.30.

## Not this skill's job

Writing hook copy (script), generating the stills (`generate-scenes`),
placing clips on the timeline (`place-scenes`), grading (`place-scenes` hook
grade note).

## Status

🟡 Exercised live on two 4 s 720p lite clips (gesture and walking; submit, poll, download, probe). Plan mode, beat trimming and the level card are UNTESTED until the Silk Road run.
