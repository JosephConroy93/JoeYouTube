---
name: preview-style
description: Generates real, rendered comparison images for a small scene range in a candidate style from content/styles/style-bible.md, so a style can be judged by looking at it applied to real scene content before committing a project to it. Reads content_prompt from an already-written (possibly chapter-split) scene-prompts manifest, merges in the candidate style's STYLE/NEGATIVE block plus the universal-negatives preamble (same stitch generate-scenes uses), and defaults to fast/direct Gemini calls rather than the batch-log flow — real usage found direct calls are the right default for the handful-of-images scale a style preview actually is. Runs validate-scenes' QC against the result. Output is disposable — content/watcher-pov/<slug>/claude/style-previews/<StyleName>-scenes-<range>/, never scene-generation/ or the real manifest. Standalone skill (moved out of scene-prompter's Mode 5, 2026-09-10) for ad-hoc use directly between Joe and the primary session — no agent judgment involved, just a lookup, a text merge, and a generation call.
---

# Preview style — ad-hoc rendered comparison for a candidate style

Generates real images for a small handful of scenes in a named candidate
style, so a style choice can be judged by looking at actual output rather
than imagining it from prompt text. Joe's original framing: *"Scenes 1-15
on Style X for Script X — so I can make a decision how I think it looks
for that video."*

**Moved out of `scene-prompter`'s Mode 5 into its own skill (2026-09-10)**:
the job — look up `content_prompt`, merge in a style, generate, QC — never
needed agent-level creative judgment, and `scene-prompter` structurally
can't execute it anyway (no Bash in its tool list — confirmed by three real
failed dispatches the same day, each burning ~70-75k tokens on prep before
hitting the wall at the actual generation call). A plain skill, with full
tool access, is the right shape for this.

## Inputs

- **Project slug** (e.g. `pharaohs-servant`).
- **A named style** from `content/styles/style-bible.md` (e.g. `Trueline`).
- **A scene range** — specific `scene_id`s, not necessarily contiguous or
  within one chapter file. Find the right `scene-prompts/level-NN.md`
  file(s) via `scene-prompts.md`'s chapter index; a range spanning more
  than one chapter file just means reading more than one.

The manifest must already exist (`scene-prompter` Mode 2 must have run for
at least the chapters covering the requested range) — this skill never
segments a script or writes `content_prompt` itself, only reads it.

## What it does

1. **For each requested scene_id, take its `content_prompt` verbatim** and
   merge in the candidate style's STYLE/NEGATIVE block plus
   `style-bible.md`'s own "Universal negatives" preamble — the exact same
   three-piece stitch `generate-scenes`' "Building the request" section
   uses, just with an explicit style argument standing in for whatever (if
   anything) the manifest's own `style` column currently holds. **Never
   writes this merge back into the manifest** — the candidate style here
   is not a commitment, `scene-prompts.md`'s `style` column stays exactly
   as it was.
2. **Generate.** Defaults to **fast/direct individual `generateContent`
   calls**, not the `generate-scenes`/`get-scenes` batch-log flow — a
   style preview is typically 3-15 images, well below the scale where
   batch submission's async overhead earns its keep, and real usage
   (2026-09-10, three real style previews) confirmed direct calls are
   faster and simpler to reason about at this size. If a genuinely large
   preview range is ever needed, the batch-log flow is still available —
   submit via `generate-scenes` with the style argument override, fetch via
   `get-scenes`, same as production — but that's the exception, not this
   skill's default path. Same model selection as `generate-scenes`
   (`gemini-3.1-flash-image` at 2K for `illustrated` rows needing
   references, `gemini-3.1-flash-lite-image` for `text-card` rows), same
   positional reference-image binding.
3. **Run `validate-scenes`' QC against the result** — a style preview is
   still a real generation, worth checking for the same content failures
   (ignored negatives, unconstrained secondary characters) the
   prompt-hardening log already documents, not just eyeballed for "does
   the style look right." Failures get logged to
   `prompt-hardening-log.md` the same way, with the same "no automatic
   retry" discipline — report and stop, don't resubmit on your own
   initiative.

## Output

Real image files at
`content/watcher-pov/<slug>/claude/style-previews/<StyleName>-scenes-<range>/<scene_id>.jpg`
— one folder per style/range combination, so two or three candidate styles
for the same scenes sit side by side as actual images, not prompt text to
imagine from. **Never touches or overwrites** `scene-prompts.md`,
`batch-log.md`, or `scene-generation/` — this is disposable comparison
output, regenerable on demand.

**Running it again for a different style on the same range** is the normal
way to compare — each call produces its own folder.

## Once a style is chosen from comparison

That's a `scene-prompter` Mode 3 (REVISE) job, not this skill's — ask Mode
3 to set the real manifest's `style` column (a bare name, never expanded
text) to the winning style, for the whole project or a range. This skill
only ever produces throwaway preview images, never touches the production
manifest or the canonical `scene-generation/` output.

## What this skill does not do

- Does not segment a script or write `content_prompt` — reads an
  already-written manifest only.
- Does not commit a style to the manifest — that's a `scene-prompter` Mode
  3 job, done explicitly, after comparison.
- Does not retry a failed preview scene automatically — same "report and
  stop" discipline as `validate-scenes`.
