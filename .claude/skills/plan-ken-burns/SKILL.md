---
name: plan-ken-burns
description: Plans per-scene Ken Burns motion and black-sweep transitions for a video whose scenes are generated and timed, writing `ken-burns-plan.md` for `apply-fusion` (or the operator) to execute. Two tiers — Baseline zoom (default) and Elevated pan/focal zoom on a confirmed off-centre target (≤10%); Static is text-cards only; no particle effects. Delegates every image read to subagents. Never touches Resolve.
---

# plan-ken-burns

Invocation: `<series>/<slug>` — see `.claude/conventions.md`.

## Reads and writes

Under `content/<series>/<slug>/`:

- `claude/scene-prompts.md` and the chapter files it names — extract the
  `scene_id`, `scene_type` and `notes` columns with a one-line script rather
  than reading the files; read a row's `content_prompt` only for an
  Elevated candidate.
- `claude/script.md` — tone and beat; chapter headings mark act boundaries.
- `claude/scene-timing.md` — `dur` = the scene's frames in `place-scenes`'
  frame plan ÷ fps: from its start to the next scene's start, across segment
  joins (the image holds through the narration pause). The `segment` column
  marks audio joins. Row count must match the manifest, else stop and name
  the missing ids.
- `scene-generation/<scene_id>.jpg` — **only via subagents** (below).
- `series.md` / `video.md` for fps.

Writes `claude/ken-burns-plan.md`: legend, one table per chapter, closing
summary. Columns exactly as `conventions.md`:

`| # | scene_id | dur | zoom | ease | transition | note |`

- `zoom`: `Static` · `In` · `Out` · `Pan <dir> (x,y)→(x,y)` · `Focal (x,y)`.
  Coordinates are fractions, origin **top-left**; `apply-fusion` does the
  Fusion Y-flip — never pre-convert. `Focal` is the target point in the
  image. `Pan` points are the Transform `Center` start and end, not the
  point looked at: the camera travelling right means `Center.x` falls, so
  `Pan right (0.58,0.50)→(0.42,0.50)` at Size 1.2.
- `ease`: `L` / `EI` / `EO`; blank for Static.
- `transition`: `sweep` or blank.
- `note`: required for Static, Pan, Focal, any `sweep`, any caution flag;
  blank otherwise.

The plan is a draft: the operator watches the cut and overrides it.

## Two tiers

| Tier | What | Cap | Executed by |
|---|---|---|---|
| **Baseline** (default) | In or Out zoom, centre pivot | none — expect ~90%+ | `apply-fusion` batch script, or the Dynamic Zoom panel |
| **Elevated** | `Pan` or `Focal` on a target confirmed in the real image | ≤10% | `apply-fusion`, per scene |

Static is reserved for `scene_type = text-card` and for hook-clip rows
(scenes replaced by `hook-plan.md` footage, which already moves); nothing
else qualifies. If text-cards exceed ~10% of scenes, flag it rather than
motion-ising them. No particle, glow or other overlay effects.

## Dynamic Zoom preset rule

The Dynamic Zoom panel produces exactly three combinations: **Out + L**
(steady pull-back), **In + EI** (building push-in), **Out + EO**
(decelerating release). Never assign `In + L` or `Out + EI`; for a flat
zoom-in use `In + EI`. Pan and Focal are Fusion keyframes and not bound by
this — their `ease` is a curve shape.

## Candidate discovery

1. **Text shortlist (no images).** From script and prompts:
   - an important detail described off-centre or half-hidden → Focal;
   - elements that read in sequence across the frame, or any wide
     composition with room to travel → Pan;
   - scenes either side of a `segment` boundary, and callback pairs named
     in `notes` → check as Elevated.
   The shortlist is larger than the caps.
2. **Image confirmation (subagents, Sonnet, about 6 scenes each; never in
   the main context).** Brief each scene with its prompt intent and ask for
   one line: for a pan, confirm/reject plus which way the camera should
   travel and what it ends on; for a focal, confirm/reject plus the target
   as top-left fractions (reject near-centre targets); a `CAUTION` for any
   head or key object at a frame edge.
3. **Selection.** Rank confirmed candidates, apply the cap, then the
   variance rules; spread picks across chapters and skip a chapter's first
   scene (its card covers the first 2 s). Unpicked candidates fall back to
   Baseline.
4. **Draft the plan** with the picks; the script applies every per-scene
   rule below to the other rows:
   ```
   python .claude/skills/plan-ken-burns/scripts/draft_plan.py <series>/<slug> --fps N --pan 012:right[:note] --focal 044:0.58,0.77[:note] --caution 052:<note> [--summary-extra "<candidates left at Baseline, rejected on the image>"]
   ```
   It refuses to overwrite an existing plan (the operator may have edited
   it) unless `--replace`, which archives the old one.

## Per-scene rules

- **Direction.** `In` for tension, reveals, intimacy, a detail that matters;
  `Out` for establishing shots, scale, aftermath, absence.
- **Ease.** `EI` for beats landing at the clip's end; `L` the default
  pull-back; `EO` for genuine release.
- **Vary direction — no uniform centre-zoom.** Never the same
  direction + ease more than 3–4 scenes running unless the content demands
  it; spread Elevated scenes out rather than clustering them.
- **Horizontal pans.** The operator prefers a slow, full-duration lateral
  pan with no animated zoom; weigh it as a favoured Elevated option on any
  scene wide enough to carry it, keep `y1 = y2`, and write the direction in
  `note` (`Pan left→right, no zoom`).
- **Focal** only on a confirmed off-centre target; a near-centre target is
  Baseline `In`.
- **Caution flags** (note-only, lean Baseline `Out`): crowded compositions
  with 4+ references; compositions built around negative space.
- **Chapter ends.** A chapter's last scene releases on `Out + EO`.
- **Text-cards.** Static; at most a minimal `In + EI`.
- **Splice points.** Scenes bracketing a `segment` change carry the audio
  join — slightly more deliberate motion.
- **Callbacks.** Give a mirrored pair opposite directions on purpose.

## Black sweep

Only when `video.md` sets `transitions: sweep`; otherwise the column stays
blank and the summary says "no transitions". When on: about 1 in 10 scenes ends with a ~0.5 s fade to black, placed only at beat
boundaries — a chapter or act closer, the end of a rank, a line that earns a
breath — never evenly spaced. Justify each in `note`. Manual in the Resolve
GUI below Resolve 21.1; on 21.1+ use `TimelineItem.AddTransition` and prove
it on one cut first. Check a sweep stacked on an Elevated hold still reads.

## Summary paragraph

Close the file with one paragraph: Baseline vs Static counts (Static under
~10%?); Elevated count against ~10%; sweep count against ~1 in 10; every
scene carrying a caution note.

## Does not

- Open, drive or script Resolve — `apply-fusion` executes the plan.
- Decide captions, loudness, or any transition other than the sweep.
- Read images in the main context, or any image outside the shortlist. For
  unshortlisted scenes, if the real composition differs from the prompt,
  trust the image over this table.
