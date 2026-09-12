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
  prompt-hardening-log.md            channel-level: image-model failure modes → promoted rules
  styles/style-bible.md              named STYLE/NEGATIVE presets + universal negatives
  styles/examples/<Style>.jpg        one exemplar per style (never inside a video folder)
  <series>/
    series.md
    concepts.md  sources.md          series-level unless video.md says otherwise
    mascot/                          optional series-level characters (bible + refs)
    <slug>/
      video.md
      research-<slug>.md             sole factual authority for the script
      reference-images/<Name>.jpg    canonical character AND location references
      voiceovers/NN-<label>.mp3      raw TTS; sorted filename order = playback order
      voiceovers/normalized/NN-<label>.wav   −16 LUFS, 48 kHz, dual-mono stereo
      hook/*.mp4                     optional cold-open clips, cut AFTER alignment
      thumbnails/
      scene-generation/<scene_id>.jpg    exactly one canonical image per scene after finalize
      scene-generation/_archive/         attempts, superseded, manual-edit sources
      _archive/                          disposables swept by close-video (never auto-deleted)
      claude/
        script.md
        character-bible.md           characters and recurring locations
        scene-prompts.md             index: chapter → file → range → status
        scene-prompts/<chapter>.md   ≤25 scenes per file; filenames come from the index
        qc-checklist.md              per-video specifics only (locks, era list, text-card strings)
        batch-log.md
        voiceover-segments/NN-<label>.txt   exact text sent to TTS
        transcripts/                 NN-<label>.alignment.json (TTS timestamps) and/or whisper JSON
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
| `wpm_measured` | last measured narration pace (planning only; timing is always measured) |
| `style_default` | style-bible entry name, or `per-video` |
| `chapter.unit`, `chapter.heading`, `chapter.file` | e.g. `level`, `Level N, the <role>.`, `level-NN.md` |
| `mascot.bible`, `mascot.reference`, `mascot.cameo` | optional; `cameo` = `manual` (operator picks the row at QC) or `none` |
| `cta` | `none` or the house CTA text/placement |
| `concepts_location` | `series` or `slug` |
| `staging_path` | local non-OneDrive path pattern for Resolve media, e.g. `C:\Users\<user>\Videos\<slug>-<fps>` |
| `fps_default`, `resolution_default` | timeline defaults |

## `video.md`

| key | meaning |
|---|---|
| `slug`, `title` | |
| `format`, `style`, `fps`, `voice` | overrides of series defaults; `style` replaces the style bible's "currently assigned" table |
| `status` | `concept` → `researched` → `scripted` → `voiced` → `prompted` → `generated` → `edited` → `published` → `closed` |
| `published_id`, `runtime` | filled at publish / close |
| `visual_guardrails` | pointer to the research file's visual-reference addenda |
| `notes` | anything the next session needs |

## Scene-prompt manifest

Index (`scene-prompts.md`): `| chapter | file | scenes | status |` with status
`planned` or `written`. Chapter file columns:

`| scene_id | script_bookmark | scene_type | content_prompt | style | characters_present / reference_images | notes |`

- `scene_id` = `NNN_<kebab-slug>`; its image is `scene-generation/<scene_id>.jpg`.
- `scene_type` = `illustrated` or `text-card`.
- `script_bookmark` = the verbatim script text the scene covers (parse the
  cell by column boundary, never by quote pair).
- `style` = a bare style-bible entry name; never expanded text.
- Chain groups and scene-specific QC flags go in `notes`.

## `batch-log.md`

`| batch_id | scenes | model | requested_at | status | checked_at | fetched_at | notes |`

`status` is exactly one of: `submitted` · `fetched` · `validated (n/m)` ·
`failed` · `superseded`. Free text goes in `notes`. Footer lines:
`FINALIZED <date>` (finalize-scenes) and `CLOSED <date>` (close-video).
Pharaoh's Servant's log predates this schema and is kept as-is.

## `scene-timing.md`

`| scene_id | chapter | segment | start_seconds | end_seconds | match |`

Seconds are **segment-relative**. `match` = `exact` · `fuzzy(NN%)` ·
`interpolated` · `api` (from TTS timestamps). Row count must equal the
manifest's; a mismatch aborts naming the missing ids.

## `ken-burns-plan.md`

`| # | scene_id | dur | zoom | ease | fx | transition | note |`

`zoom` = `Static` · `In` · `Out` · `Pan <dir> (x,y)→(x,y)` · `Focal (x,y)`.
Coordinates are fractions with origin top-left; `apply-fusion` does the Fusion
Y-flip. `fx` names a particle preset or is blank; `transition` = `sweep` or blank.

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
