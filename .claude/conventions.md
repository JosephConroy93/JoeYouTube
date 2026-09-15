# Pipeline conventions

The single source for the layouts, schemas and status words every agent and
skill relies on. Skills cite this file instead of restating it. Change a
schema here first, then the skills that read it.

## Invocation contract

Every agent and skill takes a **project path** as its first argument:
`<series>/<slug>` (e.g. `watcher-pov/pharaohs-servant`). From it they resolve:

- `content/<series>/series.md` — series config (format default, voice, style
  default, chapter unit, mascot, staging path).
- `content/<series>/<slug>/video.md` — per-video overrides and status.
- The format module named by `video.md` (falling back to `series.md`):
  `.claude/formats/<format>.md`.

No agent or skill contains a literal series name, slug, voice name or era.

## Folder layout

```
content/
  prompt-hardening-rules.md          channel-level: promoted rules + watch list, one line each (read every chapter)
  prompt-hardening-log.md            channel-level incident archive behind the rules (read on demand)
  styles/style-bible.md              named STYLE/NEGATIVE presets + universal negatives
  styles/examples/<Style>.jpg        one exemplar per style (never inside a video folder)
  <series>/
    series.md
    concepts.md  sources.md          series-level unless video.md says otherwise
    mascot/                          optional series-level characters (bible + refs)
    protagonist/                     optional reused "you" figure: cast line + reference image
    <slug>/
      video.md
      research-<slug>.md             sole factual authority for the script
      reference-images/<Name>.jpg    one per main character plus Extra-<Role>.jpg in period dress (Step 6)
      voiceovers/<slug>_voice_NN.mp3             raw TTS as delivered (source; never on the timeline); sorted order = playback order
      voiceovers/normalized/<slug>_voice_NN.wav  the timeline copy: −16 LUFS, true peak ≤ −1.5 dBFS, 48 kHz, dual-mono stereo
      hook/raw/shot-NN.mp4           Veo output as delivered (audio stripped at use)
      hook/shot-NN.mp4               hook clip trimmed to its scene's narration
      thumbnails/<name>.jpg          make-thumbnail output, with <name>-sizes.jpg (1280 / 360 / 168 px check)
      scene-generation/<scene_id>.jpg    exactly one canonical image per scene after finalize
      scene-generation/_archive/         attempts, superseded, manual-edit sources
      _archive/                          disposables swept by close-video (never auto-deleted)
      claude/
        script.md
        cast.md                      cast sheet: one costume line per figure ([[ID]] blocks), era don'ts, overlays
        scene-prompts.md             index: chapter → file → range → status
        scene-prompts/<chapter>.md   ≤25 scenes per file; filenames come from the index
        batch-log.md
        voiceover-segments/<slug>_voice_NN.txt       exact text sent to TTS
        transcripts/<slug>_voice_NN.alignment.json   TTS character timestamps (whisper JSON uses the same stem)
        scene-timing.md
        ken-burns-plan.md
        style-previews/              disposable
```

## `series.md`

A key/value table. Keys:

