---
name: plan-ken-burns
description: Plans per-scene Ken Burns motion, particle-FX candidates and black-sweep transitions for a video whose scenes are generated and timed, writing `ken-burns-plan.md` for `apply-fusion` (or the operator) to execute. Three tiers — Baseline zoom (default), Elevated pan/focal zoom on a confirmed off-centre target (≤10%), FX flags (≤5, suggestion-only); Static is text-cards only. Delegates every image read to subagents. Never touches Resolve.
---

# plan-ken-burns

Invocation: `<series>/<slug>` — see `.claude/conventions.md`.

## Reads and writes

Under `content/<series>/<slug>/`:

- `claude/scene-prompts.md` and the chapter files it names — `scene_id`,
  `scene_type`, `content_prompt`, `notes` (callbacks, locks).
- `claude/script.md` — tone and beat; chapter headings mark act boundaries.
- `claude/scene-timing.md` — `dur` = `end_seconds − start_seconds`; the
  `segment` column marks audio joins. Row count must match the manifest,
  else stop and name the missing ids.
- `scene-generation/<scene_id>.jpg` — **only via subagents** (below).
- `series.md` / `video.md` for fps.

Writes `claude/ken-burns-plan.md`: legend, one table per chapter, closing
summary. Columns exactly as `conventions.md`:

`| # | scene_id | dur | zoom | ease | fx | transition | note |`

- `zoom`: `Static` · `In` · `Out` · `Pan <dir> (x,y)→(x,y)` · `Focal (x,y)`.
  Coordinates are fractions, origin **top-left**; `apply-fusion` does the
  Fusion Y-flip — never pre-convert.
- `ease`: `L` / `EI` / `EO`; blank for Static.
- `fx`: a particle template name (e.g. `DoorwayDust`) or blank.
- `transition`: `sweep` or blank.
- `note`: required for Static, Pan, Focal, any `fx`, any `sweep`, any
  caution flag; blank otherwise.

The plan is a draft: the operator watches the cut and overrides it.

## Three tiers

| Tier | What | Cap | Executed by |
|---|---|---|---|
| **Baseline** (default) | In or Out zoom, centre pivot | none — expect ~85%+ | `apply-fusion` batch script, or the Dynamic Zoom panel |
| **Elevated** | `Pan` or `Focal` on a target confirmed in the real image | ≤10% | `apply-fusion`, per scene |
| **FX flag** (additive) | particle/glow suggestion on top of any motion tier | flat 5 | `apply-fusion`, per scene, after its luma gate — suggestion only here |

Static is reserved for `scene_type = text-card`; nothing else qualifies. If
text-cards exceed ~10% of scenes, flag it rather than motion-ising them.
Precedence: FX flag > Elevated > Static — a scene that earns a more
deliberate treatment is never demoted later.

## Dynamic Zoom preset rule

The Dynamic Zoom panel produces exactly three combinations: **Out + L**
(steady pull-back), **In + EI** (building push-in), **Out + EO**
(decelerating release). Never assign `In + L` or `Out + EI`; for a flat
zoom-in use `In + EI`. Pan and Focal are Fusion keyframes and not bound by
this — their `ease` is a curve shape.

## Candidate discovery

1. **Luma ranking (subagent, mechanical).** Rank every scene image by mean
   luma (`ffmpeg -v error -i <jpg> -vf "scale=1:1,format=gray" -f rawvideo -
   | od -An -tu1`, ÷255). FX candidates come only from the darkest handful:
   particles are Screen-merged and cannot show on a high-key image.
2. **Text shortlist (no images).** From script and prompts:
   - an important detail described off-centre or half-hidden → Focal;
   - elements that read in sequence across the frame, or any wide
     composition with room to travel → Pan;
   - a light/fire source (doorway, window, torch, brazier) **and** a dark
     luma rank → FX;
   - scenes either side of a `segment` boundary, and callback pairs named
     in `notes` → check as Elevated.
   The shortlist is larger than the caps.
3. **Image confirmation (subagents, 5–8 scenes each; never in the main
   context).** Each returns a compact verdict per scene: confirm/reject;
   for Elevated the target point(s) as top-left fractions; for FX one line
   on what is visible, the mean luma **along the intended particle path**
   (reject > 0.40), and whether an existing template plausibly fits.
4. **Selection.** Rank confirmed candidates, apply caps, precedence, then
   the variance rules. Unpicked candidates fall back to Baseline.

## Per-scene rules

- **Direction.** `In` for tension, reveals, intimacy, a detail that matters;
  `Out` for establishing shots, scale, aftermath, absence.
- **Ease.** `EI` for beats landing at the clip's end; `L` the default
  pull-back; `EO` for genuine release.
- **Vary direction — no uniform centre-zoom.** Never the same
  direction + ease more than 3–4 scenes running unless the content demands
  it; spread Elevated/FX scenes out rather than clustering them.
- **Horizontal pans.** The operator prefers a slow, full-duration lateral
  pan with no animated zoom; weigh it as a favoured Elevated option on any
  scene wide enough to carry it, keep `y1 = y2`, and write the direction in
  `note` (`Pan left→right, no zoom`).
- **Focal** only on a confirmed off-centre target; a near-centre target is
  Baseline `In`.
- **Caution flags** (note-only, lean Baseline `Out`): crowded compositions
  with 4+ references; compositions built around negative space.
- **Text-cards.** Static; at most a minimal `In + EI`.
- **Splice points.** Scenes bracketing a `segment` change carry the audio
  join — slightly more deliberate motion.
- **Callbacks.** Give a mirrored pair opposite directions on purpose.

## Black sweep

About 1 in 10 scenes ends with a ~0.5 s fade to black, placed only at beat
boundaries — a chapter or act closer, the end of a rank, a line that earns a
breath — never evenly spaced. Justify each in `note`. Manual in the Resolve
GUI below Resolve 21.1; on 21.1+ use `TimelineItem.AddTransition` and prove
it on one cut first. Check a sweep stacked on an Elevated hold still reads.

## Summary paragraph

Close the file with one paragraph: Baseline vs Static counts (Static under
~10%?); Elevated count against ~10%; FX flags listed by `#` (≤5, with
path-luma readings); sweep count against ~1 in 10; every scene carrying a
caution note.

## Does not

- Open, drive or script Resolve — `apply-fusion` executes the plan.
- Decide captions, loudness, or any transition other than the sweep.
- Read images in the main context, or any image outside the shortlist. For
  unshortlisted scenes, if the real composition differs from the prompt,
  trust the image over this table.
