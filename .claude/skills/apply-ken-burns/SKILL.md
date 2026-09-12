---
name: apply-ken-burns
description: Drives a running DaVinci Resolve Studio, via the davinci-resolve MCP server, to build the Ken Burns motion a ken-burns-plan.md describes — zoom, focal-point zoom, and pan, all confirmed working end-to-end as of 2026-09-08 (server v2.213.2+) after upstream fixed github.com/samuelgursky/davinci-resolve-mcp issue #196. Covers the exact recipe (per-scene Fusion comp + Transform tool), the Point3D input-format gotcha, the multi-comp GUI-sync trap, and a Windows screenshot-capture technique for fast iteration without rendering. Use once plan-ken-burns has produced a plan and the editor wants it applied automatically instead of by hand in the Inspector.
---

# Apply Ken Burns (Resolve MCP execution)

Takes `content/<series>/<slug>/claude/ken-burns-plan.md` (from `plan-ken-burns`)
and builds the motion in a running DaVinci Resolve project, via the
`davinci-resolve` MCP server — instead of the editor keyframing every scene
by hand. **Confirmed working end-to-end as of 2026-09-08**, on MCP server
**v2.213.2 or later** (must include the fix for
[issue #196](https://github.com/samuelgursky/davinci-resolve-mcp/issues/196) —
check `resolve_control(action="get_version")`'s `mcp.version`). Zoom,
focal-point zoom, and pan are all proven with real renders, verified by
extracting actual frames with `ffmpeg` and computing SSIM/PSNR — never by
trusting an API call alone. Full validation history, including a full day of
false starts before the fix landed, is archived in
`research/artifacts/archive-video-editing-resolve-mcp.md` (moved out of
`research/inventory.md` §2b on 2026-09-08 once the decision locked in —
that section now carries only a short current-state pointer) — worth
reading once if anything here seems to misbehave, since most
plausible-looking failure modes have already been hit and documented
there.

## Before anything else: check the server version

The render blocker this skill used to document (animated keyframes never
reaching a render) is fixed **only on server v2.213.2+**. If
`resolve_control(action="get_version")` reports an older `mcp.version`,
`cd tools/davinci-resolve-mcp && git pull origin main`, reinstall the venv's
requirements, and restart Claude Code before trusting anything below.

## What's proven, as of the v2.213.2 fix

| Capability | Status |
|---|---|
| Building a Fusion comp + Transform tool on a timeline item, scripted | ✅ Works |
| A **static** Fusion Transform value (`set_input`, no keyframe) | ✅ Renders correctly |
| **Animated zoom** (`Size` keyframed) | ✅ Renders correctly — confirmed via `ffmpeg` SSIM/PSNR on real renders, single-scene and 5-scene alternating tests |
| **Focal-point zoom** (zoom toward a specific off-center point, e.g. ending nearly full-frame on one object) | ✅ Works — set `Pivot` (not `Center`) to the target point as a static array value, then keyframe `Size` |
| **Pan** (`Center` keyframed over time) | ✅ Works — needs `modifier: "XYPath"` and the array value format (see below) |
| `timeline_item`'s Inspector-level keyframe actions (a *different*, unrelated tool) | ❌ Still genuinely broken — the method doesn't exist on the live object at all, crashes on every Resolve/Python combination tested. Always use `fusion_comp`, never `timeline_item` for keyframes. |
| Particle effects (Fusion `pEmitter`/`pRender` etc.) | ✅ Works, but out of scope here — see the sibling `apply-particles` skill (confirmed 2026-09-08 on Tomb Robber scene-01) |

## Prerequisites

- **MCP server**: `samuelgursky/davinci-resolve-mcp`, cloned at
  `tools/davinci-resolve-mcp/` in this repo, **v2.213.2+**. Configured as a
  Claude Code project-scoped MCP server via `.mcp.json` at the project root.
- **Python**: venv at `tools/davinci-resolve-mcp/venv/`. Version isn't load-bearing
  (3.13/3.12/3.11 all behave identically here) — 3.10–3.12 stays the documented-safe range.
- **Resolve version**: tested on Studio 19.1.3.7. Not believed to be version-locked.
- **License**: Studio (family key, $0, not version-locked).

## The recipe

1. **Confirm Resolve is running and has an active page.**
   `resolve_control(action="runtime_mode")` → if not running,
   `resolve_control(action="launch")` **without** `headless: true` — headless
   launch has crashed Resolve on this machine before. Then
   `resolve_control(action="get_page")` — if `null`, call
   `resolve_control(action="open_page", params={"page": "edit"})` first, or
   media import silently no-ops (`imported: 0`, no error).
2. **Import media from a plain local path, not this project's `content/`
   folders** — those live under OneDrive, and `media_storage.import_to_pool`
   intermittently returns `imported: 0` for OneDrive-synced files with no
   error. Copy to somewhere like `C:\Users\<user>\Videos\` first.
3. **Build the timeline** (`media_pool.create_timeline_from_clips`).
4. **Per scene**: `timeline_item_fusion(action="add_comp")` →
   `fusion_comp(action="add_tool", params={tool_type: "Transform", name: "KB<n>"})` →
   `fusion_comp(action="connect", ...)` **×2, both directions** —
   `MediaIn1 → KB<n>` **and** `KB<n> → MediaOut1`. Forgetting the first
   connection is an easy, silent mistake: the tool exists and takes keyframes
   fine, but the timeline preview shows "No frame available for MediaOut1"
   because the graph was never actually wired to the source.
5. **Zoom** (proven): keyframe `Size` —
   `fusion_comp(action="add_keyframe", params={tool_name, input_name: "Size", time: 0, value: 1.0})`,
   then again at the last frame with the end value (e.g. `1.15` for a subtle
   push-in, higher for a dramatic one).
6. **Focal-point zoom** (proven) — to end up nearly full-frame on a specific
   object rather than a generic center-zoom:
   - Set `Pivot` **statically** (no keyframe) to the object's position, in
     Fusion-normalized coordinates: `fusion_comp(action="set_input",
     params={tool_name, input_name: "Pivot", value: [x, y, 0]})`.
   - Leave `Center` at its default `[0.5, 0.5, 0]` — don't touch it for this.
     `Center` repositions where the image's own center anchors in the output
     canvas; `Pivot` is the point *within the image* that scaling happens
     around. Setting `Center` instead of `Pivot` was the first thing tried
     and produced a confusing wrong result (zoomed toward whatever was
     already near true center, since `Center` doesn't do what its name
     suggests here).
   - Keyframe `Size` as normal (step 5).
   - **Coordinate conversion**: Fusion's Y-axis is bottom-up (0=bottom,
     1=top), the opposite of typical image coordinates (0=top). If you know
     a point as `(px, py)` in normal top-down image-fraction coordinates
     (0–1, origin top-left), convert with `fusion_y = 1 - py`.
7. **Pan** (proven) — `Center` keyframed over time:
   - `fusion_comp(action="add_keyframe", params={tool_name, input_name: "Center", time: 0, value: [x1, y1, 0], modifier: "XYPath"})`
     — **`modifier` must be `"XYPath"`, not `"Path"` and not the default
     `"BezierSpline"`**. Both of those fail cleanly with
     `FUSION_ADD_MODIFIER_FAILED` on this Point3D-shaped input. `XYPath` is
     the one that actually attaches.
   - Second keyframe: same call, no `modifier` needed (already attached),
     `time` at the last frame, `value: [x2, y2, 0]`.
   - Usually paired with a static `Size` > 1.0 first (step 5's static form,
     e.g. `1.3`) so there's headroom to pan within — without it, panning at
     `Size: 1.0` runs off the edge of the source image.
   - `get_keyframes` on a `Center`/`XYPath` input may show a spurious extra
     keyframe at `time: -1000000000` matching the first real value — this is
     an internal spline-extrapolation anchor, not a real third keyframe. Ignore it.
   - **Joe's preferred pan style (2026-09-09): horizontal only, slow, across
     the full scene duration, "no zoom."** `plan-ken-burns` records this as
     `Pan: left→right, no zoom` (or `right→left`) in the plan's `Note`
     column when it's this specific style, not just any Pan. "No zoom" means
     no *animated* `Size` change during the clip — the static `Size > 1.0`
     headroom scale-up above is still required (and fine) since it doesn't
     change over time and isn't perceived as a zoom, only as the necessary
     room for the pan to move within. Keep `y1 == y2` (purely horizontal —
     no vertical drift) unless the plan explicitly calls for a diagonal.
     **Not yet empirically confirmed which `Center` X direction (increasing
     vs. decreasing) reads as "camera pans right" on screen** — `Center`
     is already documented above as non-intuitive (see the focal-point-zoom
     warning). The first time this style is actually executed, verify the
     visual direction with the screenshot/Inspector check below (or a real
     render) before trusting it, and update this note with the confirmed
     mapping so it doesn't need re-deriving next time.
7b. **⚠️ PAN HEADROOM — the invariant that stops black edges (found the
   hard way 2026-09-11, after shipping six broken pans).** A pan is a crop
   window sliding across the image; **the window must stay inside the image
   for the whole move**, or empty canvas shows as a black bar sweeping in
   from one side. The condition is:

   > **`Size ≥ 1 + 2 × max|Center − 0.5|`** (plus a little margin)

   Worked example of getting it wrong: `Center` keyframed `0.18 → 0.82` is
   a deviation of ±0.32, so it needs `Size ≥ 1.64`. It shipped at
   **`Size 1.25`**, which exposed roughly 17% of the frame as black on every
   one of six pan scenes. Fixed by narrowing to `0.25 → 0.75` (±0.25) at
   **`Size 1.6`** — verified clean at both extremes of the sweep.

   Bounds are free to vary per scene: a wide sweep needs a bigger `Size`
   (tighter crop, more push-in), a gentle drift can stay wide at a lower
   `Size`. Only the inequality is fixed. At `Size 1.6` the visible window is
   1/1.6 ≈ 62% of the image width, so check the source has resolution to
   spare — these 2752px-wide scenes upscale only ~1.1×, which is fine.

   **And look at the render, don't just measure it.** The broken pans passed
   an SSIM/PSNR check (0.148 / 9.68dB) that was read as "large real
   movement" — the number was real, but part of that difference *was the
   black bar sliding in*. A metric confirms something changed, not that the
   right thing changed. Extract the first and last frames of any pan and
   look at the edges.

8. **The Point3D value-format gotcha — applies to `Center`, `Pivot`, and any
   similar multi-component input, for both `set_input` and `add_keyframe`:**
   **the value must be a plain JSON array `[x, y, z]`.** An object/dict —
   whether `{"X": x, "Y": y}` or even `{"1": x, "2": y, "3": z}` matching
   the shape `get_input` itself returns — is silently accepted (`success:
   true`) but **never actually applied**. This produced a confusing false
   negative: the call reports success, `get_input` immediately after even
   *keeps reporting the old default value* (not the one you "set"), and any
   render or GUI check shows no change at all. Always use a bare array.
9. **Verification — two tiers, use both depending on what you need:**
   - **Fast iteration, no render needed**: capture the Resolve window
     directly (see "Windows screenshot capture" below) and read the
     Inspector panel for the tool — it shows live numeric values (`Center
     X/Y`, `Pivot X/Y`, `Size`) and, for animated params, a small diamond
     marker. The on-screen viewer also draws the actual pivot/center
     handles and the `XYPath` trajectory line directly over the image, which
     confirms geometry at a glance. This is faster and just as trustworthy
     as a render **once you're looking at the right comp** — see the
     multi-comp trap below, which is the main way this check goes wrong.
   - **Final confirmation, or anything render-pipeline-specific**: an actual
     render via the `render` tool (`add_job` → `start` → `verify_output`),
     then extract real frames with `ffmpeg` (`ffmpeg -ss <t> -frames:v 1
     -update 1 out.jpg`) and compare — ideally with `ffmpeg -lavfi
     "ssim;[0:v][1:v]psnr"` for a number, not just eyeballing. Two frames
     from a real animated scene should land around SSIM 0.5–0.75 / PSNR
     15–20dB for a normal Ken Burns move; SSIM ≥0.999 / PSNR ≥70dB means
     nothing actually changed (pure re-encoding noise) despite what any API
     call claimed. **Rendering has real cost and, once, triggered an actual
     Resolve crash** — don't render speculatively; use the screenshot check
     first and reserve renders for real confirmation, and always ask before
     rendering if you're not sure the user wants one right now.

## Applying at real scale (198 scenes) — added 2026-09-11, Pharaoh's Servant

The per-scene recipe above is ~6 MCP calls. At 178 motion scenes that is
~1,100 round-trips, which is not practical in a conversation. What actually
worked, as a **division of labour**:

- **Baseline zoom tier → one Lua script run inside Fusion.** Install via
  `script_plugin(action="install", language="lua", category="Edit")` and
  loop over `tl:GetItemListInTrack("video", 1)`, building
  `MediaIn1 → KB(Transform) → MediaOut1` and attaching a spline with
  `xf.Size = comp:BezierSpline()` then
  `sp:SetKeyFrames({[0]={s0},[last]={s1}})`. Wrap each scene in
  `comp:StartUndo()`/`comp:EndUndo(true)` — **not** `comp:Lock()`, which is
  the documented silent-render-failure trap. Applied 178 scenes,
  `failed=0`, in about 5 minutes.
- **Elevated Pan/Focal → the MCP recipe above, one scene at a time.** Only
  10 scenes, ~7 calls each, and it uses the proven `XYPath` modifier and
  `Pivot` array handling rather than re-deriving them in Lua. Batch the
  independent calls in parallel (10 `add_comp`s in one message, then 10
  `add_tool`s, and so on) — about 7 rounds total.

**Three real gotchas found doing this:**

1. **`script_plugin(action="execute")` returns `success: false` but the
   script DOES run.** Fusion's `RunScript` is non-blocking, so the call
   returns in ~5ms before anything has happened, and the server reports
   that as failure. Don't retry on the strength of that flag — check the
   actual state (`timeline_item_fusion get_comp_count`) or the Console.
2. **Lua stdout is not capturable by the MCP** — `print()` only reaches
   Workspace → Console → Lua tab. To read progress unattended, capture the
   Console *window* with the PowerShell `PrintWindow` technique below; it
   is a separate top-level window (enumerate windows for the Resolve PID
   and take the one titled just `Resolve`, not the main
   `DaVinci Resolve Studio - <project>` window).
3. **Do not parse JSON in Lua with `s:gmatch("%b{}")` against a whole
   document** — the outer `{...}` matches first, yielding exactly ONE
   bogus record built from the first value of each key. This silently
   produced `spec loaded: 1 scenes` and applied nothing. Narrow to the
   array first (`raw:match('"scenes"%s*:%s*(%b[])')`), then match siblings
   inside it, and add a sanity guard that aborts if the parsed count is
   far below what is expected — a half-applied motion pass across a video
   is much worse than a clean abort.

`AddFusionComp` costs roughly 1.2–2.7s per clip, so budget ~5 minutes per
200 scenes and expect the UI to look busy throughout.

## The multi-comp trap — read this before trusting any GUI screenshot

A single timeline item can end up with **more than one Fusion comp**
(`timeline_item_fusion(action="get_comp_names")` can return e.g.
`["Composition 1", "Composition 2"]`). The Fusion page's GUI does **not**
reliably show the one the API has been building — it shows whichever comp a
human last opened there, and does not follow `timeline.set_current` at all
switching the "current timeline" via the API leaves the Fusion page showing
whatever it was already showing.

- `fusion_comp` actions with **no `comp_name`** target the real comp the
  recipe above builds (confirmed: matches an explicit `comp_name` naming
  whichever one turns out to hold the actual tools). Trust this over
  guessing which named comp is "the" one.
- `timeline_item_fusion(action="load_comp", params={name: ...})` switches
  what the GUI displays. **If the name doesn't already exist, it appears to
  silently create a new empty comp under that name** rather than erroring —
  don't guess a name; call `get_comp_names` first, and if unsure which
  named comp is the real one, cross-check with `fusion_comp(action=
  "get_tool_list")` (no `comp_name`) vs. the same call **with** each
  candidate `comp_name` — whichever matches is the real one to `load_comp`.
- Prefer *not* creating a second comp at all: only call
  `timeline_item_fusion(action="add_comp")` once per timeline item, and if
  a screenshot check seems to show the wrong (empty) comp, suspect this
  trap before suspecting the recipe itself.

## Windows screenshot capture — for fast iteration without rendering

Reusable beyond this skill for any GUI-verification need. Requires no
installs — pure .NET via PowerShell:

```powershell
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Capture {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
# Find the window handle first: Get-Process | Where-Object { $_.ProcessName -like "*Resolve*" } | Select MainWindowHandle
$hwnd = [IntPtr]<handle>
$rect = New-Object Win32Capture+RECT
[Win32Capture]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$width = $rect.Right - $rect.Left; $height = $rect.Bottom - $rect.Top
$bmp = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $graphics.GetHdc()
[Win32Capture]::PrintWindow($hwnd, $hdc, 2) | Out-Null   # flag 2 = PW_RENDERFULLCONTENT
$graphics.ReleaseHdc($hdc)
$bmp.Save("<path>.png", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bmp.Dispose()
```

- **The `PW_RENDERFULLCONTENT` flag (`2`) is required** — plain `PrintWindow`
  (flag `0`) often returns black/blank for GPU-accelerated apps like Resolve.
- Captures **only that window**, at full resolution, regardless of what's on
  top of it or whether it's focused — unlike a full-screen capture (`Graphics.CopyFromScreen`
  + `Screen.PrimaryScreen.Bounds`), which grabs the whole desktop including
  unrelated windows (chat, browser tabs, etc.) and requires the target to be
  visible/in front.
- Re-find the window handle each session (`Get-Process ... MainWindowHandle`)
  — it changes across Resolve restarts.

## Workaround tried and rejected — don't re-attempt

Before the real fix was found, stepping through many small **static**
values (proven to render even when animation wasn't) was tried as a
workaround: 10 separate 12-frame clips (0.5s each), each a static `Size`
step. Mechanically worked, but the motion was **visibly stepped/chunky** —
rejected after watching it back. Now moot with animation actually working,
but don't resurrect this approach; use real keyframes.

## What this skill does NOT do

- Does not decide the motion itself — that's `plan-ken-burns`'s job. This
  skill only executes an already-approved `ken-burns-plan.md`.
- Does not cover particle effects (dust, embers, sparks) — see the
  sibling `apply-particles` skill.
- Does not touch captions, loudness, transitions, or anything else in
  Step 8's broader scope.
- Does not view the actual generated scene images — same caveat as
  `plan-ken-burns`: if a scene's real composition differs from what the
  plan assumed, trust the image.
