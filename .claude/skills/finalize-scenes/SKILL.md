---
name: finalize-scenes
description: Once a project's entire scene-generation pass is fully validated, archives every non-canonical file out of scene-generation/ (attempt-N resubmissions, .superseded-*.jpg originals, any other one-off intermediate like a manual image-edit source) into scene-generation/failed/, leaving only one <scene_id>.jpg per scene — so the folder is directly importable into DaVinci as a whole, no manual sorting needed. Pure archival, no judgment about image content (that's validate-scenes' job, already done by the time this runs). Use once a video's batch-log.md shows every row validated, right before Step 8 editing begins. Universal across projects, not Pharaoh's-Servant-specific.
---

# Finalize scenes — archive non-canonical files, don't copy canonical ones

Solves the opposite problem to a "promote the winners" step: instead of
copying the small number of accepted files out to a clean folder, this
moves the small number of *rejected/superseded* files out, leaving the
already-larger set of canonical files untouched in place. Cheaper and
lower-risk than a copy-out — the canonical files never move, so there's no
window where a botched destination is the only copy.

**Why this exists**: `get-scenes` saves a resubmission as
`<scene_id>.attempt-N.jpg` and explicitly never overwrites a prior file;
this project's own QC-fix convention (see `prompt-hardening-log.md`)
archives a superseded original as `<scene_id>.superseded-<reason>.jpg`
before promoting a fix to the bare canonical name; and an occasional
manual image-edit (done outside the pipeline entirely, e.g. a direct
Syntx edit) leaves its own source file on disk under an ad hoc name. None
of this is ever deleted, by design — it's the raw material behind
`prompt-hardening-log.md`'s patterns. But it means `scene-generation/`
accumulates real cruft: Pharaoh's Servant's folder held 208 files for 198
scenes. A folder like that can't just be pointed at DaVinci's media pool
import as-is.

## Prerequisites (check before starting, don't assume)

- **`content/watcher-pov/<slug>/claude/batch-log.md` shows every row at
  `validated` (or `validated, Joe-reviewed` / `validated, quick-QC`) —
  no row still at `submitted` or plain `fetched`.** If any row isn't
  validated yet, **stop and say so** — this isn't `finalize-scenes`'
  call to make; hand back to `get-scenes`/`validate-scenes` first. Running
  this mid-QC risks archiving a file someone still needs to compare
  against during review.
- The project's full expected scene_id set is known — read
  `content/<series>/<slug>/claude/scene-prompts.md`'s chapter index (every
  `scene_id` across every chapter file), not just whatever happens to be
  sitting in `scene-generation/` already.

## What counts as canonical

Exactly one file per `scene_id`, named `<scene_id>.jpg` — nothing else.
This is the same convention `get-scenes` and every QC-fix entry in
`prompt-hardening-log.md` already follow; this skill doesn't invent a new
naming rule, it just enforces the one already in use.

## The move

1. List every file in `content/<series>/<slug>/scene-generation/`.
2. For each `scene_id` in the manifest, confirm `<scene_id>.jpg` exists.
   **If it doesn't, stop and flag that scene_id plainly rather than
   silently leaving a gap** — a missing canonical file means something in
   the QC/promotion process didn't finish, and that's worth surfacing
   before the folder gets treated as import-ready.
3. **Everything else in the folder — every file that isn't an exact
   `<scene_id>.jpg` match for a real scene_id — gets moved**, not copied,
   into `content/<series>/<slug>/scene-generation/failed/` (create it if
   it doesn't exist). This covers, without needing to special-case any of
   them individually: `attempt-N.jpg` files, `.superseded-*.jpg` files,
   and any other one-off intermediate (a manual-edit source file with its
   own ad hoc name, a stray test render) — if it's in the folder and it
   isn't a real scene's canonical file, it's cruft relative to a DaVinci
   import and belongs in `failed/`.
4. **Never touch a `<scene_id>.jpg` file itself.** The canonical file is
   always assumed correct at this point — by the time a scene reaches
   `validated`, whoever fixed a failure has already promoted the right
   attempt to the bare canonical name (the standing convention this
   project already uses by hand, e.g. Pharaoh's Servant's `043`: crown fix
   promoted to `043_cup-bearer-trusted-completely.jpg`, flawed original
   archived as `.superseded-wrong-crown.jpg`). This skill doesn't
   re-verify that judgment call, only acts on the file layout it produced.

## Reporting back

A short summary, not a per-file narration: how many canonical files were
confirmed present, how many files were archived to `failed/` (a bare
count is enough; list filenames only if there's a small handful), and any
missing-canonical flags from step 2. State the folder is now import-ready
for DaVinci's media pool once the count matches the manifest's scene
total exactly.

## What this skill does not do

- Does not judge image content or re-open a QC decision — that's
  `validate-scenes`, already run before this skill has anything to do.
- Does not delete anything — `failed/` is a move destination, not a
  trash can. The archived files remain the raw material behind
  `prompt-hardening-log.md`'s patterns and stay on disk indefinitely.
- Does not run mid-project or per-chapter — this is a whole-video,
  end-of-QC step, run once right before Step 8 editing begins.
- Does not decide which attempt is canonical when a scene has multiple —
  that promotion decision already happened (by whoever resolved the QC
  failure) before this skill ever runs.
