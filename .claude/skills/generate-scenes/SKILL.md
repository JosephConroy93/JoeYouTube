---
name: generate-scenes
description: Builds and submits scene-generation requests to the Google Gemini Batch API — request/submit only, one chapter (or an explicit N-chapter/"rest" instruction) per call, always exactly one batch job. Stitches each request from a row's content_prompt column, the style named in its style column (looked up in content/styles/style-bible.md), and that file's own universal-negatives preamble — the manifest never stores a pre-merged prompt. Logs the submission to a per-project batch-log.md and stops — does not wait, poll, fetch results, or QC anything (split 2026-09-10 into three skills at exactly that boundary: this one submits, get-scenes fetches, validate-scenes checks). Use once scene-prompter's Mode 2 has written at least one chapter and character reference images are generated and audited. Universal across projects, not Pharaoh's-Servant-specific.
---

# Generate scenes — request and submit only

Builds the stitched Gemini request for one chapter's rows (or an explicit
range) and submits it as a single Batch API job. **Does not wait for the
result, fetch it, or check it** — that's `get-scenes` and `validate-scenes`,
deliberately separate skills since 2026-09-10. This skill's job ends the
moment the batch is submitted and logged.

**Why split this way**: the single combined skill used to submit a batch,
then sit in a backgrounded poll loop waiting for it, then fetch and QC the
result, all as one operation. Joe's call: *"I don't really like the idea
that we request and then poll."* Splitting at exactly that boundary means
submitting a batch is now a small, fast, cheap operation you can fire and
walk away from — checking on it later is a separate, equally small,
independently-repeatable operation (`get-scenes`), and neither one has to
hold a long-running wait open.

## Prerequisites (check before starting, don't assume)

- The manifest exists and is chapter-split: `scene-prompts.md` (a short
  index — shared front matter, era-anchoring negative, character legend, a
  table mapping each `scene-prompts/level-NN.md` file to its scene range
  and `written`/`planned` status) plus the chapter files themselves, 25
  scenes max each. Only `written` chapters have real rows to submit.
