# Video production workflow

How a video gets made with the locked toolchain, from concept to close-out.
This file is the as-is process only. Schemas, folder layout and the
invocation contract are in [.claude/conventions.md](.claude/conventions.md);
the reasoning behind any step is in [CHANGELOG.md](CHANGELOG.md) and
[research/inventory.md](research/inventory.md); current project status is
[research/index.md](research/index.md)'s "Where we left off".

Every agent and skill takes the project path `<series>/<slug>` and reads
`content/<series>/series.md` and `content/<series>/<slug>/video.md`.
Update `video.md`'s `status` as each step completes.

Status: 🟢 run on a real video · 🟡 defined, not yet run as designed

## Toolchain

| Job | Tool |
|---|---|
| Research, titles, competitor data, comments, transcripts | VidIQ MCP (`vidiq_*`) |
| Emulating or checking a channel (dossier, style entry, format module) | `channel-farmer` (calls `style-farmer`, `/watch`, VidIQ, Gemini) |
| Competitor visual style frames | `style-farmer` |
| Script write / revise / score | `script-writer` agent + `.claude/formats/<format>.md` |
| Voiceover | ElevenLabs REST API via `generate-voiceover` (hosted ElevenLabs MCP for auditioning voices only) |
| Timing | `align-scenes` (TTS timestamps, or whisper) |
| Character/location bible, scene prompts | `scene-prompter` agent (bible once; prompts one chapter per generation loop) |
| Scene images | Google Gemini Batch API via `generate-scenes` → `get-scenes` → `validate-scenes` → `finalize-scenes`; `chain-scenes` for continuity groups; `preview-style` for style choice |
| Edit | DaVinci Resolve Studio via the `davinci-resolve` MCP server: `place-scenes` → `plan-ken-burns` → `apply-fusion` |
| Thumbnail | Gemini image generation; VidIQ for technical checks only |
| Close-out | `close-video` |

---

## Step 0 — Series setup (once per series) 🟡

To build a series around a channel worth emulating, run `channel-farmer`
first: it produces the style entry, the format module and a `series.md`
proposal this step then adopts.

Create `content/<series>/series.md` (schema in conventions.md): default
format, voice, style policy, chapter naming, mascot block, CTA policy,
staging path. Add series-level characters (a mascot) to
`content/<series>/mascot/character-bible.md` with reference images. Pick or
add a style in `content/styles/style-bible.md`; each style keeps one
exemplar image in `content/styles/examples/`.

## Step 1 — Concept and angle 🟢

1. Candidates come from a source book/PDF dropped into `content/<series>/`
   or from a real system worth a treatment. For each promising thread, try
   several framings (as a role / after an event / during a situation /
   every rank in a system / how it actually worked) and tag each with its
   **format** (`rank-ladder` Category A or B, `explainer`).
2. **Competitor-clash check** against
   `research/artifacts/competitor-titles-index.md` — clash on the specific
   angle, not the topic. Each channel section carries a pulled date; older
   than about a week, ask before re-polling `vidiq_channel_videos` (log
   every title pulled).
3. Check each survivor against live VidIQ outlier/breakout data for its
   specific topic. `vidiq_outliers`' `keyword` is a semantic match on the
   individual terms across titles and tags, not a phrase match: run one
   strict query per phrase (`requireAllTitleTerms: true`, e.g. "silk road")
   plus one or two narrower term clusters, never a single long string
   ("silk road caravan" returned RV caravans). Note which words are polluted
   by another meaning (caravan → RVs, embalmer → modern morticians) so Step 2
   avoids them in the title.
4. **Comment mining**: `vidiq_video_comments` (5 credits/call) on the 2–3
   strongest competitor videos; log which videos were mined in `concepts.md`
   so Step 3 never re-pulls them.
5. Write every candidate into `concepts.md` with a 50–100 word story-shape
   TLDR and its format tag. Record the pick and why.

Copyright: source books are sparks, never quoted or paraphrased into the
script; facts are independently verified in Step 3.

## Step 2 — Title 🟢

`vidiq_generate_titles` seeded with tracked competitors' real titles, then
`vidiq_score_title`; iterate to 90+.

## Step 3 — Research 🟢

Output: `content/<series>/<slug>/research-<slug>.md`, the script's sole
factual authority.

1. Check `content/SOURCES.md` before acquiring anything; propose paid
   sources with a stated justification.
2. `vidiq_video_transcript` (5 credits/call) on existing videos on the
   subject to find the well-trodden angle. Check
   `research/artifacts/transcripts/index.md` first; after any pull write a
   paraphrased breakdown there, never the verbatim transcript. If VidIQ is
   down or a video has no captions, the free fallback is local: `yt-dlp
   --skip-download --write-auto-subs` for captions, else `yt-dlp -f ba` for
   the audio and `whisper --model base`; delete the audio afterwards.
