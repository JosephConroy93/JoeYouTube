---
name: validate-scenes
description: Per-scene QC of fetched images for one batch-log.md row (or an explicit scene-id list) against the video's qc-checklist.md - four universal checks plus the text-card exact-text rule, read in 5-8-image subagent groups. Writes every failure to the hardening log and sets the row to `validated (n/m)`. Checks only; never retries, resubmits or edits a prompt.
---

# Validate scenes — check only

Layout, schemas and status words: `.claude/conventions.md`. Project path
`<series>/<slug>`.

## Prerequisites

- `claude/qc-checklist.md`: locked character and location descriptions,
  the period-violation list, text-card strings. Read once per run.
- `claude/batch-log.md` has a row at `fetched`; otherwise say so and stop.
  Read only the rows in scope (grep by status or batch id), never the whole
  log; read a scene's `content_prompt` and `notes` from its chapter row, not
  the whole chapter file.
- Images at `scene-generation/<scene_id>.jpg`, or the highest-numbered
  `<scene_id>.attempt-N.jpg` when one exists; check the latest attempt.

## Scope

Default: the next `fetched` row; "next N" / "rest" take more, each written
back separately. An explicit scene-id list checks those ids only
(`chain-scenes` passes its seeds); a row is written back once every id in
its `scenes` cell has a verdict, else verdicts go in `notes` and it stays
`fetched`.

## The checks

Coarse pass/fail on the whole image, one verdict per scene:

1. **Scene match**: depicts the action and setting of the row's
   `content_prompt`; catches "something unrelated", not clause-level drift.
2. **Character and location consistency**: every figure or place with a
   reference attached reads as its locked reference and shows nothing its
   locked description forbids.
3. **Major period or setting violation**: only items on the checklist's
   list, at a size a viewer would notice. Small-prop marks, incidental
   texture, anything needing a zoomed crop: out of scope, not logged.
4. **Nothing malformed**: extra or missing limbs, warped anatomy, garbled
   faces or hands, nonsensical composition.

Text-card rows additionally: an exact, character-for-character match to
the quoted line; no second line or stray marks anywhere on the card.

A row's `notes` (a cameo, a sanctioned override, a chain group) says what
correct looks like for that scene: context, not a fifth check.

## Dispatch

Subagents read the images, 5-8 each, never one long pass; each returns
per-scene PASS or FAIL, the failed check and a one-line reason. Dispatch
them on **Sonnet** (routing table in `CLAUDE.md`); escalate a disputed
scene to Opus, never a whole batch.

## Writing results

- Every failure: one entry in `content/prompt-hardening-log.md` (the
  incident archive) in that file's entry format (what the prompt asked for,
  what the image showed, which check failed, why it matters), **and** one
  line in the Watch list of `content/prompt-hardening-rules.md`. A
  recurrence is noted on the existing entry and its watch-list line.
- Promotion (the operator's or the driving session's call, never automatic):
  the watch-list line moves to Rules with the next R-number and the log
  entry is marked PROMOTED.
- The row: `status` = `validated (n/m)`, failed ids and checks in `notes`.
  Any review writes this, an operator's direct review included; a row left
  at `fetched` reads as unreviewed.
- Files stay where they are; nothing is deleted, moved or renamed.

## Report

Per scene: PASS, or FAIL with check and reason. Then stop; next steps are
WORKFLOW Step 8's.

## Boundaries

- Does not fetch (`get-scenes`), retry, resubmit, revise a prompt, or pick
  a model for a resubmission.
- Does not promote an attempt or archive anything (`finalize-scenes`).
