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
- `scripts/capture-window.ps1` and `scripts/apply_baseline.lua` are
  **untested until a first run on one scene with a screenshot**. Do that
  before any batch.

## Order of work

1. Parse the plan into Baseline (`In`/`Out`), Elevated (`Pan`, `Focal`),
   Static (skipped) and sweeps. Sweeps are the operator's (or
   `TimelineItem.AddTransition` on Resolve 21.1+, proven on one cut first)
   — not built here.
2. Prove on one scene: one-record spec through the Lua, capture, inspect.
3. Baseline batch. 4. Elevated, per scene. 5. Verify; ask before a full
   render.

## Baseline zoom — one Lua batch

- Spec: `{"expected": N, "scenes": [{scene_id | item_index, size_start,
  size_end, center_x, center_y, ease, frames}]}`. `frames = round(dur ×
  fps)`; `center` = pivot (0.5, 0.5 for Baseline); `In` = 1.0 → 1.15,
  `Out` = 1.15 → 1.0 unless `note` asks for more. Flat records only.
- Set `SPEC_PATH` in the script (or `KB_SPEC_PATH` user env var), then
  `script_plugin install` (`language: lua`, `category: Edit`, `overwrite`)
  and `script_plugin execute`.
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

## Elevated — per scene through the MCP

Recipe: `timeline_item_fusion add_comp` (**once** per item; `get_comp_names`
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
- **Open**: which `Center` X direction reads as pan-right on screen is
  unverified. On the first pan, capture the viewer (or render and view the
  first and last frames) and record the mapping here.

## Verification

Per `conventions.md`: a `success` return or a readback is not proof.

1. **Capture first, render last.** `scripts/capture-window.ps1 -OutPath
   <staging>\check.png` shows the Inspector values, keyframe diamonds and
   the `XYPath` line without rendering. **Multi-comp trap**: the Fusion GUI
   shows whichever comp a human last opened, not the API's, and ignores
   `timeline.set_current`. `fusion_comp` without `comp_name` targets the
   real comp; `load_comp` with an unknown name silently creates an empty
   one — `get_comp_names` first, cross-check with `get_tool_list`.
2. **Render for confirmation** (`render add_job → start →
   verify_output`), extract frames (`ffmpeg -ss <t> -frames:v 1 -update 1
   out.jpg`), measure `ffmpeg -lavfi "ssim;[0:v][1:v]psnr"`. A normal move
   lands SSIM 0.5–0.75 / PSNR 15–20 dB; ≥ 0.999 / ≥ 70 dB means nothing
   changed. Then look: a metric proves change, not the right change — a
   sliding black bar also scores as movement.
3. **Ask before a full render.** Rendering costs time and has crashed
   Resolve; render a range, not speculatively.

## Does not

- Import media, create or edit timelines — `place-scenes`.
- Decide motion — `plan-ken-burns`; the operator overrides on playback.
- Build particle, glow or other overlay effects.
- Build sweeps, captions or loudness.
- Read scene images into context; if the real composition contradicts the
  plan, trust the image.
