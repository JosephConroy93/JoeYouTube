---
name: preview-style
description: Renders a small set of an existing manifest's scenes in a named candidate style from the style bible, via direct Gemini calls, so a style can be judged on real scene content before a video commits to it. Output is disposable and never touches the manifest, batch log or scene-generation folder. Use when comparing candidate styles for a video, or checking one before scene-prompter locks it in.
---

# Preview style — rendered comparison for a candidate style

Layout, manifest schema and credentials: `.claude/conventions.md`.

## Inputs

- Project path `<series>/<slug>`.
- A style name from `content/styles/style-bible.md`.
- Scene ids, not necessarily contiguous or within one chapter file.

The manifest must already exist for the chapters covering those ids; this
skill reads `content_prompt`, never writes it.

## Procedure

1. **Locate rows.** Read `claude/scene-prompts.md`'s index to find which
   `scene-prompts/<chapter>.md` file holds each requested id; a range
   spanning chapters just means reading more than one file.
2. **Stitch the request** exactly as `generate-scenes`' "Building the
   request" section: the row's `content_prompt` verbatim, then the candidate
   style's STYLE and NEGATIVE blocks from the style bible, then the bible's
   universal-negatives preamble, as one text part. The candidate style
   stands in for whatever the row's `style` column holds; the manifest is
   not edited. Attach reference images positionally, in prompt order.
3. **Generate** with one direct `generateContent` call per scene — not the
   batch flow; a preview is a handful of images. Use the model and
   resolution `generate-scenes`' model table assigns to the row's
   `scene_type`. Read `GEMINI_API_KEY` fresh from the user environment;
   never print or log it.
4. **Write** each image to
   `content/<series>/<slug>/claude/style-previews/<Style>-scenes-<range>/<scene_id>.jpg`.
   One folder per style/range pair; re-running for another style is the
   normal way to compare.
5. **QC by hand.** Apply `validate-scenes`' four checks (scene match,
   character consistency, major era violations only, nothing malformed) plus
   the text-card exact-text rule to each image yourself, and say in the
   report that this is a manual application of that checklist: no
   `batch-log.md` rows exist for a preview, so the skill is not invoked.
6. **Log fails** to `content/prompt-hardening-log.md` in its existing entry
   format. Report and stop; no automatic retry.

## Boundaries

- Never touches `scene-prompts.md`, any chapter file, `batch-log.md` or
  `scene-generation/`; output is disposable and regenerable.
- Never segments a script or writes `content_prompt`.
- Committing a style is not this skill's job: set `style` in `video.md`,
  then run `scene-prompter` Mode 3 to populate the manifest's `style` column
  with the bare name.
