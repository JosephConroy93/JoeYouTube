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
| Animated hook | Veo 3.1 via the Gemini API, `generate-hook` (from chapter 1's validated stills) |
| Cast sheet, beat sheet, prompts | cast sheet by hand (Step 6); `scene-prompter` beat sheet (Step 7); `write-prompts` by the driving session (Step 8) |
| Scene images | Google Gemini Batch API via `generate-scenes` → `get-scenes` → `validate-scenes` → `finalize-scenes`; `preview-style` for style choice |
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

## Step 6 — Cast sheet 🟡 (five minutes, hard cap)

Write `claude/cast.md` from the research file's visual notes and the
script: one line per figure who recurs (`YOU-L1` … per rung stage, then
at most three others), each a costume in a dozen words (garment, colour,
one marker), a `guard` phrase, and a list of at most five era don'ts a
viewer would notice. **No bible.** In a costume-identity style the line is
the identity.

Then render **one reference per main character** (each `YOU-*` stage and
each named recurring figure) straight from its cast line with
`channel-farmer/scripts/style-test.ps1 -Prompts`, into `reference-images/`;
run `generate-scenes/scripts/reference-heads.py` and look at the head
crops: a nose, ear, neck or tinted head means re-render, because every
scene that attaches the reference inherits it; re-roll a wrong one once,
and otherwise let that figure run on its line alone. Copy the style's stock extra
(`content/styles/extras/<Style>-Villager.jpg`, rendered once per style) in
as `Extra-Villager.jpg` and add an `EXTRA` line to the sheet. Settings and
objects get no reference. Set `visual_guardrails` to the sheet and
`status: prompted`.

## Step 7 — Beat sheet 🟡 (once per video)

`scene-prompter` Mode 2 on the whole script: index plus chapter files with
verbatim bookmarks, a ten-word beat per row, hook-shot marks in chapter 1,
`content_prompt` empty, every chapter `beats`. Run
`generate-scenes/scripts/check-manifest.py`; a floor band well over ~10%
means `merge-floor.py` (sub-floor rows join a neighbour, ids renumber);
any FAIL goes back as a Mode 3 edit. Under ten minutes.

## Step 8 — Prompts and generation, one level per loop 🟡

For each level, in order:

1. **Prompts**: `write-prompts`, run by the driving session for this
   level: the recipe, the shot-spread targets, the reference rule and
   chapter 1's `hook-plan.md` live in that skill. It ends with
   `check-manifest.py` clean and the chapter `written`.
2. **Submit**: `generate-scenes` for the level (references shrunk to 1K;
   one or two jobs).
3. **Fetch**: `get-scenes` (one status check; run again later if pending).
4. **Validate**: `validate-scenes` (three checks, Sonnet, one pass) or the
   operator's own look; either way the row gets `validated (n/m)`.
5. **Fix**: a failure is resubmitted once; a second failure gets a
   rewritten prompt. A failure seen three times in the video earns one
   rule line in `content/prompt-hardening-rules.md`.

The first level is the pilot: the operator looks at all of its images
before level 2's prompts are written.

After the last level: `finalize-scenes`, then `align-scenes`, then
`generate-hook`. Set `status: generated`.

## Step 9 — Edit 🟢

All in Resolve Studio through the MCP server. **Verification rule** (conventions.md):
nothing is done until a rendered or measured artefact proves it.

1. `place-scenes`: decide fps, pre-render every visual to exact-frame
   clips, swap each hook still for its Veo clip, add the 2 s level cards,
   draw each text-card row's `overlay` word on its blank carrier the
   same way, author and import the FCP7 XML, verify by readback and
   screenshot. Media is staged at the series
   `staging_path`, never inside OneDrive.
2. `plan-ken-burns` → `claude/ken-burns-plan.md`: Baseline motion on
   nearly every scene, Elevated on ≤10% with confirmed targets, Static
   only on text-cards, no transitions
   (`video.md`'s `transitions` turns black sweeps on, for chapter ends,
   once proven on the locked Resolve version). **The operator edits the
   plan** — pacing and emphasis stay human.
3. `apply-fusion`: motion from the plan; render-verify one scene of each
   motion type before the batch. No particle effects.
4. Grade hook clips only (CDL matched by measurement, per `place-scenes`);
   the body stays ungraded.
5. **Spot SFX only**: a short sound for an action on screen (a pot
   clattering, water splashing, a lamp or fire crackling), a handful per
   level, placed on the scene that shows it. No ambience beds or loops
   under narration. Search `content/sfx/`'s metadata TSV, never the
   filenames; add each sound used to `sfx-index.md` so the library grows
   from what worked. Bake levels well under the voice.
6. Render. Measure the render: integrated LUFS **and per-channel RMS**,
   frame spot-checks at hook, level cards and Elevated scenes. Watch it through.
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
