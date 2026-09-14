---
name: apply-fusion
description: Executes a video's `ken-burns-plan.md` in a running DaVinci Resolve Studio through the `davinci-resolve` MCP server — Baseline zoom as one Lua batch, Elevated pan/focal zoom per scene. No particle effects. Verifies with a window capture first and an ffmpeg-measured render last. Never imports media, builds timelines, or decides motion.
---

# apply-fusion

Invocation: `<series>/<slug>` — see `.claude/conventions.md`.

## Reads and writes

Under `content/<series>/<slug>/`:

- `claude/ken-burns-plan.md` — `| # | scene_id | dur | zoom | ease |
  transition | note |`. Coordinates are top-left fractions; **this skill
  does the Y-flip, `fusion_y = 1 − py`**.
- `series.md` / `video.md` — fps, `staging_path`.

Writes `<staging_path>\ken-burns-spec.json` (the batch input). Nothing else
in the project changes; the plan stays the record of what was applied.

## Prerequisites

- Resolve Studio running, the project open, the timeline `place-scenes`
  built current. `resolve_control get_page` must be non-null — if it is,
  `open_page edit` first. This skill never imports media or creates
  timelines.
- `resolve_control get_version` → `mcp.version` ≥ **v2.213.2**. Older:
  `git pull` in `tools/davinci-resolve-mcp`, reinstall the venv
  requirements, restart Claude Code.
- Keyframes go through `fusion_comp` only. `timeline_item` keyframe
  actions do not exist on the live object — never call them.
- `scripts/capture-window.ps1` is untested; prove any change to
  `scripts/apply_baseline.lua` on one scene of each motion type before a
  batch.

## Order of work

1. Parse the plan into Baseline (`In`/`Out`), Elevated (`Pan`, `Focal`),
   Static (skipped) and sweeps. Sweeps are the operator's (or
   `TimelineItem.AddTransition` on Resolve 21.1+, proven on one cut first)
   — not built here.
2. Prove on one scene: one-record spec through the Lua, capture, inspect.
3. Baseline batch. 4. Elevated, per scene. 5. Verify; ask before a full
   render.

## Every motion — one Lua batch

- Spec: `python .claude/skills/apply-fusion/scripts/plan_to_spec.py
  <series>/<slug> --fps N --out <staging>\ken-burns-spec.json [--only
  006,012]`. Records are flat: `{scene_id, frames, ease, size_start,
  size_end, center_x, center_y}` plus `pan, cx0, cy0, cx1, cy1` for a pan.
  `In` = 1.0 → 1.15, `Out` = 1.15 → 1.0 about the centre; `Focal` = pivot
  at the target, 1.0 → 1.2; `Pan` = static Size 1.2 with `Center`
  keyframed on an XYPath. Static rows are skipped.
- Copy the Lua into `script_plugin path Edit` with `SPEC_PATH` set to the
  spec (a file copy, not `install`, keeps the source out of the
  conversation), then `script_plugin execute`.
- Spline handles in `SetKeyFrames` are `{time, value}` **offsets from their
  key**; absolute points throw the curve past its end value. Read `Size`
  back mid-scene (`get_input` with `time`) on one In, one Out and one EO
  scene before trusting a batch.
- Camera travelling right = `Center.x` falling (the image slides left).
- `execute` returns `success: false` **and the script runs** —
  `fusion.RunScript` is non-blocking. Never retry on that flag; check
  `timeline_item_fusion get_comp_count` or the Console.
- Lua `print()` reaches only Workspace → Console. Read it with
  `scripts/capture-window.ps1 -Title Resolve` (the Console is its own
  top-level window titled just `Resolve`).
- The script wraps each item in `StartUndo`/`EndUndo`, never `comp:Lock()`
  (keyframes play live, vanish from the render).
- Lua `%b{}` against a whole JSON document matches the outer object and
  yields one phantom record; the script narrows to the `scenes` array and
  aborts if the parsed count is below `expected`. Keep `expected` honest.
