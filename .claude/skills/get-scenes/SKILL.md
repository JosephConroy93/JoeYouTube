---
name: get-scenes
description: Checks and fetches Gemini Batch API scene jobs that generate-scenes submitted. One status GET per batch-log.md row at `submitted`, or per explicit batch id, never a loop; a succeeded job's images are decoded to scene-generation/<scene_id>.jpg without overwriting anything and the row is set to `fetched`. Makes no judgment about image content.
---

# Get scenes — one check per pending batch

Layout, schemas and status words: `.claude/conventions.md`. Project path
`<series>/<slug>`. Driver:
`.claude/skills/generate-scenes/scripts/gemini-batch.ps1`.

## Prerequisites

- `claude/batch-log.md` has a row at `submitted`; otherwise say so and stop.
- `GEMINI_API_KEY` set per conventions.md.

## Run

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .claude/skills/generate-scenes/scripts/gemini-batch.ps1 `
  -Action status -Project <series>/<slug> [-BatchId batches/<id>]
  -Action fetch  -Project <series>/<slug> [-BatchId batches/<id>]
```

`status` reports; `fetch` reports and files. Each makes exactly one
`GET https://generativelanguage.googleapis.com/v1beta/{batch_id}` per row,
header `x-goog-api-key`, state read from `metadata.state`. To scope to a
scene-id list, pass the `-BatchId` of the row whose `scenes` cell covers
those ids (`chain-scenes` does this for its seed batch). `fetch -DryRun
-OutDir <dir>` writes images there and updates no row.

## Outcomes per row

- `BATCH_STATE_PENDING` or `RUNNING`: `checked_at` updated, status stays
  `submitted`. One line of output; run again later. Never loop, wait or
  background a poll.
- `BATCH_STATE_SUCCEEDED`: `status` prints READY with the result count.
  `fetch` reads `response.inlinedResponses.inlinedResponses[]`, each
  `{metadata.key, response.candidates[0].content.parts[].inlineData{mimeType,data}}`,
  and decodes every image to `scene-generation/<metadata.key>.jpg`, or to
  `<scene_id>.attempt-N.jpg` (next unused N, from 2) when that file already
  exists. Nothing is ever overwritten. The row becomes `fetched` with
  `fetched_at`; any result lacking an image part is named in `notes`.
- Any other terminal state (`FAILED`, `CANCELLED`, `EXPIRED`): the row
  becomes `failed` with the API error in `notes`. A submission-level
  failure, not QC; a fresh `generate-scenes` call is the operator's decision.

A batch id absent from the log, or a log in an older column layout, is
reported only; no row is written.

## Report

One line per batch: state, and for a fetch the count and file paths.
Nothing about what the images show.

## Boundaries

- No judgment on images; that is `validate-scenes`.
- No polling, waiting or backgrounding.
- No retries, resubmission or prompt changes.
