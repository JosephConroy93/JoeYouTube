---
name: finalize-scenes
description: Closes a video's scene-generation pass once every batch-log.md row is validated, failed or superseded. Confirms exactly one <scene_id>.jpg per manifest row, sweeps every other file in scene-generation/ and reference-images/ into their _archive/ folders, and appends the FINALIZED footer. File layout only; no judgment about image content.
---

# Finalize scenes — one canonical file per scene

Layout, schemas and status words: `.claude/conventions.md`. Project path
`<series>/<slug>`.

## Gate

Every `claude/batch-log.md` row is `validated (n/m)`, `failed` or
`superseded`. A row still `submitted` or `fetched`: stop and name it. A
scene id listed as failed in a `validated` row's `notes` must appear in a
later row that validated it, or that row must be `superseded`; otherwise
stop and name the id.

## Canonical set

One file per manifest row, `scene-generation/<scene_id>.jpg`, ids read
from every chapter file the index names, not from the folder. Whoever fixed
a failure has already promoted the winning attempt to that bare name; this
skill never chooses between attempts.

## Steps

1. Build the scene-id set from the manifest.
2. Confirm `<scene_id>.jpg` exists for each id. Any missing: stop, list
   them, move nothing.
3. Move every other file in `scene-generation/` (`.attempt-N.jpg`,
   `.superseded-*.jpg`, manual-edit sources, strays) into
   `scene-generation/_archive/`. Never touch a canonical file.
4. Move every file in `reference-images/` that is not a bare `<Name>.jpg`
   (`*.failed-*`, `*.superseded-*`, test renders) into
   `reference-images/_archive/`.
5. Append `FINALIZED <date>` to `batch-log.md`.

Moves only; nothing is deleted. Older videos use `scene-generation/failed/`
in place of `_archive/`; leave that as it is.

## Report

Canonical count against manifest count (must match), files archived per
folder (a count; names only for a handful), and the footer line. The
operator then sets `video.md` `status: generated`.

## Boundaries

- No image judgment (`validate-scenes`); no promotion between attempts.
- No deletion; `_archive/` belongs to `close-video` and the operator.
- Whole-video, once; never per chapter.
