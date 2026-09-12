---
name: apply-particles
description: Drives a running DaVinci Resolve Studio, via the davinci-resolve MCP server, to build ambient environmental particle effects (dust drifting through a doorway, embers off a fire/torch, etc.) directly in a scene's Fusion comp — raw-primitive pEmitter → pRender → Merge (Screen) build, confirmed working end-to-end 2026-09-08 on Tomb Robber scene-01 (a doorway light-beam dust effect). Covers the real recipe, the "small near-point source + AngleVariance" cone principle, two confirmed sign-flip traps, and a couple of Fusion input-name dead-ends found the hard way. Use when a scene calls for atmospheric particles beyond what plain Ken Burns motion (see the sibling apply-ken-burns skill) can do — values are scene-specific and need re-tuning each time, but the build pattern transfers.
---

# Apply Particles (Resolve MCP execution)

Builds an ambient Fusion particle effect (dust, embers, sparks — anything
reading as small drifting motes catching light) on a scene's timeline item,
via the `davinci-resolve` MCP server's `fusion_comp` actions. **Confirmed
working end-to-end 2026-09-08**, built and tuned live against Joe's own
Resolve GUI on Tomb Robber scene-01 (`content/watcher-pov/
tomb-robber/scene-generation/001_wake-up-ill.jpg` — dust drifting
in through a doorway light beam). Full 14-step iteration log, including every dead end,
is archived in `research/artifacts/archive-video-editing-resolve-mcp.md`
under "Particle effects — live iteration log" (moved out of
`research/inventory.md` §2b on 2026-09-08 once the decision locked in —
that section now carries only a short current-state pointer) — worth
reading once if a result looks wrong, most plausible failure modes have
already been hit there.

**This is a starting recipe, not a fixed effect.** Joe's own framing after
locking the first one in: *"for any environmental lighting particle
effects, doorways, (a natural fire/torch / other example) this setting is
nice, obviously the shape/direction etc may be dynamic per scene but great
start."* The numeric values below are this-scene-specific (doorway,
top-left light source) — re-derive position/angle/region size per scene,
but the build order, the cone principle, and the sign-flip traps all
transfer directly.

## Prerequisites

Same as `apply-ken-burns`: `davinci-resolve` MCP server (v2.213.2+),
Resolve Studio running with an active page, target clip already on the
timeline. Read that skill's "Prerequisites" and "Before anything else:
check the server version" sections if this is the first Resolve MCP work
of the session — not repeated here.

## Precondition: the backdrop must be dark enough (added 2026-09-12)

**Check this BEFORE building anything. It is the difference between an
effect and wasted render time.**

This recipe merges pale particles over the plate with **Screen**, which can
only *brighten*. Over a backdrop already near white it has nowhere to go, and
the particles are not faint — they are **mathematically invisible**. No amount
of Size, Number or Alpha tuning rescues it; the blend mode is the ceiling.

Measure the **mean luma of the particle's travel path** — not the emitter
point, the path. Particles drift (`Angle` × `Velocity` × `Lifespan`), so an
emitter sitting on a dark beam whose particles immediately drift into blown
sky fails just as hard as one starting bright:

```bash
ffmpeg -v error -i "<scene>.jpg" -vf "crop=700:460:<x-60>:<y-60>,scale=1:1,format=gray" -f rawvideo - | od -An -tu1
```

where `x,y` is the emitter in pixels and the crop box extends along the drift
direction. Divide the byte by 255.

| path luma | verdict |
|---|---|
| **< 0.40** | good — particles read clearly |
| 0.40 – 0.50 | marginal, verify by render before trusting |
| **> 0.50** | reject the scene, do not build |

**Measured on Pharaoh's Servant (2026-09-11/12), five FX scenes:**

| scene | path luma | outcome |
|---|---|---|
| 066 | 0.37 | ✓ clear, well-formed dust motes |
| 186 | dark (torch-lit) | ✓ visible haze |
| 030 | 0.47 | ✗ invisible |
| 043 | 0.74 | ✗ invisible |
| 161 | 0.81 | ✗ invisible (emitter on dark wood, drift into sky) |

Three of five were built with **byte-identical emitter settings** to the one
that worked, and three of five were invisible. The only variable was backdrop
luminance. Joe spotted 030 himself on first watch-through; 030 and 043 were
the two FX scenes never render-verified, which is exactly how they survived
to a finished cut.

