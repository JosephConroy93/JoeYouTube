---
name: write-prompts
description: Writes the image prompts for one level of a video's beat sheet — 50–80 words per row from a fixed recipe (shot, cast token, action and emotion, one dressed setting clause held across a run, light), sets each row's reference cell by the reference rule, hits the source channel's shot spread (medium-first, one or two figures, dressed backgrounds, one place per run), writes hook-plan.md for chapter 1, runs check-manifest.py and marks the chapter written. Run by the prompt-writer agent, one level per dispatch (or by the driving session). Use at WORKFLOW Step 8.1, after the beat sheet exists and before generate-scenes.
---

# Write prompts — one level at a time

Layout and schemas: `.claude/conventions.md`. Project path `<series>/<slug>`.
Run by the `prompt-writer` agent, one level per dispatch, or by the
driving session. The prompts are the judgment call in the pipeline: they
are written from what the previous level's QC found, so read that first.

## Inputs

- The level's chapter file at status `beats` (rows, bookmarks, beat in
  `notes`, hook marks), from `claude/scene-prompts.md`.
- `claude/cast.md`: the `[[ID]]` blocks, era don'ts, overlays.
- The style entry in `content/styles/style-bible.md`: its emotion and
  gesture vocabulary and its `Source frames` (glance at two).
- `content/prompt-hardening-rules.md` (the rules table, one screen).
- The previous level's written chapter file and its `batch-log.md` QC
  notes (what failed, what was overruled): what the model does well and
  badly with this cast. Open two of its images only when the notes don't
  say enough.

## Recipe, per row (50–80 words)

`[shot] [[ID]] [action, then emotion in the style's own marks] [setting: one
clause, 2–3 props, dressed] [light].`

- **Shot**: `Close shot`, `Medium shot`, `Medium two-shot`, `Wide shot`. The
  first two words of every prompt, so the spread can be counted.
- **Figures**: one or two. A third only when the beat needs one, and then
  small and far, described in six words with the style's head and skin
  stated. A crowd (six or more) only at the story's climax, and then as a
  crowd, not five individuals.
- **Setting**: one clause. Consecutive rows in the same place reuse the
  clause **verbatim**; change angle, action and figure count instead of the
  room. Dressed even behind a close-up (a shelf of jars, a hanging cloth).
  A recurring place may be a `[[SETTING]]` block in the cast sheet.
- **Age by posture and props** (a stoop, a staff, slow hands); "old"
  alone may add grey hair or a beard, which is fine (the style allows hair
  and headwear that suit a role).
- **Emotion** in the style's vocabulary only (Eggline: brow angle, mouth
  line, sweat drop, tear, blush marks); never "looks sad".
- **A close shot on an object stays attached to its figure**: "[[ID]] seen
  from the chest up, holding X out in front of him", never "the hands of
  [[ID]] holding X, his head soft behind", which draws a second body or a
  pair of hands with no one attached.
- **No tool touching a body** (a knife, hook or spatula at a wrapped or
  covered body): the model reads it as surgery and returns no image. Hands
  smooth, wrap, lift and carry.
- **A callback line may reuse an earlier validated still** ("At sixteen,
  your wrist got slapped" → that scene's image): copy its latest file to
  `scene-generation/<scene_id>.jpg`, write `reuse: NNN` in `notes`, and
  leave the row out of the `generate-scenes` id list.
- **No words in the image.** Name a document by what it is, not what it
  says ("a rolled papyrus tied with string", never "a contract"): the
  model writes the word on it in English. A `text-card` row describes its carrier blank;
  the word is in `overlay:` and drawn at the edit.
- Nothing from the bible or research beyond the cast line; the narration
  carries the facts, the image carries the atmosphere.
- A beat joined from two rows (`; ` in `notes`, from `merge-floor.py`) gets
  the image for the moment its last line lands, not a split composition.
- An extra needing a role detail keeps the `[[EXTRA]]` token and adds the
  detail in words after it (`[[EXTRA]] wearing a plain white sash as a
  lector`).

## Shot spread (from the source channel's census)

Targets per level, counted by `check-manifest.py`: medium 60–75%, wide
15–25%, close 8–15%; rows with one or two `[[ID]]` tokens ≥ 85%; wide
shots and crowds bunched where the story peaks, not spread for variety.

## Reference rule

- A main character (`YOU-*`, any named recurring figure) with a file in
  `reference-images/` is attached on every row it appears in:
  `imageN = <File> (ID)`, figures in order of importance. Without a file,
  the cast line carries it.
- An extra is written as `[[EXTRA]]` and attaches the style's stock extra
  reference (`content/styles/extras/<Style>-Villager.jpg`, copied into the
  video's `reference-images/`); without one, extras render tan about one
  time in three. Settings and objects never get a reference.
- Never more than three references on a row.

## Hook (chapter 1 only)

Hook rows are **medium or close shots**, never wide: the hook sells a
face and a question, not a place (the establishing wide comes after the
hook). For each `hook: shot N` row write one `claude/hook-plan.md` row (schema in
conventions.md): `motion_prompt` says only what moves and any emotion,
allows the mouth to move, asks for one slow constant camera move, never an
action the still already shows; `duration_s` 4, 6 or 8; `beat` = the
bookmark. A hook row re-prompted later gets its plan row rewritten to the
new still.

## Finish

1. `python .claude/skills/generate-scenes/scripts/check-manifest.py <series>/<slug> --chapter <file>`:
   no FAIL; read the spread line and adjust shots if a target is missed.
2. `gemini-batch.ps1 -Action expand … -SceneIds <two rows>`: read two
   expanded prompts once, as the model will.
3. Index row → `written`. Hand to `generate-scenes`.

## Boundaries

Does not cut or re-bookmark scenes (`scene-prompter` Mode 3), render a
reference (Step 6), generate, fetch or QC.
