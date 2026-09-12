---
name: chain-scenes
description: Orchestrates generate-scenes/get-scenes/validate-scenes across two phases for one chapter, so consistency-linked scene groups (same location, held pairings generated as separate requests) can use a real generated image as a continuity reference instead of relying on repeated text alone. Dispatches scene-prompter Mode 4a to find groups and pick a seed scene per group; if none are found, says so and stops — defer to a plain generate-scenes call instead, this skill is not the default submission path. For each group found: submits just the seed scene(s) via generate-scenes, polls narrowly via get-scenes until that small batch resolves (the one deliberately bounded exception to this project's "don't request-then-poll" rule — scoped to a handful of seed images, never a whole chapter), quick-QCs the seed(s) via validate-scenes, then dispatches scene-prompter Mode 4b to rewrite the dependent rows' content_prompt with a second positional reference image plus an explicit pose/composition guard (added after a real over-matching failure on Pharaoh's Servant scene 018), and finally submits the remainder of the chapter via generate-scenes as normal. Calls the other three skills exactly as documented, unmodified — never fetches or QCs the remainder batch itself, that's the normal get-scenes/validate-scenes flow run afterward. Added 2026-09-10, unproven beyond one manual precedent (level-01's 016/017/018) — validate on one real chapter before treating as the default path for a chapter with known continuity groups.
---

# Chain scenes — seed-then-chain submission for continuity groups

Most chapters don't need this. Most scenes that share a location only share
it for one or two consecutive rows, held in a single generation — continuity
by construction, nothing to fix. This skill exists for the narrower case: a
group of 2+ `illustrated` rows that will be generated as **separate** batch
requests but need to look like the same physical place, where repeating "the
same courtyard" in the prompt text alone isn't enough (confirmed real
failure: Pharaoh's Servant level-01's `016`/`017`/`018` — `016` rendered
richer than `017`/`018`, and `018` picked up wall carvings neither sibling
had).

The fix, proven by hand on that exact group before this skill existed:
generate the group's first scene, then attach *that real generated image*
as a second reference when generating the rest of the group. This skill
scripts that as a repeatable two-phase flow, still fully batched — it does
not change how `generate-scenes`, `get-scenes`, or `validate-scenes` work,
it just calls them more than once, with different row scopes, in sequence.

## Before invoking this skill

**Confirm the chapter is a plausible candidate first** — a chapter with no
same-location multi-scene runs gets nothing out of this skill and pays its
overhead (an extra batch submission, a bounded wait) for no benefit. If
unsure, invoke it anyway — step 1 below is cheap and will say plainly if
there's nothing to chain, and the calling session should fall back to a
normal `generate-scenes` call on that report.

**Status, 2026-09-10**: validated exactly once, informally, by hand
(`017`/`018` against `016`, same session that produced this skill) — not
yet run through this scripted flow itself. Per Joe's call, this skill's
first real use should be on **one** chapter, reviewed properly, before it
becomes the default path for every chapter with a detected group — not
rolled out across every remaining Pharaoh's Servant chapter at once.

## Prerequisites

Same as `generate-scenes`: the chapter file exists and is `written` (not
just `planned`) in `scene-prompts.md`'s index, referenced character bible
entries are audited with real files in `reference-images/`,
`GEMINI_API_KEY` is set, and `batch-log.md` exists (or gets created).
`prompt-hardening-log.md` and `content/styles/style-bible.md` get read the
same way `generate-scenes` already reads them — nothing extra to check
here beyond what that skill already requires.

## The flow — one chapter per invocation

### 1. Analyze

Dispatch `scene-prompter` Mode 4a on the target chapter file. It returns a
list of `{seed_scene_id, member_scene_ids[]}` groups, or says plainly that
none were found.

**No groups found → stop here.** Report that back and hand off to a plain
`generate-scenes` call on the whole chapter — don't force this flow onto a
chapter that doesn't need it.

**Groups found → continue**, one group at a time or all seeds together (see
step 2) — either is fine, since each group's seed is independent of every
other group's.

### 2. Submit seeds

