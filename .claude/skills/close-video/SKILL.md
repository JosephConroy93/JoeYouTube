---
name: close-video
description: Closes out a finished video — reconciles batch-log.md statuses and writes the CLOSED footer, moves every disposable file (archive folders, .bak manifests, style previews after saving their exemplars, pilot/look-test folders, superseded references) into one <slug>/_archive/ with a byte count, and prints the remaining manual checklist. Never deletes. Use after publish (WORKFLOW Step 12); its --archive step is safe any time after finalize-scenes.
---

# close-video

Invocation: `close-video <series>/<slug> [--dry-run] [--step archive|log|all]`.
Layout: `.claude/conventions.md`. Executed by `scripts/close-video.ps1`.

## What it does

**log** (only after publish)
1. `claude/batch-log.md`: any row still `fetched` whose scene images are
   canonical on disk is marked `validated (n/n) — reconciled at close`;
   appends `CLOSED <date>`.
2. `video.md`: `status: closed`; warns if `published_id` is empty.

**archive** (safe after `finalize-scenes`)
1. For each style folder in `claude/style-previews/`, copy the first image
   to `content/styles/examples/<Style>.jpg` if no exemplar exists yet, and
   repoint any style-bible link into that preview folder.
2. Move into `<slug>/_archive/` (preserving relative paths):
   `scene-generation/_archive/` (or legacy `failed/`),
   `reference-images/_archive/` and any `*.failed-*` / `*.superseded-*`
   reference image, `claude/*.bak*`, `claude/style-previews/`,
   `claude/pipeline-pilot/`, `hook-tests/`.
3. Print files moved and total bytes.

**Both** end with the manual checklist: delete `_archive/` when sure;
confirm channel About copy; confirm the description pattern; add the
title to the competitor index; note the published id in
`voice-register.md`; add the video's rough costs (images, hook, voice share,
other) and total to `content/<series>/creator-costs.md`.

## Rules

- Nothing is deleted, ever. `_archive/` is the operator's to remove.
- Canonical files are never moved: `scene-generation/<scene_id>.jpg`,
  `reference-images/<Name>.jpg`, everything in `claude/` except backups and
  previews, `voiceovers/`, `hook/`, `thumbnails/`.
- `--dry-run` prints every planned move and edit without doing it. Run it
  first.

## Status

🟡 First real run is Pharaoh's Servant's close-out.