| key | meaning |
|---|---|
| `series`, `display_name` | slug and human name |
| `format` | default format module name |
| `voice.provider`, `voice.name`, `voice.id`, `voice.model` | TTS voice actually used |
| `voice.speed`, `voice.stability`, `voice.style`, `voice.tempo` | ElevenLabs voice settings (defaults 1.0, 0.5, 0) and a post-generation time-stretch (default 1.0; pitch kept, alignment scaled to match; the only pace control on `eleven_v3`, which ignores `speed`); `video.md` overrides, set from the Step 5 audition |
| `wpm_measured` | last measured narration pace (planning only; timing is always measured) |
| `style_default` | style-bible entry name, or `per-video` |
| `chapter.unit`, `chapter.heading`, `chapter.file`, `chapter.spoken` | e.g. `chapter`, `Chapter N. <Name>.`, `chapter-NN.md`, `no`; `chapter.spoken: no` puts the heading on the chapter card only (not narrated, not bookmarked), `yes` (default) narrates it as a callout; `video.md` may override any `chapter.*` key |
| `protagonist` | optional: a reused series "you" figure (`content/<series>/protagonist/` holds its cast line and reference); Step 6 copies it into the video's cast sheet and re-dresses it per rung |
| `mascot.bible`, `mascot.reference`, `mascot.cameo` | optional; `cameo` = `manual` (operator picks the row at QC) or `none` |
| `cta` | `none` or the house CTA text/placement |
| `concepts_location` | `series` or `slug` |
| `staging_path` | local non-OneDrive path pattern for Resolve media, e.g. `C:\Users\<user>\Videos\<slug>-<fps>` |
| `fps_default`, `resolution_default` | timeline defaults |
| `thumbnail.background`, `thumbnail.ink`, `thumbnail.accent`, `thumbnail.font` | the locked thumbnail template read by `make-thumbnail`: hex colours for the ground, the text and the accent line, and a font file path |

## `video.md`

| key | meaning |
|---|---|
| `slug`, `title` | |
| `format`, `style`, `fps`, `voice`, `wpm_measured` | overrides of series defaults (`wpm_measured` when the video's voice model or tempo sets a different pace); `style` replaces the style bible's "currently assigned" table |
| `status` | `concept` → `researched` → `scripted` → `voiced` → `prompted` → `generated` → `edited` → `published` → `closed` |
| `published_id`, `runtime` | filled at publish / close |
| `visual_guardrails` | pointer to the cast sheet, `claude/cast.md` (Step 6) |
| `sfx` | the video's sound-effect policy (default: spot effects for on-screen actions only, no ambience beds) |
| `transitions` | `none` (default) or `sweep` (black sweeps at chapter ends, once proven on the Resolve version in use) |
| `grade` | a `.cube` LUT under `content/styles/luts/` and its mix (0–1), baked by `place-scenes` into every hook clip and still; default none |
| `film_open` | the last `scene_id` of an opening in the film look (gate weave, flicker, vignette, grain, grey edge falloff, 2.39:1 letterbox); the next scene opens the bars; default none |
| `loudness` | the finished video's integrated LUFS (default −16, the voice files' level; YouTube plays at −14) |
| `thumbnail` | the chosen file(s) in `thumbnails/` with the `make-thumbnail` arguments that built them; two names are a Test & Compare pair |
| `notes` | anything the next session needs |

## Scene-prompt manifest

Index (`scene-prompts.md`): `| chapter | file | scenes | status |` with status
`planned` → `beats` (rows and bookmarks, prompts empty) → `written` (prompts
in). Chapter file columns:

`| scene_id | script_bookmark | scene_type | content_prompt | style | characters_present / reference_images | notes |`

- `scene_id` = `NNN_<kebab-slug>`; its image is `scene-generation/<scene_id>.jpg`.
- `scene_type` = `illustrated`, or `text-card`: a blank carrier object whose
  word (`overlay: "<word>"` in `notes`) is drawn at the edit, never by the
  image model.
- `script_bookmark` = the verbatim script text the scene covers (parse the
  cell by column boundary, never by quote pair).
- `style` = a bare style-bible entry name; never expanded text.
- `content_prompt` is empty at `beats`; written, it is 50–80 words with
  `[[ID]]` tokens from `cast.md`; the full text sent is `gemini-batch.ps1
  -Action expand`'s output. `notes` holds the beat (≤12 words).
- Chain groups and scene-specific QC flags go in `notes`.
- `check-manifest.py` (in `generate-scenes/scripts/`) passes with no FAIL
  before any chapter is submitted.

## `cast.md`