Call `generate-scenes`, restricted to just the seed `scene_id`(s) identified
in step 1 — the same explicit-scene-id submission mechanism already used
for a single/paired-scene resubmission after a `validate-scenes` failure
(see that skill's "Cost" section). If a chapter has multiple groups, their
seeds can go in one combined small batch — still far smaller than the
chapter's full remainder.

### 3. Poll seeds

Call `get-scenes` repeatedly, **scoped only to this seed batch**, until it
resolves (`BATCH_STATE_SUCCEEDED` or a terminal failure state). This is the
one deliberately-reintroduced wait in this pipeline, and it's bounded on
purpose: typically 1-4 images, never a whole chapter's batch. This does not
reopen the "request and then poll" pattern the 2026-09-10
generate/get/validate split moved away from — that split was about not
polling for an entire chapter's batch by default; this is a small,
deliberate exception scoped to exactly the images this flow structurally
needs before it can proceed.

If the seed batch terminates in failure (not `SUCCEEDED`), stop and report
it plainly — same as `get-scenes`' own "Outcome 2" handling for any batch.

### 4. Quick QC on seeds only

Call `validate-scenes`, restricted to the fetched seed image(s) — the same
four-check pass it always runs, just scoped to a handful of images instead
of a whole chapter.

**A failed seed stops the flow here.** Don't chain a broken reference into
every dependent scene in its group — that would compound one bad image
into several. Report the failure and let whoever's driving the session
decide (plain resubmission vs. a `scene-prompter` Mode 3 revision on the
seed itself), the same choice `validate-scenes` always hands back. Re-run
this skill from step 2 once the seed is fixed.

A group whose seed passes can proceed to step 5 independently of a
different group in the same chapter whose seed is still being fixed — don't
block every group on the slowest one.

### 5. Rewrite dependents

Dispatch `scene-prompter` Mode 4b on the chapter, passing the group list
and the real seed image path(s) now on disk at
`scene-generation/<seed_scene_id>.jpg`. This rewrites every dependent row's
`content_prompt` (second-reference environment-match language plus the
mandatory pose/composition guard — see that mode's own doc for the exact
wording) and `characters_present`.

### 6. Submit remainder

Call `generate-scenes` for the rest of the chapter: every dependent row
(now carrying 2 reference images — the usual character reference plus the
seed as a location reference) and every ungrouped row, exactly as a normal
chapter submission would. Text-card rows still split into their own
Lite-model batch, same as always. This is a normal `generate-scenes` call
in every respect except that some rows now have an extra reference image
attached — no special handling needed on this skill's part beyond having
already rewritten those rows in step 5.

### 7. Exit

Same boundary as a plain `generate-scenes` call: submitted rows are logged
to `batch-log.md` as `submitted`. **Do not fetch or QC the remainder batch
as part of this skill** — that's the normal `get-scenes` → `validate-scenes`
flow, run afterward by whoever's driving the session, same as any other
batch this project generates.

## Cost and throughput

Roughly doubles the number of batch submissions for a chapter with
detected groups (a small seed batch, then the larger remainder), and adds
one bounded wait for the seed batch to resolve. `WORKFLOW.md` already flags
full-scale batch throughput/reliability as untested at production scale —
this is a reason to keep this skill's use scoped to chapters that actually
have continuity groups, not a blocker on using it at all.

## What this skill does not do

- Does not change how `generate-scenes`, `get-scenes`, or `validate-scenes`
  work — calls each exactly as documented, just multiple times with
  different row scopes.
- Does not fetch or QC the remainder batch (step 6's submission) — stops at
  submission, same boundary as a plain `generate-scenes` call.
- Does not decide fluke-vs-systematic on a seed QC failure, or auto-retry
  anything — surfaces the failure and stops (step 4).
- Does not force chaining onto a chapter with no detected groups — step 1
  is a real gate, not a formality; "no groups" is a normal, valid result
  that hands off to a plain `generate-scenes` call.
- Does not add, remove, or rename any manifest column — group membership is
  recorded as a `notes` addendum by `scene-prompter` Mode 4a, not a new
  structured field (see that mode's own reasoning for why).