A useful cross-check: the scenes that worked (066, 186) were the **two darkest
images in the entire 198-scene video** (whole-image luma 0.21 and 0.24). If a
candidate is not near the top of a darkness ranking of the video's own scenes,
be suspicious of it. Rank cheaply with `scale=1:1,format=gray` over every
scene image before choosing candidates at all.

**If no scene clears the gate, say so and build nothing.** An invisible
particle sim still costs full Fusion render time on every frame.

## The recipe

1. **Build from raw primitives, not `group_settings_load`.** If working
   from an old hand-built `.setting` file as a style reference,
   `group_settings_load` needs a **pre-existing named `GroupOperator`** in
   the comp to load values into — it does not insert a fresh group from a
   `.setting` file. Read the values straight out of the `.setting` file
   (plain XML/Lua-ish text, human-readable) and rebuild with `add_tool`/
   `set_input` instead. Old `.setting` files are a reasonable **starting
   reference**, not a spec to match exactly — treat their values the way
   Joe put it: *"I'm not saying they are the gold standard, they just
   sort of worked."*
2. **The tool chain**: `add_tool` three tools — a `pEmitter` (the particle
   source), a `pRender` (rasterizes particles to an image), and a `Merge`
   (blend mode **`Screen`**) — then `connect` them: `pEmitter → pRender`,
   and `MediaIn1 + pRender → Merge → MediaOut1` (background = the original
   plate, foreground = the particle render, Screen blend so black stays
   transparent and bright particles add light).
3. **Call `fusion_comp(action="auto_arrange")` immediately after adding all
   three tools.** Tools added via the API all land at the same default
   canvas position and visually stack/overlap in the node graph — this
   looked like an accidental Fusion "Group" the first time, and individual
   nodes couldn't be clicked into. Not a real group; `auto_arrange` spreads
   everything into a row. **Do this after every multi-tool build**, not
   just when it visibly breaks.
4. **Style — start from `ParticleStyleBlob`, not `ParticleStyleLine`, for
   ambient dust/embers.** `ParticleStyleLine` draws direction-dependent
   streaks whose length scales with `Size`/velocity — plausible for
   rain/motion-heavy effects, but reads as "shooting stars" for soft
   ambient dust (confirmed by direct comparison, iteration #3-4 in the
   log). `ParticleStyleBlob` draws rounder, non-directional marks — the
   right starting point for dust/embers/fireflies.
5. **`ParticleStyle.Size` has no usable default for either style.**
   Fusion's own default (`0.1`) was completely invisible in testing —
   don't assume a source `.setting` file's implicit default carries over
   to a new scene or resolution; tune it visibly every time. `0.4` worked
   for this scene's resolution/framing; treat that as a starting guess,
   not a constant.
