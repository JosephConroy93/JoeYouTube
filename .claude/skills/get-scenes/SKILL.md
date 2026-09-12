---
name: get-scenes
description: Checks on and fetches results for Gemini Batch API scene-generation jobs previously submitted by generate-scenes. Reads a project's batch-log.md for rows with status=submitted, attempts exactly one status check per pending batch (never a poll loop — safe to invoke again later, any time), and for anything ready, decodes and files the images to scene-generation/<scene_id>.jpg, updating batch-log.md to status=fetched. Purely mechanical retrieval and filing — makes no judgment about image content or quality (that's validate-scenes' job). Split out from the original generate-scenes skill 2026-09-10 specifically so checking on a batch is never bundled with the act of submitting or waiting for one.
---

# Get scenes — check and fetch, one attempt per pending batch

Reads `content/watcher-pov/<slug>/claude/batch-log.md` for every row with
`status=submitted`, attempts one status check per row, and either logs a
"not ready yet" and moves on, or fetches and files the result. **Never
polls in a loop** — one invocation does one check per pending batch, then
exits. Invoke it again whenever it's next convenient (a minute later, an
hour later, next session) — there is no cost to checking too early beyond
one cheap API call, and no downside to checking late.

## Prerequisites

- `content/watcher-pov/<slug>/claude/batch-log.md` exists with at least one
  row at `status=submitted` (if there's nothing pending, say so and stop —
  nothing to do).
- `content/watcher-pov/<slug>/scene-generation/` exists (create it if not).
- `GEMINI_API_KEY` is set as a User environment variable, read fresh each
  call via `[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')`
  — never typed, echoed, or logged.

## Checking a batch — one GET, no loop

For each `batch-log.md` row at `status=submitted`:

```
GET https://generativelanguage.googleapis.com/v1beta/{batch_id}
Header: x-goog-api-key: $GEMINI_API_KEY
```

Read the `state` field. Two outcomes, nothing else:

**Outcome 1 — still pending** (`BATCH_STATE_PENDING` or
`BATCH_STATE_RUNNING`): update that row's `last_checked_at` to now, leave
`status` as `submitted`, move to the next pending row (or exit if this was
the only one). **This is not a failure and not worth narrating at length**
— a one-line summary ("batch X still running, checked at 14:32") is
enough. Don't loop, don't wait, don't background a poll — just check once
and stop.

**Outcome 2 — terminal state** (`BATCH_STATE_SUCCEEDED`,
`BATCH_STATE_FAILED`, `BATCH_STATE_CANCELLED`, or `BATCH_STATE_EXPIRED`):
proceed to "Retrieving and filing results" below for `SUCCEEDED`; for
anything else, log the failure state plainly against that row (a new
`status=submit-failed` value, with the reason if the API gave one) and
stop — this is a submission-level failure, not a content QC failure, and
isn't `validate-scenes`' concern.

## Retrieving and filing results

**Results are not at `response.inlinedResponses` as a flat array — they're
one level deeper: `response.inlinedResponses.inlinedResponses[]`.**
Confirmed directly against a real response, not a docs paraphrase — the
single easiest mistake to make parsing this. Each element:

```
{
  "metadata": { "key": "<scene_id>" },
  "response": {
    "candidates": [{ "content": { "parts": [
      { "inlineData": { "mimeType": "image/jpeg", "data": "<base64>" } }
    ]}}]
  }
}
```

Match `metadata.key` back to the scene_id. For each image:

- **If `content/watcher-pov/<slug>/scene-generation/<scene_id>.jpg` does
  not already exist**, decode and save it there directly — the normal,
  first-time case.
- **If it already exists** (this is a deliberate resubmission after an
  earlier `validate-scenes` failure), save as
  `<scene_id>.attempt-<N>.jpg` instead, incrementing N past whatever
  attempt files already exist for that scene_id — **never overwrite a
  prior file**. Leave the existing canonical `<scene_id>.jpg` in place;
  whoever reviews the new attempt decides whether it should replace the
  canonical file (a manual step, not this skill's call).

For a job small enough to submit inline, results come back embedded in the
same `GET` response that shows `SUCCEEDED` — no separate download call
needed. A Files-API-based submission may return a `responses_file_name`
requiring a separate
`download/v1beta/{responses_file_name}:download` call instead — not yet
tested in this project; verify the real response shape when that path is
first actually used.

Once every scene in the batch is filed, update that `batch-log.md` row:
`status=fetched`, `fetched_at` set to now. List the filed scene_ids in your
own summary back to whoever's driving the session, but keep it short — a
count and the file paths, not a narration of each image.

## What this skill does not do

- **No judgment about image content, quality, or correctness of any
  kind** — that's `validate-scenes`, run separately, afterward, against
  rows at `status=fetched`.
- **No polling loop, no waiting, no backgrounding.** One check per pending
  row, per invocation. If a batch is still running, the right move is to
  invoke this skill again later — there is no in-skill mechanism for
  "wait until ready."
- **No retries, resubmission, or prompt changes** — a `submit-failed`
  terminal state just gets logged; deciding what to do about it belongs to
  whoever's driving the session (likely a fresh `generate-scenes` call).