- Budget ~1.5–3 s per clip; the UI looks busy throughout.
- The Dynamic Zoom panel is the manual fallback and has exactly three real
  presets: Out + L, In + EI, Out + EO — the plan is already limited to
  these.

## Elevated — per scene through the MCP (fallback)

The Lua batch handles Focal and Pan. Use this recipe to fix a single
scene by hand. Recipe: `timeline_item_fusion add_comp` (**once** per item; `get_comp_names`
first) → `fusion_comp add_tool Transform "KB"` → `connect` **MediaIn1 → KB
and KB → MediaOut1**. Missing the first connection keyframes fine and shows
"No frame available for MediaOut1". Batch independent calls in rounds (all
`add_comp`s, then all `add_tool`s, …).

- **Focal (x,y)**: `set_input Pivot [x, 1−y, 0]` static; leave `Center`
  at its default; keyframe `Size` at 0 and the last frame. `Pivot` is the
  point scaling happens around; `Center` moves the image and zooms toward
  whatever is already central.
- **Pan (x1,y1)→(x2,y2)**: static `Size` for headroom first, then
  `add_keyframe Center time 0 value [x1, 1−y1, 0] modifier "XYPath"`;
  second keyframe at the last frame, no modifier. `Path` and the default
  `BezierSpline` fail with `FUSION_ADD_MODIFIER_FAILED`. Horizontal pans
  keep `y1 = y2`; "no zoom" means no animated `Size`, the static headroom
  scale stays.
- **Headroom invariant**: `Size ≥ 1 + 2·max|Center − 0.5|` plus a margin,
  or a black bar sweeps in. The visible window is `1/Size` of the image —
  check the source has the resolution.
- Point3D values (`Center`, `Pivot`) are **bare arrays `[x, y, z]`**. A
  dict returns `success: true`, is never applied, and `get_input` keeps
  reporting the old value.
- `get_keyframes` on an `XYPath` input shows a spurious keyframe at
  `time: −1000000000` — an extrapolation anchor, ignore it.

## Verification

Per `conventions.md`: a `success` return or a readback is not proof.

0. **Readback of the whole batch.** Copy `scripts/report_kb.lua` into the
   Edit scripts folder with `REPORT_PATH` set, execute it, then
   `python .claude/skills/apply-fusion/scripts/check_kb.py --spec <spec> --report <tsv>`:
   every spec scene has its Transform with the right end values and no
   mid-scene overshoot, every Static item has none.
1. **Capture first, render last.** `scripts/capture-window.ps1 -OutPath
   <staging>\check.png` shows the Inspector values, keyframe diamonds and
   the `XYPath` line without rendering. **Multi-comp trap**: the Fusion GUI
   shows whichever comp a human last opened, not the API's, and ignores
   `timeline.set_current`. `fusion_comp` without `comp_name` targets the
   real comp; `load_comp` with an unknown name silently creates an empty
   one — `get_comp_names` first, cross-check with `get_tool_list`.
2. **Render ranges for confirmation** (`render set_settings` MarkIn /
   MarkOut → `add_job` → `start` → `verify_output`): the hook and first
   level card, a stretch with a pan, a focal and an SFX, and the last scene.
   Then
   ```
   python .claude/skills/apply-fusion/scripts/check_render.py <series>/<slug> --staging <dir> --fps N --render <mp4> --mark-in F --mark-out F --lufs <voice LUFS over the span>
   ```
   checks frame count, loudness and per-channel RMS, SSIM change on every
   moving scene (a normal move lands 0.4–0.75; ≥ 0.97 means nothing moved),
   card blackness, and each SFX's presence as the render-minus-voice
   residual. Then look at a few frames: a metric proves change, not the
   right change — a sliding black bar also scores as movement.
3. **Ask before a full render.** The operator says when; render ranges
   until then.

## Does not

- Import media, create or edit timelines — `place-scenes`.
- Decide motion — `plan-ken-burns`; the operator overrides on playback.
- Build particle, glow or other overlay effects.
- Build sweeps, captions or loudness.
- Read scene images into context; if the real composition contradicts the
  plan, trust the image.