- Each row you're submitting has a populated `content_prompt` column and a
  **populated `style` column** (a bare name from
  `content/styles/style-bible.md` — never expanded STYLE/NEGATIVE text; see
  `scene-prompter.md` Mode 2's "Style — a reference, never materialized
  full text"). **An empty `style` column is expected and correct** while
  style is still being decided — **stop and say so plainly** rather than
  inventing or guessing one. The fix is asking Joe which style to use, or a
  Mode 3 (REVISE) pass that populates `style` — not this skill's call.
- All bible characters referenced by the rows you're submitting are already
  marked audited/PASS with real files in `reference-images/`.
- **`content/watcher-pov/prompt-hardening-log.md` — read it before writing
  or resubmitting a single prompt.** Any promoted fragment there is a
  known, confirmed failure mode; don't let a scene re-trigger something
  already documented and fixed once.
- `GEMINI_API_KEY` is set as a User environment variable. **Read it fresh
  each call via `[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')`
  — never type, echo, log, or paste the actual key value anywhere,
  including into a batch request file saved to disk.**
- `content/watcher-pov/<slug>/claude/batch-log.md` exists (create it with a
  header row if not — see "Logging the submission" below).

## Choosing what to submit

Mirrors `scene-prompter` Mode 2's own batching argument — same mental
model in both places. Cross-reference `scene-prompts.md`'s chapter index
(`written` chapters) against `batch-log.md` (chapters that already have a
`submitted`/`fetched`/`validated` row) — the candidates are `written`
chapters with no batch-log entry yet, in order.

- **No argument** → submit just the next one candidate chapter.
- **"next N"** → the next N candidate chapters, as N separate batch
  submissions (one chapter = one batch job, never merged — see "Batch
  sizing" below), not one combined job.
- **"rest" / "remaining" / "all"** → every candidate chapter, same way.

If there are no candidate chapters (nothing `written` yet, or everything
`written` already has a batch-log entry), say so and stop — don't invent
work.

## Model selection

Default to **`gemini-3.1-flash-image`** (Nano Banana 2) for every
`illustrated` row needing character references — up to 4 reference images
per call, and this project's own consistency testing found reference
conditioning reliably holds identity at this tier, including across
significant pose/aging changes. Don't switch models mid-project without a
reason; consistency matters more than optimizing each scene's cost
individually.

**`gemini-3.1-flash-lite-image`** (no character-reference support, cheapest
tier) is the right choice specifically for `text-card` rows, which never
carry a reference image anyway.

**`gemini-3-pro-image`** (up to 5 references, highest cost) is a fallback
for a scene that keeps failing QC on a character-reference-related item —
not a default, a targeted escalation raised by whoever reviews
`validate-scenes`' output, not something this skill reaches for itself.

**Resolution: 2K by default, confirmed via a real 1K-vs-2K comparison
(2026-09-09)**. Real cost delta is trivial (2K uses exactly 1.5x the image
tokens of 1K: ~5.0p/image at 1K vs. ~7.5p/image at 2K — about +£3 total on
a 250-scene video). Two real reasons to prefer 2K: (1) crowd/multi-figure
scenes showed genuinely crisper facial linework and denser backgrounds at
2K in direct comparison; (2) 1K's native 1376×768 output is already below a
1080p delivery frame *before* any Ken Burns zoom. **Text-card rows are the
one confirmed carve-out** — zero legibility/quality difference found
between 1K and 2K, so `gemini-3.1-flash-lite-image` text-cards can stay at
1K.

**One caveat, not yet resolved**: a reference-free single-subject prompt
produced a duplicated-subject failure at 2K in one test (n=1, likely
ordinary variance, not confirmed as resolution-linked). Watch for this on
reference-free prompts; log a recurrence to `prompt-hardening-log.md`.

## Reference-image binding — positional stays the standard, confirmed 2026-09-09

Checked directly against Google's own docs and a live test: **there is no
structured field to bind a reference image to a character by name or ID.**
`contents.parts` has no image-ID/role concept — binding is ordinal.
Google's own prompting guide phrases multi-image references positionally
("the first image... the second image"), confirming this is the intended
pattern, not a workaround.

**Positional phrasing stays the default**: "the person shown in the first
attached reference image," matching attachment order exactly. A bare
character name in the prompt text also worked in the same live test — safe
as *reinforcement* alongside positional phrasing, never as a substitute,
since there's no structural guarantee behind it.

**Multi-character cap**: up to 4 references on NB2, 5 on Pro. A scene
needing more than that is a composition problem to flag, not something
this skill works around.

## Building the request — the stitch happens here, not in the manifest

**This skill assembles the final prompt text at submission time, for every
single request.** `scene-prompts.md` never stores a merged, style-inclusive
prompt — that re-creates the exact "expensive to update everywhere"
problem `content_prompt` was built to solve. The stitch is three pieces,
always in this order:

1. **That row's `content_prompt`** — the real scene content.
2. **The style named in that row's `style` column, looked up in
   `content/styles/style-bible.md`** — its STYLE prose block and its own
   NEGATIVE block, verbatim.
3. **`content/styles/style-bible.md`'s own "Universal negatives" preamble**
   — content-correctness rules that apply regardless of which style was
   looked up in step 2 (currently: exactly one instance of the subject, no
   duplicated/mirrored figures). Append this every time, even if step 2's
   style already has its own extensive negative list.

Concatenate 1 + 2 + 3 into one `text` part:

```json
{
  "contents": [{
    "parts": [
      { "text": "<content_prompt> STYLE: <looked-up style block> NEGATIVE: <looked-up style negative> <universal negatives preamble>" },
      { "inline_data": { "mime_type": "image/jpeg", "data": "<base64 of reference image 1>" } },
      { "inline_data": { "mime_type": "image/jpeg", "data": "<base64 of reference image 2, if any>" } }
    ]
  }],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": { "imageSize": "2K" }
  }
}
```

Reference images attach **in the same order `content_prompt` refers to
them positionally** — get the order right here or the positional phrasing
in the prompt describes the wrong image. `text-card` rows and any row with
an empty `characters_present / reference_images` cell carry no
`inline_data` parts — text-only request.

**Do the same style-block lookup once per batch submission, not once per
row** — every row sharing a `style` value needs identical looked-up text,
so resolve it a single time and reuse it across the whole batch.

## Submitting a batch — always exactly one job

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:batchGenerateContent
Header: x-goog-api-key: $GEMINI_API_KEY
Body:
{
  "batch": {
    "display_name": "<slug>-<chapter>-<range>",
    "input_config": {
      "requests": {
        "requests": [
          { "request": { <the request object above> }, "metadata": { "key": "<scene_id>" } },
          ...
        ]
      }
    }
  }
}
```

**`metadata.key` must be the scene's `scene_id`** — this is the only thing
that maps a batch result back to the right manifest row, confirmed working
correctly in the 2026-09-09 pilot (all keys came back correctly matched).

**Inline body cap: 20MB.** Check the assembled body size before submitting.
**First real data point, 2026-09-10** (`chain-scenes`' first real
invocation, Pharaoh's Servant level-02): 12 illustrated requests, several
carrying 2 reference images (a character plus a `chain-scenes` location
reference), totalled 23.55MB unsplit — over the cap on a chapter smaller
than the ~16-25-request range this was flagged untested at. **The
pragmatic fix used, not the Files API**: split into multiple smaller inline
submissions (~14MB target per chunk, real headroom under the cap, not
cutting it close) rather than switching upload mechanisms — simpler, nothing
new to validate, and `chain-scenes` already submits a chapter's remainder as
a separate batch from its seeds, so one more split is a small extension of
a pattern already in use, not a new one. **If a body approaches or exceeds
20MB, split into multiple same-mechanism submissions first** — reach for
the Files API path (upload a JSONL file of requests, reference it in
`input_config` instead of inlining `requests.requests`) only if splitting
alone isn't enough (e.g. a single request's own reference images are large
enough to blow the cap on their own) — that path is still genuinely
untested end-to-end in this project.

**One model per batch job** — don't mix Lite and NB2 requests in a single
submission (a chapter with both `illustrated` and `text-card` rows needs
two separate submissions, one per model).

**Every request in a batch is fully independent** — no shared context,
style inference, or bleed between requests in the same job. This is *why*
every prompt has to stay fully self-contained regardless of batch vs.
single-call — batching is purely a submission mechanism.

## Logging the submission

Append one row to `content/watcher-pov/<slug>/claude/batch-log.md`
immediately after a successful submission (create the file with this
header if it doesn't exist):

```
| batch_id | chapter(s)/range | requested_at | status | last_checked_at | fetched_at |
|---|---|---|---|---|---|
```

Fill `batch_id` with the `name` field from the submit response (e.g.
`batches/xxxxxxxx`), `chapter(s)/range` with the chapter file and scene_id
range submitted, `requested_at` with the current UTC time, `status` with
`submitted`, and leave `last_checked_at`/`fetched_at` blank. **This row is
the only durable record connecting a batch job to its scenes** — `get-scenes`
and `validate-scenes` both read it, and a session interrupted right after
submission can recover from this row alone rather than needing to
resubmit.

**Then stop.** No waiting, no polling, no fetching, no QC — hand off to
`get-scenes` (whenever it's next convenient to check) and `validate-scenes`
(once fetched). If several chapters were submitted in one "next N"/"rest"
call, log one row per chapter/batch, not one combined row.

## Batch sizing — one chapter file = one batch submission

The 2026-09-09 pilot validated the *mechanism* at 4 requests (14.1 minutes,
0/4 failures) — it did not validate throughput or reliability at anything
approaching a real 150-300 scene manifest. **Don't assume turnaround
scales linearly, and don't assume one giant batch is safe just because a
tiny one worked.** One chapter file (≤25 scenes, per the 2026-09-10
manifest split) is the concrete submission unit — never a full-manifest
single submission — at least until a real mid-size batch (a few dozen
requests) has been run and its timing/reliability logged for the next
session to build on.

## Cost

At batch rate (50% off standard), NB2 at 1K is **~£0.025/image** (~$0.0335,
converted at the day's real rate — **always report costs in sterling, per
CLAUDE.md**); add a fraction of a penny per attached reference image
(confirmed tokenization: ≤384px reference images cost 258 tokens each). A
45-scene manifest at this rate is roughly **£1.10**; a 250-scene manifest
roughly **£6.20**. A resubmission after a `validate-scenes` failure costs
the same per-image rate again — there's no automatic multiplication built
into this skill anymore (no automated retry loop; see `validate-scenes`),
but a human choosing to resubmit several failed scenes should still expect
to pay for each resubmission.

## What this skill does not do

- Does not write prompts, define characters, or make creative judgment
  calls about scene content — that's `scene-prompter`'s job.
- Does not decide which style a project uses — reads whatever `style` name
  `scene-prompter` wrote into the manifest (or stops and asks if that
  column is empty).
- Does not wait for a batch, fetch its results, or check them — see
  `get-scenes` and `validate-scenes`.
- Does not retry anything automatically. A resubmission after a failure is
  a fresh, deliberate invocation of this same skill, decided by whoever
  reviewed `validate-scenes`' report — not something this skill triggers
  on its own.
- Does not touch `content/styles/style-bible.md` or
  `prompt-hardening-log.md`'s "promotion" review pass.
