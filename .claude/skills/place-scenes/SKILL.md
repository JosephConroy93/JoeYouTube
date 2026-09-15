---
name: place-scenes
description: Builds a video's first cut in DaVinci Resolve from `claude/scene-timing.md` — every scene image, hook clip and voiceover segment at its measured frame position. Pre-renders each visual to an exact-frame clip with ffmpeg, authors an FCP7 XML with `scripts/build_timeline.py` and imports it, because the scripting API cannot set a still's duration or trim a placed clip. Use after `align-scenes`, before `plan-ken-burns`.
---

# place-scenes

Invocation: `place-scenes <series>/<slug>`. Layout, schemas and the
verification rule: `.claude/conventions.md`.

## Inputs

- `claude/scene-timing.md` — complete; row count equals the manifest's.
- `scene-generation/<scene_id>.jpg` — one canonical image per scene.
- `voiceovers/normalized/*.wav` — −16 LUFS, 48 kHz, dual-mono stereo,
  levels baked in (the API cannot set `Volume`).
- `hook/*.mp4` — optional cold-open footage, native fps.
- Staging folder from `series.md` `staging_path` (`<slug>-<fps>`), local
  and outside any synced folder (`import_to_pool` can silently import
  nothing from synced paths), with `hook/`, `scenes/`, `voiceovers/`.
- fps and resolution from `video.md`, else `series.md` defaults; `grade`,
  `film_open` and `loudness` from `video.md` (all optional).

## Steps

1. **fps first, on a fresh project.** `timelineFrameRate` is settable only
   before any timeline exists; `timelinePlaybackFrameRate` is not settable
   from the API — the operator sets it in Project Settings; read it back.
   Match the hook footage's fps if there is any. Set resolution.
2. **Probe the audio.** Stream duration (`-select_streams a:0
   -show_entries stream=duration`), never the container's — containers
   pad. Offset of segment *i* = sum of durations before it. Copy the WAVs
   to `<staging>/voiceovers/`.
3. **Frame positions.** `frames(t) = round(t × fps)`;
   `start = frames(offset[segment] + start_seconds)`. A scene runs to the
   **next scene's start frame**, the last to `frames(total audio)` — its
   own `end_seconds` is where narration stops, not where the picture
   should. Difference rounded frame numbers, never round differences.
   Assert: no zero-length scene, each start equals the previous end, last
   end equals the audio end.
4. **Pre-render every visual** (steps 4, 5, 5b and 5c in one run):
   ```
   python .claude/skills/place-scenes/scripts/prerender.py <series>/<slug> --staging <dir> --fps N [--grade <lut> --grade-mix M] [--film-until <scene_id>] [--overlay-pos <scene_id>=x,y] [--jobs 8] [--only id,id]
   ```
   Copies the normalised WAVs to `<staging>/voiceovers/`, then writes
   `<staging>/scenes/<scene_id>.mp4` at exactly each scene's planned frame
   count (`-frames:v`, never `-t`; `-an`; stills cropped to 16:9, never
   downscaled) and `<staging>/cards/<scene_id>.mp4`, and frame-counts every
   output with `ffprobe -count_frames`. Run it in the background. Parallel
   runs can leave a clip short under load: rerun the ids it names with
   `--only` and fewer `--jobs`.
5. **Hook clips.** Each row of `claude/hook-plan.md` names a `scene_id`;
   its clip `hook/shot-NN.mp4` **replaces that scene's still** at the same
   timeline position and duration (the plan is 1:1 with scenes; there is no
   separate hook script). `prerender.py` scales it to the timeline size and
   trims it to the scene's frames, or holds its last frame when shorter; the
   staging `hook/` folder stays empty. **Never trim the last hook clip to make
   a total fit.**
5b. **Chapter cards**: after the scene clips, `prerender.py` renders a 2.2 s
   card per chapter in the thumbnail layout (`series.md` `thumbnail.*`):
   cream ground, `CHAPTER N` in the accent colour over the chapter name from
   the `## ` heading, and the scene the card lands on as a tilted outlined
   card on the right. The card grows, straightens and fills the frame; its
   last frame is that scene's frame under it, so the zoom is the cut into
   the chapter. The landing scene holds still for the card, then pushes in
   (baked; text-card rows stay still). `build_timeline.py --cards` places
   each card on V2 from the landing scene's first frame; a card may run past
   a short scene. It lands on the chapter's first scene, or on the first
   scene after `film_open` when the chapter opens inside it. A chapter made
   only of hook clips is the cold open and gets no card. Beat files split as
   `chapter-05a/05b` count as one chapter. Check one card's landing: its last
   frame against the scene clip's frame under it (SSIM ≥ 0.97).
