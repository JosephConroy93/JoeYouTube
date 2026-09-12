---
name: plan-ken-burns
description: Reads an approved scene-prompts.md manifest and its script, and produces a per-scene Ken Burns editing-suggestions table for DaVinci Resolve's Edit page. Three tiers per scene — Baseline zoom (In/Out, the default for ~85%+ of scenes), Elevated motion (Pan or Focal-Point Zoom on a confirmed off-center target, capped ~10%), and FX-candidate flags (Fusion particle/glow suggestions, flat-capped at 5 scenes, suggestion-only — never executed by this skill). Static is now reserved for text-card/papyrus scenes only. Elevated/FX candidates get their real on-screen target confirmed by delegating scene-image reads to subagents (never read directly in the main planning pass) — see "Candidate discovery" below. Use once scene generation is done and the editor is starting Step 8 assembly. Universal across projects, not Tomb-Robber-specific. Produces a draft applied by hand, or via the sibling `apply-ken-burns` (Baseline/Elevated motion) and `apply-particles` (FX) skills — this skill itself only plans, never touches Resolve.
---

# Plan Ken Burns (Resolve editing-suggestions table)

Consumes an already-approved `content/<series>/<slug>/claude/scene-prompts.md`
manifest and the script it was segmented from, and produces
`content/<series>/<slug>/claude/ken-burns-plan.md` — a per-scene table the
editor applies by hand in Resolve's Edit page, or executes via
`apply-ken-burns`/`apply-particles`, while watching the real assembled video
back.

**This is a draft, not a decision.** WORKFLOW.md Step 8 is explicit that
editorial judgement (pacing, emphasis, where a beat holds) stays human, not
automated — this skill exists to save the editor from starting each scene
from a blank page, not to remove their judgement from the loop. Every scene
here should get watched and overridden where it doesn't feel right.

**Three tiers per scene, on top of one another** — see "Three tiers" below
for the full breakdown. Two of the three (Elevated motion, FX-candidate)
require confirming something about the scene's *actual pixels*, not just its
prompt text — handled via a delegated subagent image-read pass (see
"Candidate discovery"), not by this skill reading images itself.

## Motion is the default; Static is reserved for text-cards only (tightened 2026-09-08)

**This reverses the 2026-09-07 version of this section (Static by default,
walked back 2026-09-08 to motion by default), and further tightens the
2026-09-08 version, which still let short illustrated scenes qualify for
Static.** That carve-out never had independent evidence behind it — it was
inherited unchanged from the old Static-by-default logic when the rule
flipped, and it directly contradicts the finding that flipped the rule in
the first place: direct competitor review (POVrank's "Every Rank in the
Chinese Communist Party," frame by frame) showed **motion runs on nearly
every scene, including short ones** — static frames are rare, not the norm,
and nothing in that review suggested short scenes specifically go static.

**Motion is the default for every illustrated scene, full stop.** **Static
is reserved for exactly one case: text-card/papyrus scenes** — letting the
text be read is a real, separate rationale text-card scenes have and
illustrated scenes don't. The ~10% cap on Static still applies as a ceiling,
but in practice this will rarely bind now — it's a backstop in case a
video's script leans unusually text-card-heavy, not a target to fill.

## Three tiers of scene treatment (new 2026-09-08)

Every scene gets exactly one **motion tier**, plus an independent, additive
**FX flag**:

| Tier | What it is | Cap | Who executes it |
|---|---|---|---|
| **Baseline** (default) | Plain In/Out zoom via Resolve's Dynamic Zoom panel — the workhorse for the large majority of scenes | No cap (it's the default) | Editor by hand, or `apply-ken-burns` |
| **Elevated** | A **Pan** or **Focal-Point Zoom** targeting a specific confirmed on-screen point — used deliberately to raise production value and read as more considered than a generic center-zoom (this also helps avoid a "low-effort" read on the channel) | **~10% ceiling** | `apply-ken-burns` (proven automation for both) |
| **FX-candidate** *(additive, not a motion tier)* | A flagged suggestion that a scene would suit a Fusion particle/glow effect (dust, embers, sparks) alongside whatever motion tier it has | **Flat 5 scenes**, not a percentage | **Nobody, yet** — flagged only. Applied by the editor with Claude via `apply-particles`, scene by scene, during Step 8 |

