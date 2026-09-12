---
name: chain-scenes
description: Two-phase scene submission for one chapter whose consistency-linked scene groups (same location across separately generated rows) need a real generated image as a continuity reference. Finds groups via scene-prompter Mode 4a, generates and validates a seed per group, rewrites dependents via Mode 4b, then submits the remainder. Use when a chapter has known same-location runs; a plain generate-scenes call is the default otherwise.
---

# Chain scenes — seed-then-chain submission for continuity groups

Layout, schemas and status words: `.claude/conventions.md`. Project path
`<series>/<slug>`, one chapter per invocation.

Most chapters need nothing here. This skill is for a group of 2+
`illustrated` rows generated as **separate** requests that must read as the
same physical place, where repeating the location in text alone is not
enough: generate the group's seed scene first, then attach that real image
as a second reference for the rest of the group.

It calls `generate-scenes`, `get-scenes` and `validate-scenes` unmodified,
each with an **explicit scene-id list** argument scoping it to the rows
named, and `scene-prompter` Mode 4a/4b for the judgment in between.

## Prerequisites

Same as `generate-scenes`: the chapter is `written` in the manifest index,
referenced characters are audited with files in `reference-images/`,
`GEMINI_API_KEY` is set, `batch-log.md` exists or is created.

## Flow

1. **Analyze.** Dispatch `scene-prompter` Mode 4a on the chapter file. It
   returns `{seed_scene_id, member_scene_ids[]}` groups or says none were
   found. **No groups → stop**, report it, and hand off to a plain
   `generate-scenes` call on the whole chapter.

2. **Submit seeds.** Call `generate-scenes` with the seed ids only. Seeds
   from several groups can share one small batch.

   **Cross-chapter seed reuse**: if a group's location already has a
   validated image from an earlier chapter (`scene-generation/<scene_id>.jpg`
   with its batch-log row at `validated` and the image among the passes),
   name that id as the group's seed and skip steps 2–4 for it.

3. **Poll seeds.** Call `get-scenes` scoped to the seed batch until it
   reaches a terminal state — the one bounded exception to the
   submit-then-walk-away rule, scoped to a handful of seed images, never a
   chapter. A seed batch that terminates in failure stops the flow; report
   it as `get-scenes` would.

4. **QC seeds.** Call `validate-scenes` scoped to the seed ids. **A failed
   seed stops its group here**: chaining a broken reference compounds one
   bad image into several. Report the failure and leave the
   resubmit-versus-revise decision to the operator; re-enter at step 2 once
   the seed passes. A group whose seed passed proceeds independently of one
   still being fixed.

5. **Rewrite dependents.** Dispatch `scene-prompter` Mode 4b with the group
   list and each seed's path, `scene-generation/<seed_scene_id>.jpg`. It
   rewrites the dependent rows' `content_prompt` (second-reference
   environment-match language plus the mandatory pose/composition guard,
   per that mode's doc) and their `characters_present / reference_images`
   cell.

6. **Submit remainder.** Call `generate-scenes` with every remaining id in
   the chapter: dependents now carrying two references, plus ungrouped
   rows. A normal submission in every respect; text-card rows still split
   into their own batch. Two-reference rows are larger, so watch the inline
   body cap.

7. **Exit.** Submitted rows are logged `submitted` in `batch-log.md`.
   Fetching and QC of the remainder are the normal `get-scenes` →
   `validate-scenes` flow, run afterward.

## Cost

Roughly doubles submissions for a chapter with groups (a small seed batch,
then the remainder) and adds one bounded wait. Step 1 is cheap and says
plainly when there is nothing to chain.

## Boundaries

- Calls the three scene skills exactly as documented, never altering how
  they work; does not fetch or QC the remainder batch.
- Does not auto-retry or decide fluke-versus-systematic on a seed failure;
  surfaces it and stops.
- Does not add, remove or rename manifest columns; group membership lives
  in `notes`, written by Mode 4a.