3. Comment mining, second use: what viewers keep asking or complaining is
   missing becomes beats.
4. Record sources used in `sources.md` (series-level unless `video.md`
   says otherwise) and in the central index.
5. **Hook fact**: one hard, specific, verifiable number for the first 30
   seconds. If none exists, record the gap explicitly.
6. Beats, scaled to format: rank-ladder A ≈ one beat per 60–90 s of
   runtime; rank-ladder B one entry per real tier with sourced structural
   facts plus illustrative composite beats; explainer one section per
   sub-question with one sourced example each.
7. **Fact-check section**: every uncertain fact flagged. `script-writer`
   treats these as binding.
8. **Treatment**: a 150–300 word start/middle/end compression appended as
   `## Treatment`. **Gate: the operator reads it and decides go/no-go.** A
   list of facts with no shape means find a stronger angle.

## Step 4 — Script 🟢

1. Optional delivery-style reference: reuse a cached transcript breakdown
   for register and structure only; say which part is being reused.
2. `script-writer` Mode 1 (WRITE) with the format from `video.md` →
   `claude/script.md` with handoff notes.
3. `script-writer` Mode 3 (SCORE): gates G1–G4 must pass; floors from the
   format module. Revise with Mode 2 until it passes. Lock.
4. Set `status: scripted`.

## Step 5 — Voiceover and timing 🟡 (new position: straight after script lock)

1. `generate-voiceover <series>/<slug>`: splits the script into segments,
   writes `claude/voiceover-segments/<slug>_voice_NN.txt`, calls ElevenLabs
   with the series voice, saves `voiceovers/<slug>_voice_NN.mp3` (raw, kept as source) plus the
   character-timestamp alignment, then normalises to **−16 LUFS, true peak
   ≤ −1.5 dBFS, 48 kHz, dual-mono stereo WAV** in `voiceovers/normalized/` (the only copy that
   goes on the timeline).
   Log the voice in `voice-register.md` and `video.md`.
2. Listen to one segment before generating the rest.
3. `align-scenes <series>/<slug>` runs **at the end of Step 8**, once every
   chapter's manifest exists (it needs all the `script_bookmark`s); it is
   listed here because the audio it needs exists from this point. With API timestamps no
   transcription is needed; whisper remains the fallback.
4. Set `status: voiced`.

Hook clips (Step 9) are cut to the measured narration beats, never
generated before the voiceover exists.

## Step 6 — Visual reference pass 🟡

Research covers what the script may *say*; nothing yet covers what a scene
may *show*. Scan the locked script for animals, garments, objects, building
decoration and anything else where "era-appropriate" is not precise enough
for an image model. For each, check the research file for its appearance;
if absent, do a sourced lookup (WebSearch/WebFetch — `scene-prompter` has
no web tools) and append a caveated visual-reference addendum to the
research file. Visual only: a contradiction with a narration claim is a
Step 3 gap, flag it back. Point `video.md`'s `visual_guardrails` at the
addenda.

## Step 7 — Bible and style 🟢 (once per video)

1. `scene-prompter` Mode 1 (DEFINE): lock every recurring **character,
   location and companion object** into `claude/character-bible.md`, with
   `claude/reference-prompts.txt`; render the reference images
   (`channel-farmer/scripts/style-test.ps1 -Prompts reference-prompts.txt`)
   into `reference-images/` and audit them against the bible.
2. Choose the style: `preview-style` renders a few real scenes in candidate
   styles; set `style` in `video.md`.
3. Set `status: prompted` once the bible and references pass.

## Step 8 — Scene prompts and generation, one chapter per loop 🟢

**Prompts are never written ahead of the images they learn from.** Each
chapter runs the whole loop before the next chapter's prompts exist, so a
failure found in chapter N is a rule in chapter N+1 rather than a revision
across files already written.

For each chapter, in order:

1. **Prompts**: `scene-prompter` Mode 2 for this chapter only. It re-reads
   the hardening log first, including every entry added since the last
   chapter, and writes the chapter file (≤25 scenes) plus index row; the
   first chapter also writes `claude/qc-checklist.md` (per-video specifics
   only). Visual gaps are flagged in `notes`, never invented.
2. **Submit**: `generate-scenes` for the chapter, or `chain-scenes` when the
   chapter has consistency-linked groups (same location or held pairing
   across separate requests; an already-validated image from an earlier
   chapter can be the seed).
3. **Fetch**: `get-scenes` (one status check; run again later if pending).
4. **Validate**: `validate-scenes` (four checks in 5–8-image subagent
   groups, writes `validated (n/m)`). The operator may review the images
   directly instead; either way the row gets `validated (n/m)`.
