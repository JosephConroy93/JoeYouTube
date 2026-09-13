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
- fps and resolution from `video.md`, else `series.md` defaults.

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
4. **Pre-render every visual** to `<staging>/scenes/<scene_id>.mp4` at
   exactly its planned frame count: `ffmpeg -loop 1 -i <jpg> -frames:v <N>
   -r <fps> -vf crop=<16:9> -c:v libx264 -crf 18 -pix_fmt yuv420p -an`.
   `-frames:v`, never `-t` (rounds up a frame); `-an` always; crop to
   16:9, don't scale; upscale only sources below timeline resolution.
   Verify every output with `ffprobe -count_frames`. Run the batch in
   parallel, in the background.
5. **Hook clips.** Each row of `claude/hook-plan.md` names a `scene_id`;
   its clip `hook/shot-NN.mp4` **replaces that scene's still** at the same
   timeline position and duration (the plan is 1:1 with scenes; there is no
   separate hook script). Trim to the scene's measured duration; if the clip
   is shorter, hold its last frame. **Never trim the last hook clip to make a
   total fit.** (Older videos with a separate hook section: cut each clip at
   its own narration beat from the word timings.)
5b. **Level cards** (`rank-ladder (nine-level)` videos): for each level,
   render a 2 s black card with the level heading from `script.md` in small
   white hand-lettered capitals, centred (ffmpeg `drawtext`, exact text,
   project fps, frame-exact), and place it over the first two seconds of that
   level's first scene. `build_timeline.py` does not yet insert cards: add a
   `--cards` option (or place them by hand on V2) before the first edit of
   such a video.
   Conform each to the project fps with the same ffmpeg form (no `-loop`)
   into `<staging>/hook/`; any `start_frame`/`end_frame` given to the API
   is in **source** frames at the clip's native rate.
6. **Author the XML.**
   ```
   python .claude/skills/place-scenes/scripts/build_timeline.py <series>/<slug> --staging <dir> --fps N --out <xml> [--hook-order a.mp4,b.mp4] [--count-frames]
   ```
   Re-derives the frame plan from the timing file and staging inventory,
   aborts naming any clip whose frame count disagrees, requires the hook
   to fill frame 0 to the first scene exactly, writes one sequence (V1 =
   hook then scenes, one audio track per segment) and re-parses it to
   check video end = audio end = planned total.
7. **Import.** Bins first (`add_subfolder` + `set_current_folder`: Hook /
   Scenes / Voiceover), then `timeline.import_timeline_checked(path,
   sanitize_media: true)` — without it a syntax fault reports only
   "created no timeline". Check `media.linked == media.total`.
8. **Verify** (conventions rule): `timeline.get_current` end frame equals
   the plan; read back name/start/end/duration of the first item, each
   hook clip, the first body scene and the last item; the last audio item
   ends on the last video frame. Then **look**: a window capture (recipe
   in `apply-fusion`) or a render — a build with every duration wrong
   passes every position check. Every audio check reports integrated LUFS
   **and per-channel RMS**: a mono file on a stereo track plays left-only
   and integrated loudness cannot see it.

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

## Hook grade

Hook clips only; the body stays ungraded. Apply a CDL per hook item,
solving slope/offset/power from three points on the target curve, and
verify on a short render by measuring mean RGB and crushed-pixel % against
the reference — a readback of the CDL values is not verification.

## Not this skill's job

Motion and particles (`plan-ken-burns`, `apply-fusion`), the hook→body
transition, captions, SFX beds, final loudness, export, or judging whether
a measured duration reads well.