**Precedence when a scene qualifies for more than one thing**:
**FX-candidate > Elevated > Static.** An FX-candidate scene keeps
whatever motion tier suits it (usually Elevated, but Baseline is fine too —
FX doesn't require Elevated motion) and is never downgraded to Static. An
Elevated-motion scene is never downgraded to Static either. In short: once a
scene earns a "more deliberate" treatment, nothing after that in the
decision process should walk it back down to the least deliberate option.

**Why FX stays suggestion-only here**: `apply-particles` is proven on
exactly one effect (doorway dust, Tomb Robber scene-01) after a full
session of live back-and-forth tuning against the real Fusion viewer — the
same "validate small before trusting at scale" discipline as the Sollo
lesson (`research/inventory.md` §2a). This skill's job is to surface good
*candidates* (and point at a reusable template like `DoorwayDust.setting`
when one plausibly fits), not to silently auto-build FusionFX across dozens
of scenes on the strength of one data point. Scaling this up to real
auto-execution is a future decision, made once there's more than one
confirmed effect to generalize from.

## Candidate discovery — text pass, then delegated image verification

Two passes, only the second one touches actual scene pixels:

1. **Pass 1 (this skill, text only, cheap).** Read the script and
   `scene-prompts.md` manifest and shortlist candidate scenes for Elevated
   motion and/or FX, from **prompt-text signals only** — the same kind of
   signals the old "manual flag" rules used to look for:
   - An emotionally important detail described as **off-center or partially
     hidden** ("a hint of gold visible in the darkness") → Focal-Point Zoom
     candidate.
   - **Multiple distinct elements that need reading in sequence across the
     frame** (several tomb entrances along a cliff face) → Pan candidate.
     **Independent of this signal**, Joe also has a standing stylistic
     preference for horizontal pans generally — see the callout under
     "Elevated assignment" below — worth weighing on any scene with enough
     width/depth to support one, not only ones with distinct sequential
     elements.
   - An **environmental light/fire source described in the prompt** — a
     doorway, window, torch, campfire, brazier — → FX candidate (dust/embers
     matching the confirmed `apply-particles` pattern).
     **A light source in the prompt is necessary but NOT sufficient — gate it
     on darkness (added 2026-09-12).** The `apply-particles` recipe merges pale
     particles with **Screen**, which can only brighten, so on a high-key image
     the effect is invisible no matter how it is tuned. Before flagging any
     scene FX, measure the mean luma of the image region the particles would
     drift through and **reject anything above ~0.40** (see
     `apply-particles` → "Precondition: the backdrop must be dark enough" for
     the exact command and thresholds). On Pharaoh's Servant three of five FX
     scenes were flagged on the light-source signal alone, built with identical
     settings to the one that worked, and were invisible in the finished
     render — all three were high-key. **Cheapest reliable filter: rank every
     scene image in the video by mean luma first, and draw FX candidates only
     from the darkest handful.** The two that worked were the two darkest
     images of 198.
   - A **splice-point or callback scene** (see below) — already worth extra
     deliberateness for other reasons, worth checking as Elevated candidates
     too.
   This pass produces a shortlist **larger than the final caps** — it's a
   "worth checking," not a final answer.
2. **Pass 2 (delegated to subagents — do not read these images directly in
   the main planning context).** Per CLAUDE.md's token-hygiene rules, dump
   batches of shortlisted scenes (5-8 at a time, same batching `generate-scenes`
   already uses) to a subagent each. Each subagent:
   - Opens the actual generated image for each shortlisted scene — the
     manifest's own filename field is what ties a script chunk to a specific
     image file on disk, so this is a targeted handful of reads, never all
     scene images.
   - Confirms or rejects the candidacy against the real pixels (a prompt can
     describe something the actual generation didn't render clearly).
   - For a confirmed **Elevated** candidate: returns the real target point in
     **top-down image-fraction coordinates** (0-1, origin top-left — the same
     convention already used elsewhere in this project; `apply-ken-burns`
     handles the Fusion Y-flip itself, don't pre-convert here) — a single
     point for Focal-Point Zoom, or two-plus points for a Pan.
   - For a confirmed **FX** candidate: returns a one-line description of
     what's actually visible (e.g. "doorway, left third of frame, visible
     light beam crossing toward center") and whether an existing template
     (`DoorwayDust.setting` — see `apply-particles`) plausibly fits or a new
     build would be needed.
   - Returns only this compact structured verdict — **raw image tokens never
     enter the main planning thread**, matching how `generate-scenes`'
     per-scene QC already works.
3. **Final selection.** From the confirmed-back candidates, rank and select
   up to the caps (Elevated ~10%, FX flat 5), apply the precedence rule
   above, and respect the variance rule below. Any shortlisted-but-unpicked
   or rejected candidate just falls back to Baseline treatment under the
   normal per-scene rules — being shortlisted isn't a promise.

## Resolve's real Dynamic Zoom constraint — read this before assigning Baseline motion

Confirmed by hand against a live Resolve session (2026-09-04), not assumed
from the UI or documentation: **Dynamic Zoom's Ease dropdown only produces
three real combinations**, not free direction × curve combination:

| Ease dropdown value | Actual direction | Actual curve |
|---|---|---|
| Linear | **Out** only | constant speed |
| Ease In | **In** only | accelerating |
| Ease Out | **Out** only | decelerating |

**Swap** toggles between Ease In ↔ Ease Out specifically — it does nothing
when Linear is selected, and there is no way to get a constant-speed zoom-**in**
through this panel at all.

**Practical rule this skill follows for Baseline scenes**: never assign "In +
Linear" or "Out + Ease In" — those don't exist. Where the ideal pacing would
be a flat/constant zoom-in, assign **In + Ease In** instead (the acceleration
is subtle over a 10-40s clip and not worth manual keyframing on its own).
The three real presets are the only non-manual options:

- **Out + Linear** — steady pull-back
- **In + Ease In** — building push-in
- **Out + Ease Out** — decelerating release

**This constraint is specific to the Dynamic Zoom panel — it does not apply
to Elevated-tier scenes.** Pan and Focal-Point Zoom are built via
`apply-ken-burns`'s Fusion Transform automation, not the Dynamic Zoom panel
at all, so they aren't limited to these three presets — an Elevated scene's
`Ease` value is still one of Linear/Ease In/Ease Out for consistency of
language in the plan, but it's expressed as a keyframe curve shape in Fusion
(`apply-ken-burns` handles this), not a dropdown choice.

## Prerequisites

- `scene-prompts.md` exists and is the approved manifest (not a draft/revision
  in progress), and its per-scene rows include the generated image's filename
  — required for the delegated image-verification pass above.
- The script it was segmented from (for narration tone/pacing — the `---`
  section breaks in the script are load-bearing, see below)
- All scenes are already generated on disk (required this time, not just
  recommended — the FX/Elevated candidate-confirmation pass needs the real
  files to read)

## Per-scene decision rules

**Static vs. motion — decide this first.** Default to **motion** for every
scene. A scene qualifies as Static only if it's a **text-card/papyrus
scene** (`scene_type` containing "text-card") — nothing else qualifies,
regardless of runtime. If more text-card scenes exist than the ~10% cap
would allow, that's a real flag worth raising to Joe rather than silently
motion-izing text cards (motion actively works against text-card readability
— see below), but this should be rare.

**Baseline Direction** — read from the scene's actual content/mood, not a
fixed pattern:
- **In**: building tension, a reveal, drawing into intimacy/emotional weight,
  a quiet realization, a detail that matters (an object, an expression)
- **Out**: establishing shots, isolation/scale, aftermath, release/settling,
  absence (a space that used to have someone in it)

**Baseline Ease** — from the three-preset constraint above:
- **Ease In** (In + accelerating) for beats building toward something that
  lands at the end of the clip
- **Linear** (Out + constant) as the default steady pull-back — the
  workhorse for establishing/context beats
- **Ease Out** (Out + decelerating) for genuine release/settling/ending beats

**Elevated assignment** — from the confirmed candidates (see "Candidate
discovery"), pick up to the ~10% ceiling. Prefer scenes where the confirmed
target genuinely earns the extra deliberateness (the emotionally important
beat actually reads better landing tight on the confirmed point) over
picking scenes just to fill the quota — the cap is a ceiling, same discipline
as the old Static cap.

**Joe's standing style preference (2026-09-09): horizontal pans, no zoom.**
Joe likes the look of a slow, full-scene-duration lateral pan — starting
from one side of the frame and moving to the other (left→right, or the
reverse, right→left) — with **no zoom paired with it**: the framing scale
should read flat to the viewer, just lateral movement, not a push/pull
happening alongside the pan. When picking Elevated candidates, weigh a
horizontal pan of this specific style as a real, favored option — not only
when the stricter "multiple sequential elements" signal above is present.
Still counts against the same ~10% Elevated ceiling and the caution flags
(crowded compositions, negative-space framing) unless Joe says otherwise.
Record the direction explicitly in the plan's `Note` column (e.g. `Pan:
left→right, no zoom`) alongside the usual target coordinates, so
`apply-ken-burns` executes the right direction — see that skill's own note
on the technical side of "no zoom" (a pan still needs a static scale-up for
headroom to move within, which is different from an animated zoom).

**Caution flags — hold back from a confident automatic assignment**, even
post-image-confirmation:
- The scene has **4+ reference images / a crowded composition** — pushing in
  risks cropping into the group awkwardly; a confirmed subagent read should
  lean toward recommending Baseline Out (hold wide) over Elevated here, not
  toward picking a focal target
- The composition is explicitly built around **negative space or absence**
  ("composed for absence — small in frame, turning away") — an automatic
  zoom target (even a confirmed one) usually fights this rather than serves
  it; flag as `Note`-only guidance for the editor rather than assigning
  Elevated with confidence

**Text-card / papyrus scenes**: always Static, or if a slow minimal move is
truly wanted, a gentle Baseline In + Ease In at the smallest comfortable
magnitude. The point is to let the text be read, not to demonstrate motion.

**Splice-point scenes**: cross-reference against the audio's own
part-boundaries (wherever the voiceover was split for a >5000-character TTS
cap — see the script's own `---` section breaks, which should be the actual
split points per the process note in `voiceover-research.md`). The scene
right before and right after an audio join deserves slightly more deliberate
motion — it's doing double duty covering the edit — and is worth checking as
an Elevated candidate for that reason alone.

**Callback compositions**: scene-prompts.md often flags a scene as a
deliberate callback to an earlier one (same location, mirrored or inverted
framing). Check the `notes` column for this. Where found, consider giving
the pair **opposite zoom directions** on purpose (the earlier one pushes in,
the callback pulls out, or vice versa) — that's a visual rhyme worth making
deliberate rather than leaving to chance, and a strong candidate pair for
Elevated treatment on both ends.

**Variance**: don't let the same Direction+Ease combination run more than
~3-4 scenes in a row unless the content genuinely calls for it. **A long run
of consecutive Static scenes is itself a flag** — with Static now
text-card-only, this should mean nothing more than "there are several
text-cards in a row," which is fine; it should never mean illustrated scenes
crept into Static. Also space out Elevated/FX scenes across the video rather
than clustering them — the point is deliberate emphasis, which is lost if
several land back-to-back.

## Black-sweep transition — ~1 in 10 scenes, permanently a manual step

A second, separate per-scene decision alongside motion tier/FX: whether this
scene ends on a **gradual sweep to black (~0.5s) before the next scene
begins**, rather than a straight cut — the effect Joe pulled directly from
real competitor footage (a scene fades to black while its caption briefly
persists on the black frame, then the next scene begins).

**Manual on Resolve 19.1.3.7 — but NOT "impossible forever."** The
2026-09-08 version of this section claimed transitions "cannot be
automated, not just 'not yet'" and would "stay a manual GUI step forever."
**That was wrong, and was corrected 2026-09-11** against the MCP server's
own verified API ledger:

- **`TimelineItem.AddTransition` exists from Resolve 21.1.** Signature
  `AddTransition(transitionOptions)`, where the options carry `type`
  (e.g. `'Cross Dissolve'`), `category` (`simple`/`fusion`/`ofx`/`audio`),
  `position`, `alignment`, and an optional duration in frames. The ledger
  claims existence and signature only — it was deliberately never invoked
  (a call mutates a real timeline), so it is version-verified, not
  behaviour-proven.
- **Offline authoring already works today**: a cross dissolve written at an
  abutting cut round-trips into Resolve and reads back at the expected
  centred range.
- **What genuinely does not work on 19.1.3.7**, which is what this project
  runs: the scripting API has no transition-creation method at all, and the
  FCP7 XML importer "does NOT carry a TRANSITION's parameters" — a *Dip to
  Color Dissolve* authored that way was measured **rendering inert on
  exactly this build** (luma flat through its whole window). So the
  black sweep this skill plans is specifically the case that fails.
- **Readback stays missing even on 21.1** — no accessor for an existing
  transition's type, alignment or duration beyond its name and frame range.

**Practical upshot**: keep planning black sweeps as a manual GUI step while
on 19.x, but treat that as a version constraint with a known exit, not a
permanent law. On 21.1+ prefer `AddTransition` and prove it on one real
cut before trusting it across a video.

**Target roughly 1 in 10 scenes** — deliberately chosen at meaningful
beat-boundaries, never evenly spaced or random:
- An **act/section closer** — the last scene before a `---` break
- The end of a **rank/level** in a Category B video, where the next scene
  starts a new rank
- A beat that earns a breath before the next thought lands

**Justify each one in `notes`**, same discipline as the other per-scene
flags — a black-sweep with no stated reason is a segmentation-table miss,
not a judgement call. Note this is a different axis from motion tier — it
doesn't clash with the Elevated/FX precedence rule above (a scene can be
both an FX-candidate and a black-sweep closer), but don't let a black-sweep
and an already-Elevated 7-8s hold stack without checking it actually reads
right together.

## Output format

Write `content/<series>/<slug>/claude/ken-burns-plan.md`. Group scenes by
the script's own `---` section breaks (call them acts/parts) — those breaks
are real narrative beats and usually line up with the voiceover's own split
points too, worth calling out explicitly at the top of the file if so.

Table columns: `#` | `Scene` | `Zoom` (In, Out, **Static**, or **Pan**) |
`Ease` (L/EI/EO, blank for Static) | `FX` (blank, or a short tag like
"particles — doorway" for one of the flat-5 FX-candidates) | `Transition`
(blank for a normal cut, or **Black sweep**) | `Note` (required whenever
Zoom is Static or Pan, the scene is an FX-candidate, or Transition is Black
sweep; blank otherwise). For a Pan or Focal-Point Zoom, `Note` must carry the
confirmed target coordinate(s) from the subagent pass, in the format
`Focal target: (x, y) top-down` or `Pan: (x1,y1)→(x2,y2) top-down`. For an
FX-candidate, `Note` carries the subagent's one-line visual description plus
whether an existing template fits (e.g. `Doorway, left third, visible beam
— DoorwayDust.setting likely fits`).

Put a short legend above the first table stating plainly that **Baseline
motion is the default/expected value**, Static is text-card-only, and
Elevated/FX are capped ceilings, not targets to fill. Close the file with a
one-paragraph summary covering: how many scenes are Baseline vs. Static
(and whether Static is under its ~10% cap — expect near-zero unless the
script has real text-cards), how many are Elevated (and whether under the
~10% cap), how many are FX-candidates (should be ≤5, and list them by number
so the editor can find them fast during Step 8), how many got the
black-sweep transition (and whether near ~1-in-10), and which scenes carry a
caution-flag note.

## What this skill does NOT do

- Does not open, drive, or script Resolve itself. Baseline and Elevated
  motion can be executed via the `apply-ken-burns` skill; FX-candidates are
  suggestion-only and always executed by hand (with Claude) via
  `apply-particles` during Step 8 — this skill produces the plan either way.
- Does not decide captions, loudness, or anything else in Step 8's scope.
  For transitions specifically: decides only the black-sweep transition
  described above (~1 in 10 scenes, permanently manual — see above) — every
  other transition type (fade, wipe, a differently-timed dip-to-black)
  remains the editor's manual choice during assembly, not planned here.
- **Does now read scene images — but only for shortlisted Elevated/FX
  candidates, and only via delegated subagents, never directly in the main
  planning pass, and never for every scene.** This is a deliberate,
  narrow exception to the old blanket "never views generated images" rule,
  scoped specifically to confirming a real on-screen target point or a
  real environmental-effect opportunity. For any scene where a subagent
  read wasn't run (i.e. everything outside the shortlist), the old caveat
  still holds: if a Baseline scene's real composition turns out different
  from what the prompt described, trust the image, not this table.