5c. **Text-card words**: a `text-card` row's carrier image is generated
   blank; `prerender.py` draws its `overlay: "<word>"` (from the row's
   `notes`) in hand-lettered ink-dark type, centred, or at `--overlay-pos`
   when the blank patch sits off-centre. Check each overlay frame (a
   subagent) for the word sitting on the patch.
5d. **Spot SFX**: write `claude/sfx-plan.md` (schema in `conventions.md`)
   from the scenes that show a sounding action, searching
   `content/sfx/cinematic-bundle-metadata.tsv` descriptions, never
   filenames. Then
   ```
   python .claude/skills/place-scenes/scripts/sfx.py <series>/<slug> --staging <dir> --fps N
   ```
   cuts, fades and level-sets each clip to `<staging>/sfx/<scene_id>.wav`
   (48 kHz stereo) and measures integrated LUFS and per-channel RMS on every
   output; it aborts on a sound that runs past its scene (or past its
   `until` scene, for a sound held across scenes such as the film-open
   projector).
5e. **Grade and film open** (baked in step 4, never graded in Resolve):
   `--grade` mixes the `video.md` LUT over every hook clip and still at its
   mix, never over cards. `--film-until` gives every visual up to that scene
   the film look and a 2.39:1 letterbox; the next scene's bars slide off in
   0.6 s, after its card has landed when it carries one. Film-look clips
   are 1920×1080 with the bars baked in, so they stay static in
   `plan-ken-burns`. Check one frame each of a film hook clip, a
   film still, the bar-open scene at 0 / 0.25 / 1 s and a body still (a
   subagent) before the full run.
6. **Author the XML.**
   ```
   python .claude/skills/place-scenes/scripts/build_timeline.py <series>/<slug> --staging <dir> --fps N --out <xml> --count-frames [--cards] [--sfx] [--loudness <video.md loudness>]
   ```
   `--loudness` raises every audio clip's level by the same step from the
   voice files' −16 LUFS, so a render lands at the target with the SFX
   balance unchanged.
   Re-derives the frame plan from the timing file and staging inventory,
   aborts naming any clip whose frame count disagrees, writes one sequence
   (V1 = scenes, V2 = chapter cards, one audio track per voice segment, then
   SFX tracks packed without overlaps) and re-parses it to check video end
   = audio end = planned total.
7. **Import.** Bins first (`add_subfolder` + `set_current_folder`: Hook /
   Scenes / Voiceover), then `timeline.import_timeline_checked(path,
   sanitize_media: false, require_temp_path: false)`. On Windows the
   sanitizer reads `file://localhost/C:/...` as `/C:/...`, reports every clip
   missing and imports an empty timeline; if an import ever reports
   "created no timeline", run the sanitizer once only to read its syntax
   report. Check `media.linked == media.total`.
8. **Verify** (conventions rule): `timeline.get_current` end frame equals
   the plan; read back name/start/end/duration of the first item, each
   hook clip, the first body scene and the last item; the last audio item
   ends on the last video frame. Then **look**: a window capture (recipe
   in `apply-fusion`) or a render — a build with every duration wrong
   passes every position check. Every audio check reports integrated LUFS
   **and per-channel RMS**: a mono file on a stereo track plays left-only
   and integrated loudness cannot see it.

## Audio traps

- An XMEML import makes every audio track **mono, panned centre**: it plays
  3 dB under the file and takes channel 1 only. `build_timeline.py` writes an
  Audio Levels filter of +3 dB on each audio clip (clip volume is settable
  through the XML, not the API), and every WAV it places must be dual-mono
  (`sfx.py` folds SFX). A render of a narration range lands within about
  0.5 LU of the voice file over the same span; 3 LU under means the filter
  was lost.
- Integrated LUFS cannot see a missing channel: per-channel RMS on every
  audio check.

## Destructive-call rules

- `timeline.lift_range` applies to **every** track whatever `track_index`
  says; its `allow_partial_item_delete` deletes whole overlapping items.
  Never pass that flag once voiceover is placed.
- Replace an audio item by disabling it (`timeline_item.set_clip_enabled`)
  and placing the replacement on a **new track**. Never delete.
- `timeline.set_track_enable` can return success and do nothing: read back
  with `get_track_enabled`, fall back to per-item `set_clip_enabled`, then
  render and measure.
- A placed clip has no duration, trim or position setter: re-render and
  rebuild, never patch.
- Never drive Resolve's scripting API from an external Python process (it
  crashes); use the MCP server.

## Not this skill's job

Motion (`plan-ken-burns`, `apply-fusion`), the hook→body
transition, captions, ambience beds, export, or judging
whether a measured duration reads well.