5. **Harden**: every failure gets a full entry in
   `content/prompt-hardening-log.md` and one line in the watch list of
   `content/prompt-hardening-rules.md`. A failure that recurs, or that the
   next chapter's scenes would obviously repeat, is **promoted** into the
   rules now, before step 1 of the next chapter.
6. **Fix**: a one-off render fluke → resubmit the scene id via
   `generate-scenes`; a prompt problem → `scene-prompter` Mode 3 on the
   failed rows, then resubmit. Nothing retries automatically. A chapter is
   closed when every row is validated.

The first chapter is also the video's pilot: look at its images before
writing chapter 2 at all, not only at the failures.

After the last chapter: `finalize-scenes` (one canonical `<scene_id>.jpg` per
scene, the rest to `_archive/`, `FINALIZED` footer), then `align-scenes`
(needs every chapter's `script_bookmark`s and the voiceover). Set
`status: generated`.

## Step 9 — Edit 🟢

All in Resolve Studio through the MCP server. **Verification rule** (conventions.md):
nothing is done until a rendered or measured artefact proves it.

1. `place-scenes`: decide fps, pre-render every visual to exact-frame
   clips, cut hook clips to the measured beats, author and import the FCP7
   XML, verify by readback and screenshot. Media is staged at the series
   `staging_path`, never inside OneDrive.
2. `plan-ken-burns` → `claude/ken-burns-plan.md`: Baseline motion on
   nearly every scene, Elevated on ≤10% with confirmed targets, FX
   suggestions capped at 5, Static only on text-cards, a black sweep on
   about 1 in 10 beat boundaries. **The operator edits the plan** — pacing
   and emphasis stay human.
3. `apply-fusion`: motion and particles from the plan; render-verify each
   effect once and drop any that is invisible.
4. Grade hook clips only (CDL matched by measurement, per `place-scenes`);
   the body stays ungraded.
5. SFX and beds from `content/sfx/` (search the metadata TSV, never the
   filenames; index a new pack with `index-pack.sh` first). Bake levels.
6. Render. Measure the render: integrated LUFS **and per-channel RMS**,
   frame spot-checks at hook, title cards and FX scenes. Watch it through.
   Set `status: edited`.

Automate the mechanical (sequencing, sync, loudness, export); keep the
editorial human — templated structure is a named inauthentic-content trigger.

## Step 10 — Thumbnail 🟢

After the edit, so a real frame or moment can be used.

- Template: white/very light background, one consistent protagonist with
  era-identifying detail, exaggerated emotion, 2–3 words readable at 100 px,
  one saturated accent, locked layout across videos.
- **Thumbnail text is a factual claim.** Check every candidate line against
  the research file's fact-check flags exactly as script lines are checked;
  where the research says "contested", the thumbnail may not resolve it.
  Prefer a differentiated fact the research supports over a competitor's
  stronger inaccurate hook. Text adds the stake, never restates the title.
- Generate in the video's style with the same reference images.
  `vidiq_score_thumbnail` is for blur/brightness only, never pass/fail.

## Step 11 — Publish 🟡

1. Channel identity check: name, About copy, icon/banner match the series
   (`content/<series>/mascot/watcher-concept.md` holds the copy for Watcher POV).
2. Description: citation list plus a "People & Sites Mentioned" section;
   disclose dramatised composites where the format uses them.
3. Title from Step 2, thumbnail from Step 10, chapters from the level
   callouts.
4. Record `published_id` and publish date in `video.md`; add the title to
   the competitor-titles index under the channel's own section.
   Set `status: published`.

## Step 12 — Close-out 🟡

`close-video <series>/<slug>`: reconciles `batch-log.md` statuses and writes
the `CLOSED` footer, moves every disposable (`_archive/` folders, `.bak`
manifests, style previews after their exemplars are copied to
`content/styles/examples/`, pilot and look-test folders, superseded
reference images) into one `<slug>/_archive/`, and prints the remaining
manual checklist. It never deletes; deleting `_archive/` after publish is
the operator's call. Set `status: closed`.

---

## Standing rules

- **Validate small before scale**: a few scenes, one segment, one chapter,
  before a full batch.
- **Accuracy is the product**: a gap in the research is information, not a
  prompt to improvise — this applies to scripts, prompts and thumbnails.
- **Costs in sterling.** Gemini ≈ £0.037 per 2K image (batch); ElevenLabs
  Creator ≈ £17/month ≈ £3.40 per 24k-character video.
- **Log every change to this file, an agent, a skill or a format** in
  `CHANGELOG.md` (one line plus the why) and commit it.