The cast sheet. A table `| block | text | guard |`, one row per figure
(`YOU-<stage>` per costume stage of the protagonist, e.g. `YOU-BOY`, `YOU-CLERK`; `FATHER`; `ID.variant` binds to `ID`'s reference), an
optional row per recurring setting (`YARD`), and `_closing`; then a short
list of era don'ts and an overlays table `| scene | text |`. Written by hand
in Step 6; `gemini-batch.ps1` reads the table (falls back to a legacy
`prompt-blocks.md`).

- `text` = the noun phrase, `{ref}`, then the costume or setting in a dozen
  words: `the tall narrow man{ref}, bald egg head, long white kilt with a
  broad madder-red hem border and red belt, no sash`. `{ref}` becomes
  ` shown in the <Nth> attached reference image` when the row attaches that
  ID, else nothing.
- `guard` = the attributes to preserve, as a possessive phrase; the guards
  of every block a row uses are joined into one sentence at submit.
- `_closing` = the style's figure line(s), appended to every `illustrated`
  row sentence by sentence, skipping any the prompt already holds.
- No `|` inside a cell.

## `batch-log.md`

`| batch_id | scenes | model | requested_at | status | checked_at | fetched_at | notes |`

`status` is exactly one of: `submitted` · `fetched` · `validated (n/m)` ·
`failed` · `superseded`. Free text goes in `notes`. Footer lines:
`FINALIZED <date>` (finalize-scenes) and `CLOSED <date>` (close-video).
A log in the older 6-column shape is read-only for `gemini-batch.ps1`: if such a video needs further submissions, start a fresh 8-column log for it (or migrate the old one) first.

## `scene-timing.md`

`| scene_id | chapter | segment | start_seconds | end_seconds | match |`

Seconds are **segment-relative**. `match` = `exact` · `fuzzy(NN%)` ·
`interpolated` · `api` (from TTS timestamps). Row count must equal the
manifest's; a mismatch aborts naming the missing ids.

## `hook-plan.md`

`| shot | scene_id | motion_prompt | duration_s | beat |`

Written by `scene-prompter` Mode 2 with the first chapter when `video.md`
sets `hook`. At most 8 rows; `duration_s` ∈ 4 · 6 · 8; `beat` is the scene's
`script_bookmark`. Each clip replaces its scene's still in the edit.

## `ken-burns-plan.md`

`| # | scene_id | dur | zoom | ease | transition | note |`

`zoom` = `Static` · `In` · `Out` · `Pan <dir> (x,y)→(x,y)` · `Focal (x,y)`.
Coordinates are fractions with origin top-left; `apply-fusion` does the Fusion
Y-flip. `transition` = `sweep` or blank.

## `sfx-plan.md`

`| scene_id | source | in_s | dur_s | offset_s | lufs | note | until |`

`source` is relative to the SFX library root named in
`content/sfx/sfx-index.md`; `in_s` is the start inside the source; blank
`dur_s` = to the end of the file; `offset_s` is from the scene's start and
the sound must end inside the scene, or inside the optional `until` scene
(a sound held across scenes; blank `dur_s` then runs to that scene's end);
`lufs` is the baked clip's integrated loudness (voice files sit at −16).
`note` names the metadata description and the on-screen action.

## Verification rule (every Resolve step)

A change is done only when a rendered or measured artefact proves it: a
screenshot, an ffmpeg measurement (SSIM/PSNR, integrated LUFS **plus
per-channel RMS**, crushed-pixel %), or a readback that is then rendered. A
`success` return value or a readback alone is not proof.

## Documentation rule

Agent and skill files hold run instructions only: what to read, what to do,
what to write, what must be true. No dates, no "confirmed", no tool
comparisons, no incident narrative. Those go in `CHANGELOG.md` (one line plus
the why) and the git history. A non-obvious technical constraint stays as a
one-line rule.

## Credentials and costs

API keys live in the Windows **user** environment (`GEMINI_API_KEY`,
`ELEVENLABS_API_KEY`), read with
`[System.Environment]::GetEnvironmentVariable('<NAME>','User')` from
PowerShell or `$env:<NAME>`. Never in a file. Costs are always quoted in
sterling.
