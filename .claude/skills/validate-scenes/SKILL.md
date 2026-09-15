---
name: validate-scenes
description: QC-lite of fetched scene images for one chapter (or an explicit scene-id list) — three coarse checks per image (beat, style, malformed) read in 5–8-image Sonnet groups against the cast sheet and the style's source frames. Sets the batch-log row to `validated (n/m)` with failed ids in notes. Checks only; never retries or edits a prompt.
---

# Validate scenes — check only

Layout, schemas and status words: `.claude/conventions.md`. Project path
`<series>/<slug>`.

## Prerequisites

- `claude/batch-log.md` has a row at `fetched`; otherwise say so and stop.
  Read only the rows in scope.
- `claude/cast.md`: costume lines and era don'ts. Read once per run.
- Images at `scene-generation/<scene_id>.jpg`, or the highest-numbered
  `<scene_id>.attempt-N.jpg`; check the latest.
- The prompt as sent: `gemini-batch.ps1 -Action expand -Project
  <series>/<slug> -SceneIds <ids>`.

## Scope

Default: the next `fetched` row; "next N" / "rest" take more, each written
back separately. An explicit scene-id list checks those ids only.

## The checks

One verdict per image, coarse, at the size a viewer sees:

1. **Beat**: the image shows the action, figures and framing the prompt
   asked for; catches "something else", not clause-level drift.
2. **Style**: judged against two of the style entry's `Source frames`
   (attached to every group), never against earlier renders. For a
   costume-identity style every figure, background ones included, keeps
   the head, skin and proportions of the source; a principal keeps their
   cast line's costume. A tan body or a wrong costume fails. Hair, a beard
   or headwear that suits the role is a note, not a fail, unless it hides
   who a principal is. Small face
   detail on any figure (a faint nose curve, a brow crease, a doubled
   mouth mark) and a short neck like the source frames' own are notes, not
   regenerates; a fully drawn face (nose with nostrils, ears, irised eyes)
   fails. Soft airbrushed shading on the far side of a head or under the
   chin, and a short neck above a collar, are the style's own rendering
   (the style block asks for them): never a fail, not even a note.
   The style's own emotion marks (tears, sweat drops, blush, a crack
   across the head for shock, closed arc eyes for a smile) are the style.
   Document scribble that reads as pseudo-handwriting but no real words
   passes. Face rules apply to figures only: a mask, statue or carving
   keeps its own modelled face. A figure rendered with no face at all
   fails. White skin running into white linen is not a costume change.
   References are stricter: a reference with any nose line is
   re-rendered, because every scene that attaches it copies it.
3. **Malformed**: extra or missing limbs, warped anatomy, garbled hands,
   nonsense composition.

A `text-card` row passes with scribble, or with legible words that fit the
scene ("Contract" on a contract, a plausible ledger heading). It fails only
when the words are wrong for it: anachronistic, contradicting the narration,
or garbled text that reads as a mistake.

## Dispatch

Subagents on **Sonnet**, 5–8 images each, returning per image `PASS` or
`FAIL | check | one-line reason`, plus framing and figure count. Each brief
names the image files, the cast sheet, two source frames, the prompts as
sent (`gemini-batch.ps1 -Action expand … | Out-File` to a scratch file) and a
short watch list for that chapter (who appears, what they wear, the known
risks). Escalate a disputed image to Opus, never a group. A group that fails
wholesale on style is looked at by the driving session against scenes that
already passed before anything is resubmitted: a Sonnet group once failed
eight images for the style's own shading.

## Writing results

- The row: `status` = `validated (n/m)`, failed ids and reasons in `notes`.
  An operator's direct review writes the same; a row left at `fetched`
  reads as unreviewed.
- A failure is resubmitted once by `generate-scenes`; a second failure goes
  back to the prompt pass. Nothing retries automatically.
- The same failure on a third image in one video earns one line in
  `content/prompt-hardening-rules.md`; nothing is logged per failure.

## Report

Per image: PASS, or FAIL with check and reason. Then build the chapter's
sheet for the operator and stop:
`python .claude/skills/validate-scenes/scripts/contact-sheet.py <series>/<slug> --chapter <file> --latest`.
