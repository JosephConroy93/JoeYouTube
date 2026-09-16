---
name: generate-scenes
description: Builds and submits scene-generation requests to the Gemini Batch API for one chapter of a video's scene manifest, or an explicit scene-id list. Stitches each row's content_prompt with its named style-bible block and the universal negatives, attaches reference images positionally, submits one job per model (split under the inline cap), logs every job to batch-log.md at `submitted`, and stops. Never waits, fetches or checks results.
---

# Generate scenes — submit only

Layout, schemas and status words: `.claude/conventions.md`. Project path
`<series>/<slug>`. Driver: `scripts/gemini-batch.ps1` in this folder,
shared with `get-scenes`.

## Prerequisites

- `claude/scene-prompts.md` lists the chapter file. Chapter filenames come
  from that index, never from a naming pattern. Only `written` chapters
  have rows.
- Every selected row has a `content_prompt` and a bare style name in
  `style`. An empty `style` means stop and ask the operator; never invent
  one.
- Every reference named in a row's `characters_present / reference_images`
  cell has an audited file in `reference-images/` (or, for a generated-scene
  reference, its canonical `scene-generation/<scene_id>.jpg`).
- `content/prompt-hardening-rules.md` read before submitting or
  resubmitting any prompt.
- `python .claude/skills/generate-scenes/scripts/check-manifest.py <series>/<slug> --chapter <file>`
  reports no FAIL. A FAIL goes back to `scene-prompter` Mode 3; WARN lines
  are the driving session's call.
- Every `[[ID]]` token in the selected rows has a block in
  `claude/cast.md`; every selected row has a `content_prompt` (the chapter
  is `written`, not `beats`).
- `GEMINI_API_KEY` set per conventions.md. The script reads it; never echo
  it or write it anywhere.

## Selecting what to submit

Candidates are `written` chapters, in index order, with no `batch-log.md`
row yet.

- No argument: the next candidate chapter.
- "next N": the next N candidates, one script call each.
- "rest": every candidate, one script call each.
- An explicit scene-id list (full id or 3-digit prefix, any chapter):
  `-SceneIds`; `-Chapter` is then optional (resubmits use this form).

No candidates: say so and stop.

## Run

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .claude/skills/generate-scenes/scripts/gemini-batch.ps1 `
  -Action submit -Project <series>/<slug> -Chapter <file> [-SceneIds 012,013] [-Notes "..."]
```

A submit appends to `batch-log.md`: never run one while a `validate-scenes`
agent is writing that file, or the new row is lost under its rewrite.

**Always wait for the batch (hard rule).** A slow or stalled batch is waited
out, however long it takes (the API allows up to 24 hours); never cancel it
to go faster. `-Direct` (one interactive `generateContent` call per row, about
twice the batch price, saved as `fetch` would and logged at `fetched` with
`batch_id` `direct`) runs only when the operator says so in chat, for the
rows they name.

`-DryRun -OutDir <dir>` writes the request bodies and posts nothing; use it
on a new chapter shape or after a manifest edit. `-Action expand` prints
each selected row's prompt after block expansion, nothing else.
References are shrunk in memory to a 1376 px long edge before inlining
(`-RefMaxPx`, 0 to send them as on disk): a chapter fits one or two jobs, the
model's per-image token budget is fixed so cost is unchanged, and identity
measured equal to full-size references. `-Model` and `-Resolution`
override every selected row (escalation only). `-Root` overrides the
project root (default: four levels above the script).

## What the script does

Per row, one request. `contents[0].parts` is one `text` part followed by
one `inline_data` part (base64 JPEG or PNG) per reference, in the cell's
`image1, image2...` order; the prompt's "first/second attached reference
image" phrasing is the only binding, so order is everything. About four
references is the practical ceiling, five on the pro model. Text-card rows
carry no references.

Text = `content_prompt` with its `[[ID]]` tokens expanded (block text,
attachment ordinal from the reference cell, the blocks' guards as one
preservation sentence, then `_closing`; rules in conventions.md) +
`STYLE: <style block>` + `NEGATIVE: <style
negatives>` + the style bible's universal negatives, each style looked up
once per run. `generationConfig` = `responseModalities [TEXT, IMAGE]` and
`imageConfig.imageSize`. `metadata.key` = `scene_id`, the only link from a
result back to its row.

Model and resolution: `illustrated` uses `gemini-3.1-flash-image` at 2K;
`text-card` uses `gemini-3.1-flash-lite-image` at 1K; `gemini-3-pro-image`
only via `-Model` after a review calls for escalation. Lite (1K only, ~⅓ the price;
Google lists up to 14 reference images, not yet tested with references in
this pipeline) may also be chosen per row via a `model`
note in `notes` for medium/close character beats with simple backgrounds in
flat cartoon styles; never for establishing shots, crowds, maps or fine
props (validated on Eggline, see the Explainer Boss dossier). Flash at 1K
sits in the same bracket: same style, ~half the 1080p sharpness of 2K, no
sharper than lite under a Ken Burns push — use it on the same shot types
only. One model per job,
so a mixed chapter is at least two jobs. Bodies are split at 14 MB (inline
cap 20 MB); a single row over 14 MB aborts naming the row, so shrink its
references. Reference files of 2 MB and up force several small jobs per
chapter.

Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:batchGenerateContent`,
header `x-goog-api-key`, body
`{"batch":{"display_name":"<slug>-<chapter>-<range>[-partN]","input_config":{"requests":{"requests":[{"request":{...},"metadata":{"key":"<scene_id>"}}]}}}}`.
Requests in a job share nothing; every prompt is self-contained.

Each job appends one `batch-log.md` row (schema in conventions.md):
`batch_id` = the response `name`, `scenes` = chapter and range, `model`,
`requested_at` in UTC, `status` `submitted`, `notes` = resolution, styles,
part n/m, and any `-Notes` text. The file is created with its header when
absent. A log in an older column layout refuses new rows; start a new log.

Then stop. Fetching is `get-scenes`; QC is `validate-scenes`.

## Cost

Batch rate (50% off list, verified against Google's pricing page): flash-image
about £0.039 per 2K image, £0.026 per 1K; flash-lite-image about £0.013 per
image, **1K only** (a 2K request is rejected); pro-image about £0.052 per
1K/2K. A reference image costs about £0.0002 per request whatever its pixel
size (fixed per-image token budget). A resubmission pays again.

## Boundaries

- Does not write or revise prompts, choose a style, or touch the style
  bible or the hardening log.
- Does not wait, poll, fetch or QC.
- Does not retry. A resubmission is a fresh, deliberate call with
  `-SceneIds`, decided after `validate-scenes` reports.

## Test status

Real POST, log append, dry-run
submission, status, fetch and the log-row updates are exercised.