6. **The cone principle — this is the part most likely to go wrong first
   try.** A convincing directional spread (particles emanating from a
   point and fanning out as they travel, e.g. "dust pouring through a
   doorway") comes from:
   - A **small, near-point source region**, positioned at the effect's
     **true physical origin** (e.g. the top of the doorway, where the
     light first crosses into frame) — not a region shaped or sized to
     match the final spread.
   - A nonzero **`AngleVariance`** (this input defaults to `0`), which
     fans individual particles' travel directions out around the central
     `Angle`. **Without this, every particle travels in an identical
     direction regardless of where in the region it spawned** — a tall or
     wide source region with `AngleVariance=0` just produces a flat
     sideways-drifting band, not a cone, no matter how the region is
     shaped or positioned. This was the actual root cause the one time
     the effect looked wrong despite a "correctly" tilted/shaped region
     (iteration #11 in the log: *"too high, particles in the unwanted
     zone. not coning down"*) — the fix was shrinking the region back to
     near-point-sized and adding `AngleVariance` (`15` worked here), not
     further reshaping the region.
   - `Angle` sets the central/average direction; `Velocity` × `Lifespan`
     sets how far particles travel before dying — both need real values
     for a cone to read as "coming from" the source rather than sitting
     static near it.
7. **Region rotation — use `RectRgn.Rotate.Z`, not `RectRgn.Angle` or
   `RectRgn.Rotation`.** Both of the plausibly-named inputs exist in the
   tool's input list but **silently no-op**: `set_input` reports
   `success: true`, and `get_input` immediately after still returns
   null/unchanged. The real, working input was only found via
   `probe_fusion_tool(timeline_item, tool_name, include_inputs: true)`'s
   full input dump — **when a plausible input name doesn't visibly do
   anything, probe the tool's full input list before assuming the effect
   isn't supported at all.** Note the probe returns every real input
   `id`/name but not current values (those still need `get_input` per
   field).
8. **Sign convention — try negative first, on two separate inputs.** Both
   `RectRgn.Rotate.Z` (tilting the source region) and `pEmitter.Angle`
   (the particles' travel direction) needed the **opposite sign** from the
   first intuitive guess to match the visible direction in the scene (a
   positive value on either rotated/drifted the wrong way, confirmed
   wrong by Joe watching the live viewer both times). Not confirmed as a
   universal Fusion rule, but worth trying negative first on the next
   scene rather than re-discovering this from scratch.
9. **Glow, if reusing one alongside particles**: a single `Glow` tool,
   `Filter: "Fast Gaussian"`. An old `.setting` file's `Blend` value may be
   tuned for a different source image's brightness — this scene's source
   already had a bright built-in light source, so the old file's
   `Blend=0.2` blew the doorway out; cut it ~30% (`0.14`) on Joe's ask,
   confirmed "much better." Tune per scene, don't copy the old value
   blind.
10. **All particle inputs here are plain scalars/strings via `set_input`**
    (`Style`, `Region`, `Number`, `Lifespan`, `Velocity`/
    `VelocityVariance`, `Angle`/`AngleVariance`, `ParticleStyle.Size`,
    `ParticleStyle.ColorControls`/`Red`/`Green`/`Blue`/`Alpha`,
    `RectRgn.Width`/`Height`/`Translate.X`/`Translate.Y`/`Rotate.Z`) — none
    of them hit the Point3D array-format gotcha documented in
    `apply-ken-burns` (that's specific to `Center`/`Pivot`-shaped inputs,
    not these).

## Numbers that actually transfer (added 2026-09-11, Pharaoh's Servant — 5 scenes)

The Tomb Robber reference values below **do not transfer**, and the first
attempt using them produced a full-frame blizzard of specks settling on a
character's face — closer to video static than dust. Three rules came out
of fixing it, and these are the parts worth carrying forward:

1. **Travel budget: `Velocity × Lifespan` ≈ total distance travelled, in
   normalized units where the frame is ~1 unit wide.** The reference's
   `0.025 × 200 = 5.0` sends every particle across the frame five times
   over, which is why it reads as a blizzard rather than ambient dust.
   **For ambient dust keep the product ≤ ~0.4.** Confirmed good here:
   `Velocity 0.004, Lifespan 110` (= 0.44) for dust; `Velocity 0.003,
   Lifespan 60` (= 0.18) for embers, which should linger near their source.
2. **Coordinate mapping, confirmed empirically**: for a target at top-down
   image fraction `(x, y)`,
   `RectRgn.Translate.X = x - 0.5` and `RectRgn.Translate.Y = 0.5 - y`.
   Verified by pinning particles in place (`Velocity 0.0005`) and reading
   the emitter's on-screen region indicator in the Fusion viewer — it
   landed at (0.244, 0.086) against a target of (0.24, 0.07). If a position
   ever looks wrong, **pin the velocity and look at the region indicator
   before touching the maths** — it makes the origin unambiguous in one
   render-free check.
3. **`Angle 90` = up. No sign flip needed on this axis.** Rising embers
   worked at `+90` first try. The "try negative first" note below was
   specific to the doorway's down-right geometry, not a universal rule —
   treat it as "verify the direction", not "negate it".

Working dust values on this video: `Number 3, Lifespan 110, Velocity 0.004,
VelocityVariance 0.002, AngleVariance 22, ParticleStyle.Size 0.38,
ColorControls 1, Green 0.78, Blue 0.4`, region ~`0.10 × 0.12` at the
source. Embers: `Number 9, Lifespan 60, Velocity 0.003, Angle 90,
Size 0.30, Green 0.45, Blue 0.12`, region `0.03 × 0.03`.

**Ease the effect in.** Keyframe the Merge's `Blend` from 0 to 1 over about
a second (`time 0 → 30` at 30fps) so particles arrive softly instead of
popping on at the cut. Applied to all five scenes here.

## Interaction with Ken Burns motion — decide where the Merge goes

If the scene also carries a zoom or pan, **put the Merge BEFORE the
Transform** (`MediaIn1 → Merge → Transform → MediaOut1`). Particles then
travel with the plate, which is correct: dust in a shaft and embers on a
torch belong to the scene, not to the screen. Placing the Merge *after* the
Transform leaves them in screen space, floating independently of the image.

Three consequences to account for:

- **`Size` multiplies both particle size and apparent velocity.** At
  `Size 1.6`, a `ParticleStyle.Size` of 0.22 renders like 0.35 and the
  drift moves 1.6× faster on screen. Dial the emitter down accordingly.
- **The emitter must stay inside the moving crop window** for the whole
  move. A torch at the far-right edge (0.92, 0.12) produced *no visible
  embers at all* on a panning scene — the window barely reached it, and
  rising particles left the top of frame immediately. Pick a source with
  real headroom that stays in shot.
- **Net on-screen motion is particle drift plus camera drift**, so embers
  rising during a rightward pan read as rising-and-drifting-left.
  Physically right, easy to misjudge.

**Editorially, be wary of particles on a scene whose pan is already the
feature** — the pan may be carrying the shot, and a second moving element
can muddy it. Worth judging on playback per scene rather than by rule.

## Verification

Same two-tier approach as `apply-ken-burns`: **no-render GUI/screenshot
check by default** (Windows screenshot-capture technique — see that
skill's own section, reusable as-is here), reserve an actual render for
final confirmation and **always ask before rendering** unless the user
already has. Particle motion in particular is easy to misjudge from a
single static screenshot (a frame mid-cone can look sparser or denser than
the effect reads in motion) — where possible, prefer the user watching the
live Fusion viewer play back over a single frame grab.

## Reusable template — `DoorwayDust.setting`

The confirmed-working build below has been grouped in Fusion (`Group1` →
`DoorwayEmitter`/`DoorwayRender`/`DoorwayMerge`/`DoorwayGlow`) and exported
via `fusion_comp(action="group_settings_export")` to **two places**:
`.claude/skills/apply-particles/templates/DoorwayDust.setting` (this repo,
for reference) and the live Fusion Settings folder
(`%AppData%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Settings\
DoorwayDust.setting`), so it now shows up in the Effects Library / is
loadable via `group_settings_load` in **any** Resolve project, not just
this one. Grouping itself has to happen by hand in the Fusion GUI (select
the tools, Ctrl+G) — there's no MCP action to create a group, only to
export/load an existing one's settings.

**Note**: `group_settings_load` needs a **pre-existing named `GroupOperator`
already in the target comp** to load values into — it does not insert a
fresh group from the `.setting` file. On a new scene, either group-and-load
into a stub group first, or just use this file as a values reference and
rebuild from primitives per the recipe above (which is what step 1 already
recommends for the same reason).

## Confirmed-working reference build (Tomb Robber scene-01, doorway dust)

Kept as a concrete worked example, not a template to copy verbatim onto a
different scene — region position/size and `Angle` are specific to this
doorway's on-screen position and light direction.

- `DoorwayEmitter` (`pEmitter`): `Number=4, Lifespan=200, Velocity=0.025,
  VelocityVariance=0.01, Angle=-30, AngleVariance=15,
  Style=ParticleStyleBlob, Region=RectRgn, RectRgn.Width=0.11,
  RectRgn.Height=0.15, RectRgn.Translate.X=-0.279,
  RectRgn.Translate.Y=0.05, RectRgn.Rotate.Z=0, ParticleStyle.Size=0.4,
  ParticleStyle.ColorControls=1, ParticleStyle.Green=0.78,
  ParticleStyle.Blue=0.4`
- `DoorwayGlow` (`Glow`): `Blend=0.14, Filter="Fast Gaussian",
  XGlowSize=10`
- Chain: `MediaIn1 → DoorwayEmitter → DoorwayRender (pRender) →
  DoorwayMerge (Screen, fg) ← MediaIn1 (bg) → MediaOut1`, with
  `DoorwayGlow` applied on the relevant layer per the Blend note above.

## What this skill does NOT do

- Does not decide *whether* a scene should have a particle effect, or
  what kind — that's an editorial call the plan (or the editor directly)
  makes, same division of labor as `plan-ken-burns`/`apply-ken-burns`.
- Does not cover Ken Burns motion (zoom/pan) — see `apply-ken-burns`.
- Does not confirm whether `Region` supports shapes beyond `RectRgn`/
  `SphereRgn` — untested, not blocking so far since `RectRgn` has covered
  every case tried.
- Does not view the actual generated scene image to judge composition —
  same caveat as the Ken Burns skills: confirm the real doorway/light-source
  position in the actual generated file before positioning a region, don't
  assume from the prompt text alone.
