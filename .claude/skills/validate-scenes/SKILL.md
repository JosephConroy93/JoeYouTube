---
name: validate-scenes
description: Runs per-scene QC on fetched images against a project's shared qc-checklist.md — four coarse checks (scene match, character consistency, major era violations only, nothing malformed) plus text-cards' own exact-text rule. Reads batch-log.md rows at status=fetched, checks images in small 5-8-image subagent groups (never one long pass), writes failures to prompt-hardening-log.md, and sets status=validated with a pass/fail count. Does NOT retry, resubmit, or revise anything — marks what failed and why, full stop; deciding whether a failure is worth a plain resubmission or a prompt revision (scene-prompter Mode 3) is left to whoever's driving the session. Split out from the original generate-scenes skill 2026-09-10 specifically to separate "check" from "act."
---

# Validate scenes — check only, no retries

Runs QC against a batch's fetched images and reports pass/fail per scene,
with a concrete reason for every failure. **Does not act on a failure in
any way** — no automatic retry, no automatic prompt tweak, no automatic
resubmission. That decision belongs to whoever's driving the session, made
*after* reading this skill's report, not inside it.

**Before invoking this skill at all**: the session driving the pipeline
should offer Joe the choice of reviewing the fetched images himself first,
rather than always spending an automated QC pass. This is orchestration
behavior, not something this skill decides — by the time this skill runs,
the choice to run automated QC has already been made.

**If Joe reviews the fetched images himself instead of this skill running,
the "Recording results" step below still has to happen** — whoever's
driving the session writes `status=validated` to the relevant `batch-log.md`
row (same format this skill uses: a short pass/fail count) based on Joe's
verdict, and logs any FAIL he calls out to `prompt-hardening-log.md` the
same way this skill would. **Confirmed gap, 2026-09-11**: several chapters'
rows sat at `status=fetched` indefinitely, read by a later session as
"never QC'd," even though Joe had already reviewed them — the QC happened,
the write-back didn't, because it was implicitly treated as *this skill's*
job and this skill was never invoked for a conversational review. The
write-back is owned by the *review event*, not by this skill specifically —
don't assume a `fetched` status means unreviewed without asking first.

## Prerequisites

- `content/watcher-pov/<slug>/claude/qc-checklist.md` exists (written once
  per video by `scene-prompter` Mode 2) — the four standing checks plus the
  text-card exact-text rule. Read it once per validation run, not once per
  image.
- `content/watcher-pov/<slug>/claude/batch-log.md` has at least one row at
  `status=fetched` (if nothing's fetched yet, say so and stop — that's
  `get-scenes`' job first).
- The images themselves exist at
  `content/watcher-pov/<slug>/scene-generation/<scene_id>.jpg` (or
  `<scene_id>.attempt-N.jpg` for a resubmission — validate whichever is the
  latest attempt for that scene_id).

## The four checks (from `qc-checklist.md`, redesigned 2026-09-10)

Coarse pass/fail on the image as a whole — not an itemized negative-by-
negative sweep:

1. **Scene match** — does the image depict roughly the intended action/
   setting from that row's `content_prompt`? Catches "generated something
   unrelated," not fine-grained deviation from every clause of
   `script_bookmark`.
2. **Character consistency** — do the attached reference character(s) read
   as themselves (identity/build/hair/skin), and are they free of anything
   that breaks their locked description (a crown on a character who should
   never wear one fails *this* check, not a separate one).
3. **No major era violation** — check only against this video's own
   `qc-checklist.md`-listed big, obviously-visible anachronisms, at a
   size/prominence a viewer would actually notice. **Deliberately do not
   hunt for minor background detail** — illegible marks on a small prop,
   incidental texture, anything needing a zoomed crop to even see is out
   of scope, not logged, not a reason to fail.
4. **Nothing malformed or visually broken** — extra/missing limbs, warped
   anatomy, garbled faces/hands, nonsensical composition.

**Text-card rows keep their own separate, stricter, unchanged
requirement**: exact character-for-character text match against the quoted
line, no stray second line or marks anywhere else on the card. Checked in
addition to (not instead of) checks 1-4.

Any scene-specific flag in that row's own `notes` (a mascot cameo, a
sanctioned negative override) is context for the check above, not a fifth
check — it tells you what "correct" looks like for that one scene.

## QC dispatch sizing — 5-8 images per subagent, never one long pass

Each image read adds real weight to an agent's context, and that weight
compounds across every subsequent tool call in the same conversation (see
`CLAUDE.md`'s token-hygiene rules). A chapter's worth of fetched images
(16-25) gets reviewed across ~3 small subagent dispatches, never one
sequential pass — this is independent of how many scenes were in the
original batch submission.

## Recording results

**Pass** → nothing further needed; the file at `scene-generation/<scene_id>.jpg`
stands as final.

**Fail** → write one entry to `content/watcher-pov/prompt-hardening-log.md`
for every failure, even one that looks like an obvious fluke — a pattern
is only visible once entries exist to compare. Follow the file's own
existing entry format: what the prompt asked for, what the image actually
showed, which of the four checks (or the text-card rule) it failed, and
why it matters. If a fragment already in that log clearly explains what
just happened again, note the recurrence there directly rather than
writing a near-duplicate entry.

**No retry, no regeneration, no prompt edit happens as part of this
skill** — the failed image stays on disk exactly where it landed; nothing
gets deleted or moved. Once every fetched image in the batch has been
checked, update that `batch-log.md` row: `status=validated`, with a short
pass/fail count (e.g. "18/20 passed, 2 failed: `047`, `112`").

## What happens after a failure — not this skill's decision

Report failures plainly and stop. Whoever's driving the session reviews
`prompt-hardening-log.md`'s new entries and decides, per failed scene:

- **Plain resubmission** — a fresh `generate-scenes` call with the same
  request, on the theory it was ordinary generation variance (a "maybe it
  was a fluke" retry). Cheap to try, costs one more generation at the
  normal per-image rate.
- **Prompt revision first** — if the failure looks systematic rather than
  a fluke (the same check failing the same way, or a pattern already
  logged in `prompt-hardening-log.md`), a `scene-prompter` Mode 3 (REVISE)
  pass on that row's `content_prompt` before resubmitting.

This skill doesn't guess which — it isn't equipped to judge "fluke vs.
systematic" from a single failure, and guessing wrong costs real money
either way (an unnecessary revision, or a repeat of the same failure).

## What this skill does not do

- Does not fetch batch results — that's `get-scenes`, which must have
  already run and set `status=fetched` before this skill has anything to
  check.
- Does not retry, resubmit, or revise a prompt under any circumstance.
- Does not decide fluke-vs-systematic for a failure, or which model/tier
  to use on a resubmission — reports the failure, leaves the decision to
  whoever's driving the session.
