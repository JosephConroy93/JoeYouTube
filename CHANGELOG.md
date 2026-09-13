# Changelog

Tracks changes to **workflow (`WORKFLOW.md`), agents (`.claude/agents/`), and
skills** only — not research findings, tooling decisions, or content. Those
stay in [research/inventory.md](research/inventory.md). Newest first.

---

## 2026-09-13 — Core refactor: docs pruned to run-instructions, series-agnostic config, scripts extracted, ElevenLabs earmarked

Retro + plan: `research/artifacts/retro-2026-09-12-refactor-plan.md`. Branch `refactor/core-pruning`, one commit per group; `main` = pre-refactor baseline.

- **Source control**: project root is a git repo; whitelist tracks only the core (`.claude/`, `WORKFLOW.md`, `CLAUDE.md`, `CHANGELOG.md`, `.mcp.json`, `tools/`); `davinci-resolve-mcp` is a submodule pinned to v2.213.2. Why: version the mechanics, not 600 MB of content.
- **`.claude/conventions.md`** (new): `<series>/<slug>` invocation contract, folder layout, `series.md`/`video.md` schemas, fixed batch-log status enum, pinned `scene-timing.md` and `ken-burns-plan.md` schemas, verification rule, documentation rule. Why: five skills each described the same files slightly differently.
- **`.claude/formats/rank-ladder.md`, `explainer.md`** (new): script shape, register, runtime and Stage 2 rubric per format. `script-writer` keeps only the format-independent provenance discipline and loads a format by name. Why: one writer with format modules instead of a writer per series; the sourcing rules must not fork.
- **`content/<series>/series.md`, `content/<series>/<slug>/video.md`** (new, untracked data): voice, style, chapter naming, mascot, fps, status. Every hardcoded `content/watcher-pov/...`, Jim/171 wpm, `level-NN`, mascot and Egypt rule left the agents and skills.
- **All agents/skills pruned** to run-instructions (37k → ~11k words): history, dated confirmations, dead-tool comparisons (Sollo, Syntx, VidIQ voiceover, Claude-in-Chrome) removed; non-obvious constraints kept as one-line rules. `scene-prompter` Mode 1 now locks recurring locations as well as characters (location drift on the last video).
- **Scripts extracted** so nothing is re-derived from prose: `align-scenes/scripts/align.py` (reproduces the last video's timing 198/198), `place-scenes/scripts/build_timeline.py` (reproduces the 39,813-frame timeline), `generate-scenes/scripts/gemini-batch.ps1`, `apply-fusion/scripts/apply_baseline.lua` + `capture-window.ps1` (untested until a one-scene run), `generate-voiceover/scripts/tts.ps1` and `close-video/scripts/close-video.ps1` (dry-run tested). `.ps1` files are CRLF + UTF-8 BOM, ASCII only (Windows PowerShell 5.1 parsing).
- **`apply-ken-burns` + `apply-particles` → `apply-fusion`**: one owner for the Fusion node graph (Merge-before-Transform). `DoorwayDust.setting` fixed (dangling Glow reference).
- **`generate-voiceover`** (new): ElevenLabs with-timestamps REST, −16 LUFS dual-mono 48 kHz WAV, alignment JSON for `align-scenes --source api`. Hosted ElevenLabs MCP is for auditioning voices only (a hosted server can't write files; narration through the context window is the token failure CLAUDE.md warns about). Creator tier ≈ £17/month ≈ £3.40/video.
- **`close-video`** (new): archive-never-delete close-out; reconciles the batch log; first real run pending Pharaoh's Servant's publish.
- **`finalize-scenes`**: `failed/` → `_archive/`, also sweeps `reference-images/`, writes `FINALIZED` footer. `validate-scenes` owns the four checks; `qc-checklist.md` holds per-video specifics only.
- **`WORKFLOW.md`** rewritten as-is and renumbered Step 0–12: voiceover + alignment straight after script lock (hook clips cut to measured beats), visual pass, thumbnail after the edit with the research-guardrail gate, publish, close-out. Old Step 6/7 ordering notes resolved. `CLAUDE.md` rewritten: phase = production, pointers and rules only.
- `content/prompt-hardening-log.md` moved to channel level (stub left at the old path). `plan-ken-burns` `dur` = hold until the next scene starts, matching the real build.
- **`generate-voiceover` live-tested** (one segment): fixed PowerShell 5.1 ffmpeg stderr handling (route through `cmd /c`), last-match parsing of ebur128 summaries, BOM-free alignment JSON, backtick-stripping config reader; added `--skip-generate` and `scripts/voices.ps1` (list/search/add voices). Series voice id recorded in `series.md`.
- **`channel-farmer`** (new): one channel in → dossier, transcript breakdowns, competitor-index section, frames, a validated style-bible entry (≤10 Gemini images via `scripts/style-test.ps1`, live-tested), and a format module if needed. `style-farmer` gains `scripts/grab-frames.sh` (sectioned yt-dlp + ffmpeg, `YTDLP_EXTRA` for browser cookies). WORKFLOW Step 0 points at it.
- **`channel-farmer` first real run** (The Explainer Boss): rules added — `vidiq_video_watch` misreports motion (use the frames pass or the operator); `/watch` on Windows needs `PYTHONUTF8=1` and leaks the cookie file into its work dir; yt-dlp config cookie path must use forward slashes; `style-farmer` uses `bv*` (video-only) since signed-in sessions get no muxed stream.
- Going forward this file takes one line per change plus the why; diffs are in git.

## 2026-09-12

- **`apply-particles` and `plan-ken-burns` gained a hard darkness gate for FX
  candidates.** Joe spotted on first watch-through of the assembled Pharaoh's
  Servant cut that the workshop scene (`030`) showed no particles. It had a
  correctly-built comp with **byte-identical emitter settings** to `066`, which
  works. Checking all five FX scenes in the finished render: **three of five
  were invisible** — `030`, `043`, `161`.
  The cause is not tuning, it is the blend mode. The recipe merges pale
  particles with **Screen**, which can only *brighten*; over a backdrop already
  near white there is nowhere to go and the particles are mathematically
  invisible at any Size/Number/Alpha. Measured mean luma of each particle's
  **travel path** (not its emitter point — `161`'s emitter sits on dark roof
  beams but the particles drift straight out into blown sky):
  `066` 0.37 ✓ · `030` 0.47 ✗ · `043` 0.74 ✗ · `161` 0.81 ✗.
  New rule in both skills: **reject any FX candidate whose particle path
  exceeds ~0.40 mean luma**, with the exact `ffmpeg ... scale=1:1,format=gray`
  measurement command and a marginal band of 0.40–0.50 requiring a render
  check. `plan-ken-burns` additionally now treats "an environmental light
  source is named in the prompt" as **necessary but not sufficient**, and
  recommends ranking every scene image by luma first and drawing candidates
  only from the darkest handful — the two scenes that worked (`066`, `186`)
  were the two darkest images of all 198.
  Contributing process failure worth recording: `030` and `043` were the only
  two FX scenes **never render-verified**, which is exactly how they survived
  into a finished cut. `apply-particles`' Verification section already prefers
  a live-viewer check over a render; that is fine for tuning but does not
  substitute for confirming each built effect in output at least once.
  Resolution on this video (Joe's call): the three dead scenes were **dropped**
  rather than re-sited — particle nodes deleted, comps rewired to
  `MediaIn1 → KB → MediaOut1` with Ken Burns motion intact — and the dark-scene
  pivot applies to **future** videos at planning time.


- **`WORKFLOW.md` Step 7 gained a voiceover loudness-normalisation gate.**
  VidIQ generates voiceover at **~-30.8 LUFS** (measured across all six
  Pharaoh's Servant segments) — about **17 dB below** YouTube's ~-14 LUFS
  target. YouTube only normalises *down*, never up, so a mix left at source
  level plays back far quieter than surrounding videos and reads as thin, not
  merely quiet. Joe's first-watch note ("the audio is too low... scarcity of
  viewer experience") was exactly this. New banner gives the measure/apply
  ffmpeg pair, the target (**-16 LUFS, TP ≤ -1.5 dBFS**), the
  **`alimiter ... level=disabled`** requirement (it auto-normalises by default
  and will *raise* the level instead of taming it), the LRA sanity check for
  over-compression, and the instruction to export **WAV at project frame rate**
  so source frames equal timeline frames. Placed at Step 7 because gain does not
  affect timing — the `align-scenes` transcript and `scene-timing.md` stay valid
  — and doing it there avoids the wasted full render this video needed.

- **`WORKFLOW.md` Step 8 now points at the SFX catalogue, plus a reusable pack
  indexer.** New `content/sfx/index-pack.sh` reads embedded BWF/ID3 metadata
  from any sound library into a searchable `description / duration / path` TSV.
  Built after the £8 Cinematic bundle looked useless by filename — every file
  had been bulk-renamed to meaningless poetry ("aerial rhythms 12") — while the
  **original Soundminer keyword metadata survived intact in the WAV headers**
  for 2,751 of its 7,842 files ("Wind, Storm, Strong, Low"). Standing rule now
  recorded: **index a new pack and search the metadata before auditioning
  anything by hand**, and check a pack for `room tone`/`walla` *before* buying —
  their absence identifies a trailer/game pack in one query.

- **`WORKFLOW.md` Step 6 gained a factual-accuracy gate on thumbnail text.**
  Thumbnail copy is a factual claim and the first one a viewer sees, but it was
  never checked against the video's own research guardrails the way script lines
  are. Caught live: "BURIED ALIVE" was drafted, rendered onto all three
  Pharaoh's Servant thumbnail variants and recommended, before Joe asked "were
  they buried alive though??" — they were not. That video's research states
  cause of death is **genuinely unresolved** (strangulation and poison both live
  proposals) and explicitly says *"Do not present either method as the single
  documented truth for all victims."* Two compounding costs recorded: the claim
  **contradicted the video within minutes of the click** (a retention/trust
  problem, not only an accuracy one), and it was **a competitor's framing** —
  the same research file lists Past Unlocked's *"What If You Were Buried Alive
  as a Pharaoh's..."*, so copying it surrendered the differentiation the concept
  was chosen for. New rule: where research flags something contested, the
  thumbnail may not resolve it; prefer a differentiated fact the research does
  support, and make thumbnail text *add* the stake rather than restate the
  title. Rejected renders kept on disk as `.rejected-inaccurate-*`.

- **`place-scenes` gained a safety section on `timeline.lift_range`.** Called to
  remove a 9-second SFX bed scoped to `track_index=2`, it refused and named the
  **voiceover clips on A1 and A3** as the blocking items — the range applies
  across every track regardless of `track_index`, and its own error suggests
  `allow_partial_item_delete=True`, which would have deleted the entire last 3.5
  minutes of voiceover. New rules recorded: never pass that flag once VO is
  placed; replace audio by **disabling** the old item and placing the new one on
  a **new track**; bake levels into files before import since `Volume` writes
  return `false`. Also records that the versioning hook archived the timeline
  (v7) before the refused call.

- **`place-scenes` safety section extended with two more same-day traps.**
  (1) A **mono** WAV placed on a stereo track rendered to the **left channel
  only** — v2 measured a clean −16.2 LUFS integrated with the right channel at
  −inf, and Joe caught it by ear on a soundbar ("distant, back-left, better in
  mono"). Rule: export VO as dual-mono stereo, and add **per-channel RMS** to
  every audio verification — integrated loudness is blind to channel balance.
  (2) **`timeline.set_track_enable` returned `success: true` twice on A3 and
  did nothing**, leaving the mono track summing +6 dB into the left; it had
  worked on A1. Rule: `get_track_enabled` readback, fall back to per-item
  `set_clip_enabled` (which took), then render and measure. v3 is the upload
  candidate; L/R verified identical at −20.04 dB on the check excerpt.

## 2026-09-11

- **`apply-particles` gained the numbers that actually transfer;
  `apply-ken-burns` gained the pan-headroom invariant.** Both from applying
  the plan to a real 198-scene video.
  **`apply-particles`**: the Tomb Robber reference values do NOT transfer —
  `Velocity 0.025 × Lifespan 200` = 5.0 units of travel across a ~1-unit
  frame, producing a snowstorm of specks settling on a character's face.
  New rule: **`Velocity × Lifespan` ≈ total travel; keep ≤ ~0.4 for ambient
  dust.** Plus the empirically confirmed coordinate mapping
  (`Translate.X = x − 0.5`, `Translate.Y = 0.5 − y`, verified by pinning
  velocity to ~0 and reading the region indicator in the viewer), the
  finding that **`Angle 90` = up with no sign flip** (the existing "try
  negative first" note was specific to the doorway geometry, not
  universal), an ease-in via keyframed Merge `Blend`, and a new section on
  Merge placement relative to a Ken Burns Transform — before it, so
  particles travel with the plate, with the three consequences that
  follow (`Size` multiplies particle size *and* apparent velocity; the
  emitter must stay inside the moving crop window; net motion is particle
  drift + camera drift).
  **`apply-ken-burns`**: six pan scenes shipped with a black bar sweeping
  into frame because `Size 1.25` cannot cover a `Center` excursion of
  ±0.32. Added the invariant **`Size ≥ 1 + 2 × max|Center − 0.5|`** with
  the worked example, and the process lesson that caused it — the broken
  pans passed an SSIM/PSNR check read as "large real movement" when part of
  that difference *was the black bar*. A metric confirms something changed,
  not that the right thing changed; extract and look at the first and last
  frames of any pan.
- **`apply-ken-burns` gained a "real scale" section; `plan-ken-burns`'s
  transition claim corrected as factually wrong.** Applying motion to 198
  scenes at ~6 MCP calls each is ~1,100 round-trips, so the working split
  is: Baseline zoom tier via one **Lua script run inside Fusion**
  (`script_plugin` install; `StartUndo`/`EndUndo`, never `comp:Lock()`) —
  178 scenes, `failed=0`, ~5 min — and the 10 Elevated Pan/Focal scenes via
  the proven MCP `XYPath`/`Pivot` recipe, batched in parallel rounds. Three
  gotchas recorded: `script_plugin execute` returns `success: false` while
  the script **does** run (non-blocking `RunScript`); Lua `print()` is not
  capturable by the MCP, so the Console must be screenshotted as its own
  top-level window; and Lua `%b{}` against a whole JSON document matches
  the OUTER object, yielding one phantom record and silently applying
  nothing (narrow to the array first, plus a count guard that aborts rather
  than half-applying).
  **`plan-ken-burns` correction**: it asserted transitions "cannot be
  automated, not just 'not yet'" and would stay manual "forever". Wrong —
  `TimelineItem.AddTransition` exists from **Resolve 21.1**, and an
  offline-authored cross dissolve already round-trips. What is true is
  narrower and version-specific: on 19.1.3.7 the API cannot create one, and
  a dip-to-colour authored via XML was measured **rendering inert on this
  exact build** — which is precisely the planned black sweep. Reframed as a
  version constraint with a known exit.
- **`place-scenes` rewritten around the recipe that actually worked, and
  `align-scenes` given a parse fix + row-count guard.** The first
  `place-scenes` draft (below) documented a `create_timeline_from_clips`
  path that does not survive contact with a real manifest. Confirmed live:
  a still's duration is unsettable before, during *and* after placement
  (the server's own ledger — TimelineItem has "NO matching setters"), so
  the ffmpeg pre-render is the only path, not an optimisation; and
  assembling 200 clips needs one authored **FCP7 XML** imported via
  `timeline.import_timeline_checked`, which places video *and* audio at
  exact frames with no media-pool UUIDs (plain appends can't put audio
  under the picture — `AppendToTimeline` appends at the timeline end).
  Also added: scenes must hold until the *next* scene starts (honouring
  bookmark ends gave 165 gaps / 109s of black frames), frame-rate choice
  belongs to whatever real motion footage exists and can only be set on a
  fresh project pre-timeline (`timelinePlaybackFrameRate` can't be set from
  the API at all — a manual GUI step, or playback runs off-cadence and
  audio *looks* desynced), centre-cropping to true 16:9 because no
  generator returns exactly 16:9, and the hook-beat cut rule. Dead end
  recorded: external Resolve scripting segfaults on this machine in both
  shells and both interpreters.
  **`align-scenes`**: its bookmark capture terminated at nested double
  quotes, silently dropping the only 3 manifest rows that contain them and
  then reporting "195/195 … 0 flagged" against a 198-row manifest — 3
  scenes would have been missing from the finished video. Now parses the
  bookmark by table column and reconciles parsed-vs-manifest row counts
  before writing.
  Both proven on the real thing: Pharaoh's Servant is on a verified
  201-clip / 6-segment timeline, 22:07, frame-exact.
- **New `place-scenes` skill** — turns `scene-timing.md` (from the
  same-day `align-scenes` skill) plus a project's scene images, hook
  clips, and voiceover segments into an actual DaVinci Resolve timeline:
  every visual imported and placed at its exact measured position/
  duration, before `apply-ken-burns` runs. Built and validated live
  against a running Resolve Studio (not written speculatively) — found
  two real, silent API gotchas in the process: a still image's on-timeline
  duration cannot be set per-clip via `media_pool_item.set_clip_property`
  (fails silently, falls back to Resolve's 5s default), and
  `create_timeline_from_clips`'s `start_frame`/`end_frame` are SOURCE
  frames in the clip's own native rate, not the timeline's (a 30fps hook
  clip placed against a 24fps timeline landed ~21% short when this wasn't
  accounted for). Fix: pre-render every visual through `ffmpeg` to the
  timeline's own fps at an exact frame count before import — confirmed
  frame-accurate via `append_to_timeline`'s own `drift_detection` field.
  Also documents a real hook/body timing conflict found on Pharaoh's
  Servant (27.096s of hook footage vs. a 21.40s audio cue for the first
  body scene) and a mechanical placeholder (trim the hook's tail) pending
  the still-unbuilt hook→Level-1 transition. Validated small-scale only
  (hook + level-01, 22 clips) — full-manifest run not yet done.
- **New `WORKFLOW.md` Step 4.5 — Visual reference pass — plus a matching
  `scene-prompter.md` Mode 2 rule.** Root-caused from two real Pharaoh's
  Servant QC findings the same morning: dogs rendering as a modern
  golden-retriever type, and a palace hall rendering with no wall
  decoration next to a sibling scene that had rich painted reliefs. Both
  trace to the same structural gap — Step 3's research is scoped to
  *narration* accuracy (what the script may say), never to *visual*
  accuracy (what a scene may show), so a script can pass every fact-check
  gate while still containing elements whose real appearance was never
  researched. `scene-prompter` then either invents an unconstrained
  visual or leaves it generic enough that the model defaults to something
  anachronistic — the same shape as the already-promoted 2026-09-09
  "unconstrained character defaults to the wrong era" finding, just caught
  one step earlier (prompt-writing time, not generation-QC time), and on
  non-human elements this time. Fix: a new Step 4.5 between script lock
  and Mode 2, run by the driving session (not `scene-prompter` itself,
  which has no web-research tool) — scans the locked script for visually-
  specific elements, checks the research file for existing visual
  coverage, and appends a sourced, properly-caveated addendum where
  missing (worked example: `research-pharaohs-servant.md`'s 2026-09-11 dog-
  appearance addendum to beat 12). `scene-prompter.md`'s "Standing content
  rules" now tells Mode 2 to check for these addenda before writing a
  `content_prompt`, and to flag a gap plainly in `notes` rather than guess,
  if Step 4.5 hasn't run yet for that chapter. Joe's framing: *"what's
  important is that we make the process watertight... if we need the
  workflow to change... then so be it."* Status: defined, not yet run as
  its own deliberate pass from the start of a video — reconstructed after
  the fact here; the next video is the real test.
- **`validate-scenes.md` — closed a `batch-log.md` write-back gap.** The
  skill already documented offering Joe the choice to review fetched images
  himself instead of running an automated QC pass, but never said who
  updates `batch-log.md`'s `status=validated` when he takes that choice —
  the write-back instruction lived only inside this skill's own procedure.
  Confirmed gap: several Pharaoh's Servant chapters (levels 1-6) sat at
  `status=fetched` despite Joe having already reviewed them in chat, which
  a later session misread as "never QC'd" and re-dispatched redundant
  review agents against. Fix: the "Before invoking this skill" section now
  states explicitly that a Joe-driven review still needs the same
  `batch-log.md`/`prompt-hardening-log.md` write-back this skill would do —
  the write-back belongs to the review event, not to this skill.
- **`scene-prompter.md` — mascot cameo generation moved from automated to
  manual-only, on top of the 2026-09-10 scene-selection change.** Prompted
  by Joe's Pharaoh's Servant retrospective: `096` (the one real production
  use) took three full automated regeneration attempts, all failing on
  positioning, before a single manual Syntx edit worked in one pass. This
  agent no longer writes the mascot into any row's `content_prompt` or
  reference images at all — the designated scene generates and QC's as a
  completely ordinary scene, flagged only in `notes`, and the cameo is
  inserted afterward as a manual image-edit on the finished canonical file.
  Also retires the chain-scenes "no alien negative on dependent rows" rule
  (nothing to bleed if he's never in the automated image) and rewrites
  Mode 2 self-check #7 to match. Not retroactive to `096`.
- **`scene-prompter.md` — new filename-prefix convention for scene-prompt
  files, forward-only.** Joe's feedback: Pharaoh's Servant's bare
  `level-01.md` naming means a VS Code filename search hits every project
  once a second video exists. Mode 2 now derives a short all-caps
  abbreviation from the project slug on first use (`pharaohs-servant` →
  `PS`, etc.) and prefixes every chapter file and the index with it
  (`PS_level-01.md`, `PS_scene-prompts.md`). Pharaoh's Servant's existing
  files are not renamed.
- **New skill `finalize-scenes`** (`.claude/skills/finalize-scenes/SKILL.md`).
  Archives every non-canonical file out of a finished project's
  `scene-generation/` folder (`attempt-N` resubmissions, `.superseded-*.jpg`
  originals, one-off manual-edit intermediates) into a `failed/`
  subfolder, leaving exactly one `<scene_id>.jpg` per scene — so the
  folder is directly importable into DaVinci as a whole. Gated on
  `batch-log.md` showing every row validated; never deletes anything, only
  moves. Prompted by Joe's retrospective flag that Pharaoh's Servant's
  folder held 208 files for 198 scenes with no step to clean it up before
  editing. Run for real against Pharaoh's Servant the same day this skill
  was written: 10 non-canonical files archived, 198 canonical files
  confirmed present.

---

## 2026-09-10 — `scene-prompter.md`: mascot cameo scene selection moves from the agent to Joe

Prompted by QC on Pharaoh's Servant level-06's `096` — the first real
production use of the "one hidden cameo per video" mechanic, chosen
algorithmically at Mode 2 segmentation time as "the first dense
multi-specialist scene." It still needed a QC-driven placement fix once
rendered (skin colour drift, not genuinely obscured). Joe: *"regarding the
Watcher scene, I think it would be best for it not to be scripted by the
agent/skill — it's something I'll choose and own myself when I'm QC'ing —
I'll get a feel for what's the best scene to do it on."*

- **"Channel mascot" section rewritten**: scene selection is now Joe's own
  manual call during QC, not this agent's during segmentation. If no scene
  has been named yet for a video in progress, Mode 2 leaves the mascot out
  of every row and says so, rather than guessing — added later via a
  targeted Mode 3 edit once Joe picks one.
- **New standing requirement**: the cameo row must attach `MASCOT-01`'s own
  reference image (plus the standing colour-preservation guard), the same
  as every other locked character — added after the text-only description
  drifted on skin colour with no reference image attached.
- **New standing requirement**: if the cameo row becomes a `chain-scenes`
  seed, every dependent row in that group needs an explicit "no alien
  figure" negative — the mascot bled from seed `096` into dependent row
  `099`, which never mentioned him. See
  [`content/watcher-pov/prompt-hardening-log.md`](content/watcher-pov/prompt-hardening-log.md)
  for the full QC record behind all three changes.
- Not retroactive — `096` stands as Pharaoh's Servant's cameo scene; this
  applies to scene selection on future videos.

## 2026-09-10 — New `chain-scenes` skill + `scene-prompter` Mode 4: seed-then-chain submission for consistency-linked scene groups

Same day as the request/fetch/validate split immediately below, layered on
top of it rather than reopening it. Prompted by a real QC finding on
Pharaoh's Servant level-01: rows `016`/`017`/`018` are a deliberate held
pairing (same courtyard) but were generated as fully independent batch
requests with no shared context, so the rendered environments drifted
(`016` came out richer; `018` also picked up unwanted wall carvings
neither sibling had). Fixed by hand first — regenerated `017`/`018` with
`016`'s real generated image attached as a second, positionally-referenced
image ("match its environment as closely as possible") — then turned into
a repeatable mechanism at Joe's request: *"is there a smoother way of
generating the scenes... when we tackle one, we take a look at scenes that
are 'the same as' and ensure the prereq scene is produced and submitted as
a reference image?"*

- **New skill `chain-scenes`** (`.claude/skills/chain-scenes/SKILL.md`) —
  orchestrates `generate-scenes`/`get-scenes`/`validate-scenes` across two
  phases for one chapter: submit just a group's seed scene(s), poll
  narrowly until that small batch resolves, quick-QC the seed(s), rewrite
  the dependent rows to reference the real seed image, then submit the
  remainder normally. Calls all three existing skills exactly as
  documented, unmodified — this is a pure orchestrator, not a change to
  any of their contracts. A chapter with no detected groups is a no-op
  that defers to a plain `generate-scenes` call.
- **Deliberately reopens a bounded version of the "request and then poll"
  pattern** the entry below split apart — scoped to a handful of seed
  images per chapter, never a whole chapter's batch, and confirmed with
  Joe as the right scope for that exception before building it.
- **New `scene-prompter` Mode 4 — CHAIN** (`.claude/agents/scene-prompter.md`),
  reusing the Mode 4 slot vacated by the old per-scene batch-QC mode
  (retired 2026-09-08, now re-titled "Retired: per-scene batch QC" in that
  file to avoid collision). Two sub-steps: **4a** analyzes a chapter and
  tags consistency-linked groups (recorded as a `notes` addendum — no new
  manifest column, per this project's standing avoidance of retrofitting
  an already-written manifest's schema); **4b** rewrites each group's
  dependent rows once the seed image is real, adding a second positional
  reference plus a mandatory pose/composition guard — a direct fix for a
  second real finding the same session: `018`'s regeneration matched
  `016`'s environment correctly but also over-matched its pose/held object,
  because `018`'s own requested action was already close to `016`'s.
- **`WORKFLOW.md` Step 5 updated** to list `chain-scenes` as a fifth,
  situational skill — invoked deliberately for a chapter with known
  continuity groups, not part of the default linear chain.
- **First real scripted run, same day: level-02, 3 groups, clean.** Mode 4a
  found 3 real consistency groups (courtyard: `026`/`027`; workshop:
  `029`/`030`/`031`; quiet corner: `032`/`033`/`034`) and correctly left two
  edge cases untagged rather than forcing them (a 3-room junction shot
  needing 2 simultaneous location references; a distant background field
  reference that would've double-booked an existing seed) — reported back
  instead of silently guessing. All 3 seeds passed quick QC first try. Mode
  4b's rewrites correctly adapted to real per-seed limitations the QC pass
  surfaced (an ambiguous camera vantage on one seed, a seed showing 1 figure
  where the dependent scene needed 2-3, a seed with no doorway for a
  dependent scene needing an exit implied) rather than applying the
  template blindly. **One real problem hit and fixed on the spot, not
  anticipated in the skill's own doc**: the remainder submission (12
  illustrated requests, several carrying 2 reference images) hit
  `generate-scenes`' 20MB inline cap (23.55MB) on a chapter smaller than
  the range that cap was flagged untested at — fixed by splitting into
  multiple same-mechanism submissions rather than reaching for the
  untested Files API path; `generate-scenes/SKILL.md` updated with this as
  the new recommended default. Full remainder batch fetch/QC still pending
  as of this entry — that's the normal follow-up `get-scenes`/
  `validate-scenes` pass, not part of `chain-scenes` itself.
- **Second real chapter run, same session: level-03, 2 groups, mechanism
  holds clean on the pose/continuity dimension specifically.** Mode 4a
  found 2 groups (workshop: `038`/`039`/`040`; courtyard: `052`/`053`/
  `054`/`055`, the latter spanning a daylight-to-golden-hour lighting
  shift). All 5 dependent rows passed QC — including `040`, the first real
  test of the newly-promoted "differentiate the pose, don't just add a
  guard sentence" rule (worked), and `054`/`055`, the first test of an
  explicit lighting-exclusion carve-out on an environment-match instruction
  (also worked — golden-hour rendered correctly despite the seed being
  plain daylight). **Level-02's `031` failure was also fixed and confirmed
  in this session**: Mode 3-revised with a genuinely different pose
  (seated at a distance vs. standing adjacent) rather than a repeated guard
  sentence, resubmitted, and passed clean on retry — real evidence the
  newly-promoted rule works, not just a plausible theory.
- **Two chapters in, zero pose-bleed repeats found beyond the original
  `018`/`031` cases that produced the standing rule** — the 3 other level-03
  failures (`043` Djer crown mismatch, `045` legible tally-tablet text,
  `050` cloned background faces) are all pre-existing, unrelated failure
  modes with their own log entries, not new chain-scenes-specific bugs.
- **Small implementation bug found and fixed the same session, not a
  design flaw**: level-03's Mode 4b run correctly matched the pre-existing
  `;`-separated `characters_present` convention already used elsewhere in
  that same file for multi-reference rows, but level-02's earlier Mode 4b
  run had used `,` instead (no pre-existing multi-image row in that file to
  match against). `scene-prompter.md` now states `;` as the standing
  convention explicitly; level-02's rows were normalized to match.
- **Paused here, Joe's call**: two chapters is a strong result on the
  specific question of whether the pose-bleed fix generalizes, not yet
  grounds to roll `chain-scenes` out unattended across every remaining
  chapter — next step is Joe's review before continuing further.

---

## 2026-09-10 — Scene generation re-modularized: resumable Mode 2, style-preview extracted to its own skill, generate-scenes split into request/fetch/validate

Second modularization pass the same day as the global-QC-checklist redesign
(see entry below) — Joe, after using the redesigned pipeline for real:
*"I need to refactor even more, breaking things down to be more
modular... this should protect us from big context churning operations and
big file reads."*

- **`scene-prompter` Mode 2 is now resumable, chapter-at-a-time.** First
  invocation on a fresh project writes a planning table (every chapter
  boundary, `planned`/`written` status) into `scene-prompts.md`, then
  writes only the first chapter in full. Later invocations take "the next
  N" or "the rest"; unspecified defaults to just the next unwritten
  chapter. Manifest-wide self-checks (mascot-cameo uniqueness, overall
  distribution) run once, when the batch that completes the manifest is
  written — not silently skipped, not run redundantly per batch.
- **Mode 5 (STYLE PREVIEW) removed from `scene-prompter` entirely**,
  rebuilt as the standalone `preview-style` skill
  (`.claude/skills/preview-style/SKILL.md`). It never needed agent-level
  judgment, and the agent structurally can't execute it anyway (no Bash —
  the exact wall three real Mode 5 dispatches hit earlier the same day).
  Defaults to fast/direct generation (matching real usage from the
  earlier style-preview session), reuses `generate-scenes`'
  request-building and `validate-scenes`' QC rather than duplicating
  either.
- **`generate-scenes` split into three skills at the "wait for the batch"
  boundary** — Joe: *"I don't really like the idea that we request and
  then poll."*
  - **`generate-scenes`** (trimmed): builds and submits exactly one batch
    (one chapter by default, or an explicit N-chapter/"rest" instruction —
    same argument shape as Mode 2's), logs the submission to a new
    per-project `batch-log.md` (`batch_id`, chapter/range, `requested_at`,
    `status`), and stops.
  - **`get-scenes`** (new): one status check per pending `batch-log.md`
    row, never a poll loop — not ready → logs the check and exits, safe to
    invoke again any time later; ready → files results to
    `scene-generation/<scene_id>.jpg` and marks the row `fetched`. No
    content judgment.
  - **`validate-scenes`** (new): the four-check global QC (from the
    earlier same-day redesign) against a `fetched` batch, in 5-8-image
    subagent groups. **Automatic retries removed entirely** — marks
    pass/fail and why (logged to `prompt-hardening-log.md`), then leaves
    the fluke-vs-systematic call, and whether that means a plain
    resubmission or a `scene-prompter` Mode 3 prompt revision first, to
    whoever's driving the session. The session should also offer Joe the
    option to review fetched images himself before spending an automated
    QC pass at all.
- **`WORKFLOW.md` Step 5 rewritten** to describe the new one-agent/
  four-skill shape. Pharaoh's Servant's existing files were **not**
  retrofitted this pass — its manifest is already fully written, and
  Mode 2's resumability only matters for a manifest not yet complete.

---

## 2026-09-10 — Scene-prompts/QC/generation workflow redesigned for cost — global QC checklist replaces per-row column, batch/QC dispatch sizing formalized

**Supersedes the narrower "prominence test" entry immediately below** (same
day, same root complaint) — kept as an accurate record of the intermediate
step, not deleted, but its mechanism is now replaced by this bigger change.

- **Joe, after living with the workflow for real this session**: *"big huge
  document reads/writes/refactors - multiple agents reading the same huge
  files, trivial image failure/qc feedback loop seems very expensive...
  QC strictness needs cutting by about 70%... is there a better way we can
  plan/execute this workflow?"*
- **The per-row `qc_checklist` manifest column is gone**, replaced by one
  shared `content/watcher-pov/<slug>/claude/qc-checklist.md` per video,
  written once by `scene-prompter` Mode 2 (not 198 times). Four coarse
  checks — scene match, character consistency, major era violations only,
  nothing malformed — plus text-cards' own unchanged exact-text rule.
  Explicitly does **not** hunt for minor background detail (illegible
  marks on a small prop, anything needing a zoomed crop) — out of scope
  entirely, not even a soft note. Scene-specific flags (mascot cameo,
  sanctioned negative overrides) now live in `notes`, which already served
  that purpose, instead of a second parallel column.
- **Batch submission and QC review are now explicitly decoupled** in
  `generate-scenes/SKILL.md`: one chapter file (≤25 scenes, per today's
  earlier manifest split) = one Batch API submission, but QC review of the
  results runs in small 5-8-image subagent groups — a rule `CLAUDE.md`
  described as already existing but that wasn't actually written into the
  skill's own operating instructions until now.
- **Pharaoh's Servant retrofitted**, not just future projects:
  `qc-checklist.md` written; the now-redundant `qc_checklist` column
  stripped from all 11 `scene-prompts/level-*.md` chapter files (198 rows,
  mechanical script, row-count verified unchanged). `scene-prompter.md`,
  `generate-scenes/SKILL.md`, and `WORKFLOW.md` Step 5 all updated to
  describe the new schema; `prompt-hardening-log.md`'s 2026-09-10
  scribe-tablet entry got a second addendum pointing at this change instead
  of the now-superseded prominence test.
- **What did not change**: prompt-writing discipline itself (character
  negatives baked into `content_prompt`, positional reference binding,
  segmentation/pacing rules) — good prompting is what prevents a retry
  being needed, a separate lever from how strictly the result gets checked
  afterward. The retry policy's own mechanics (3 attempts, escalating
  tweak) are unchanged.

---

## 2026-09-10 — `generate-scenes`: per-scene QC gets a prominence test, drops pixel-peeping hard-fails (superseded same day, see entry above)

- **Joe's pushback, same session**: Threadbare's scene `050` had just been
  marked FAILED for invented script-like marks on a background scribe's
  tablet — technically a real era-anchoring-negative violation, but only
  visible on a zoomed crop of a minor prop in a wide shot. "I think the QC
  check is too harsh and nobody is going to zoom in on the scribe's plaque
  to check that the scripts match the bloody era."
- **`generate-scenes/SKILL.md`'s Per-scene QC section now applies a
  prominence test** before a found violation becomes a hard FAIL: on/near
  the main subject, large in frame, or otherwise a focal point → still
  FAIL, retry policy unchanged (this still covers every genuinely damaging
  case — pyramids, mummification, crowns/cartouches, large legible text).
  Small, incidental, zoom-required-to-notice → soft note in `notes` +
  still logged to `prompt-hardening-log.md` for pattern-tracking, but the
  scene **passes**, no retry spent on it. Checking every stated negative
  against the image is unchanged — this only changes what counts as
  blocking once a violation is found.
- **`scene-prompter.md`'s `qc_checklist` field guidance updated** to ask
  the prompt's own author to flag background/incidental checklist items as
  such, so QC doesn't have to judge prominence cold.
- **The Threadbare `050` log entry itself was not retroactively
  "un-failed"** — it's an accurate record of what happened under the rule
  as it stood that day; the new rule applies going forward, addendum added
  to that entry explaining the change rather than rewriting it.

---

## 2026-09-10 — `scene-prompter`/`generate-scenes`: manifest chapter-split into 25-scenes-max files, standing rule going forward

- **Joe's call, after direct experience**: Pharaoh's Servant's
  `scene-prompts.md` had grown to 198 rows/~178KB even after the
  content_prompt/style restructure — awkward to read/edit by hand, and
  expensive for an agent to work through in one pass (hit the Read tool's
  256KB cap earlier the same day). "The whole scene-prompts document/flow
  just seems wrong, it's hammering tokens and real money."
- **Pharaoh's Servant's manifest split for real**: `scene-prompts.md` is
  now a short index (shared front matter + a chapter-range table); the 198
  rows live in `scene-prompts/level-01.md` through `level-10b.md` — one
  file per script Level, capped at 25 scenes, Level 10 (34 scenes) split
  into two 17-scene halves since it alone exceeded the cap. Pure mechanical
  split, no content changed — done directly with a script, not dispatched
  to an agent (see the 2026-09-10 memory note on filtering mechanically
  before agent dispatch).
- **Standing rule for future projects**: `scene-prompter.md` Mode 2's
  "Output" section now specifies chapter-split output from the start (25
  scenes max per file, split further if a single chapter exceeds that) —
  don't write one flat table and split it later. Mode 3 and Mode 5's
  "Inputs" sections and `generate-scenes/SKILL.md`'s intro updated to read
  the chapter index rather than assume a single table.

---

## 2026-09-10 — `scene-prompter`: Mode 5 doc corrected after a real failed dispatch (no Bash, can't execute its own "actually generate" step)

- **Found by real failure, not review**: dispatched Mode 5 three times
  (Trueline/Threadbare/Honeyline previews) expecting it to generate images
  end-to-end, per its own description and Mode 5 section ("actually
  generate the images"). All three fully prepared the run (manifest, style
  bible, character bible, `generate-scenes/SKILL.md` all read correctly)
  and then correctly stopped and reported a blocker rather than fabricate
  output: the agent's own `tools:` frontmatter (`Read, Write, Edit, Grep,
  Glob`) has no Bash/network access, so it has no way to actually call the
  Gemini API. ~218k tokens spent across the three attempts for zero images.
- **Mode 5's doc now says explicitly**: this agent can design the
  content+style merge (step 1) but whoever invokes Mode 5 must hand steps
  2-3 (actual generation + QC) to a Bash-capable agent/session — it will
  not finish the job itself. Re-dispatched successfully to `general-purpose`
  agents instead, pre-loaded with everything the three failed attempts had
  already discovered so nothing was re-derived.
- **Same edit also fixed a stale resolution reference**: Mode 5's step 2
  said "1K," left over from before the 2026-09-09 decision that moved the
  project default to 2K. Now says 2K.
- **One real, useful thing the failed Threadbare attempt surfaced anyway**:
  Threadbare's STYLE block is written for a modern urban register ("parked
  cars, utility poles and wires") that directly conflicts with this
  project's First Dynasty setting, and nothing in the existing
  era-anchoring negative catches it. Worth folding into `style-bible.md`'s
  Threadbare entry as a standing caveat if a future project actually picks
  Threadbare for an ancient/pre-modern setting — not fixed yet, just
  flagged.

---

## 2026-09-10 — `scene-prompter`: distribution self-check hardened after a real miscount on Pharaoh's Servant

- **Found by independent recount, not by the agent itself**: Pharaoh's
  Servant's Mode 2 self-check reported 41/198 (20.7%) scenes at the 9s
  ceiling, computed by grepping its own `notes`-column "Ceiling-band scene"
  tags. An actual per-row word count of every `script_bookmark` found only
  27/198 (13.6%) genuinely at or past 24 words — the `notes` tag had been
  applied during writing as a loose "long-ish" catch-all rather than a
  precise band, and the self-check never recounted before reporting.
- **Item 6 (Distribution check) now requires an actual per-row word count at
  self-check time**, never a `notes`-tag grep and never an estimate — the
  exact gap that let 41 and 27 drift apart.
- **The ~10% floor/ceiling shares are now explicitly a pacing-quality
  target, not a hard gate.** Joe's call: a share a few points over ~10%
  (13.6%, in the real case) isn't on its own grounds to re-segment, and
  re-segmenting should never come at the cost of a scene's own narration or
  delivery just to force the percentage down. Item 5's actual per-scene
  ceiling (~26 words/9s) remains the one non-negotiable constraint; a
  merely-high share gets reviewed scene-by-scene against each row's own
  justification instead.

---

## 2026-09-09 — `scene-prompter`/`generate-scenes`: style becomes a reference, not materialized text — the `prompt` column is gone

- **Joe's follow-up catch, same day as the previous entry**: even with
  style made an explicit argument, Mode 2 was still going to write a fully
  merged, self-contained `prompt` column per scene once a style *was*
  chosen — the manual-Syntx-paste discipline this was inherited from
  ("select one block, paste it, nothing missing") no longer applies now
  that `generate-scenes` assembles every request in code. Worse, a fully
  materialized `prompt` column reintroduces the exact problem
  `content_prompt` was built to solve, just deferred: a later change to a
  style's own negative list (which `prompt-hardening-log.md` is
  specifically designed to produce) would leave every already-written
  `prompt` cell stale.
- **The `prompt` column is retired.** `scene-prompts.md` now has
  `content_prompt` (the real, permanent scene content — including any
  genuinely scene-specific negative, like a text-card's stated exception)
  and a new **`style` column holding only a bare name** from
  `content/styles/style-bible.md` (empty if no style has been chosen yet
  — same "stop and ask, never default" rule as before, just one column
  over).
- **`content/styles/style-bible.md` gains a "Universal negatives"
  section** — content-correctness rules that apply regardless of chosen
  style (currently: exactly one instance of the subject, no
  duplicated/mirrored figures — moved here from `scene-prompter.md`'s own
  standing-rules list, since it's a negative-list item, not
  content-writing guidance).
- **`generate-scenes/SKILL.md`'s "Building the request" now describes the
  actual stitch**: `content_prompt` + the named style's STYLE/NEGATIVE
  (looked up once per batch, not per row) + the universal-negatives
  preamble, concatenated at generation time. Prerequisites, "What this
  skill does not do," and the frontmatter description all updated to
  match. `WORKFLOW.md` Step 5 updated too.
- Net effect: changing a project's style, or updating a style's own
  negative list mid-project, is now a one-line edit (or nothing at all,
  for the negative-list case) instead of a bulk rewrite across hundreds of
  manifest rows — the thing this whole redesign was for.

## 2026-09-09 — `scene-prompter`: style is now an explicit argument, never a silent default (Mode 1 and Mode 2)

- **Real gap Joe caught**: the Mode 2 brief used to generate Pharaoh's
  Servant's manifest defaulted `prompt` to Trueline "as a working
  placeholder" while style was still being decided — exactly the
  expensive-to-undo mistake `content_prompt` was built to prevent (a
  committed style baked into every row, needing a full rewrite if the
  choice changes). Traced to two spots in `scene-prompter.md` that still
  assumed a fallback default existed to reach for.
- **Mode 1** — "House style — check the channel-level lock first" replaced
  with "Style — an explicit argument, never a silent default." Character
  descriptions stay style-agnostic and always get locked regardless of
  style status; the reference-image generation prompt only gets built if
  a `style` argument was actually supplied — **no argument means stop and
  ask, not default to Trueline.**
- **Mode 2** — gained the same explicit-argument framing. `content_prompt`
  is always written; `prompt` is only populated when a `style` argument
  was supplied for that run, and is left explicitly empty (not
  placeholder-filled) otherwise. Output table's `prompt` row, the Mode 2
  self-check, and the frontmatter description all updated to match.
- **`generate-scenes/SKILL.md`** — Prerequisites updated: an empty
  `prompt` column is now documented as an expected, correct state (style
  not yet chosen), not an error — the skill stops and says so rather than
  inventing a style or generating anything.
- **Not retroactive** — the already-running Pharaoh's Servant Mode 2 pass
  that prompted this (launched before the fix) was explicitly left to
  finish as-is, per Joe's call; this only governs future runs.

---

## 2026-09-09 — Scene generation rebuilt on the direct Gemini API, superseding Syntx.ai — `generate-scenes` rewritten, `scene-prompter` refactored, new prompt-hardening feedback loop

**The big one.** Syntx.ai's own ToS bans the scripted access `generate-scenes`
performed, and the browser-driven pipeline never solved the rank-ladder
format's real scene count (150-300/video, 3-7x anything it was ever run
against) — see the archived version's own "Scale problem, unresolved"
section. Moved to calling the Gemini API directly instead, validated via a
real hands-on pilot on Pharaoh's Servant before any skill got rewritten
around it (this project's standing "validate small" discipline).

- **Research first, two focused passes**: (1) confirmed directly against
  Google's own docs that reference-image binding is positional-only, same
  as Syntx, just a different API shape — no rewrite forced on
  `scene-prompter`'s core reference convention. (2) A full pilot — real
  locked character references generated for Pharaoh's Servant (the servant
  protagonist, King Djer), consistency-tested across 6 follow-up scenes,
  and a real Batch API job submitted and observed end to end (846s/14.1min
  for 4 requests, 4/4 succeeded). Findings in
  `research/artifacts/archive-style-bible-validation.md` and this session's
  own pilot output (`content/watcher-pov/pharaohs-servant/claude/pipeline-pilot/`).
- **`generate-scenes/SKILL.md` — fully rewritten.** Old Syntx-era content
  archived in full at
  `research/artifacts/archive-generate-scenes-syntx-era.md` (not deleted —
  real hard-won UI-automation knowledge, kept in case ever needed again).
  New version: direct `generateContent`/`batchGenerateContent` calls,
  model tiering (NB2 default, Lite for text-cards, Pro as escalation), the
  confirmed batch request/response schema (including the
  `response.inlinedResponses.inlinedResponses[]` nesting gotcha), and —
  the one genuinely new operational requirement — **async batch waiting via
  a backgrounded Bash command with its own exponential-backoff poll loop
  (30s→5min ceiling), never a live tight poll loop**, per Joe's explicit
  instruction not to have an agent hammering `GET` every 30 seconds.
  Per-scene QC and the two-tier retry policy (plain retry, then one
  targeted tweak, then stop at three attempts) carry forward unchanged in
  structure — the pilot confirmed reference conditioning fixes identity
  drift but not content/negative-prompt compliance, so QC stays mandatory
  regardless of generation method. Batch throughput at real production
  scale (150-300 scenes) is explicitly flagged as untested, not assumed.
- **New: `content/watcher-pov/prompt-hardening-log.md`.** A channel-level,
  append-only log of real QC failures — what a prompt asked for, what the
  model actually did, and the concrete fix — pre-populated with three real
  findings from the pilot, two already promoted into `scene-prompter.md`
  Mode 2 as standing rules: **every on-screen character needs at least a
  minimal era/style constraint**, not just locked leads (an unconstrained
  "steward" rendered as a Greco-Roman toga figure — the single most
  important finding of the pilot), and **"exactly one instance, no
  duplicated/mirrored figures" is now a standing negative** (a text-only
  regeneration produced three copies of the same person in one frame). Two
  more logged but not yet promoted (crowd-figure cloning, rank
  under-differentiation) pending a second occurrence. `generate-scenes`
  writes to this log on every QC failure; `scene-prompter` reads it before
  writing prompts for a new project.
- **`scene-prompter.md` — Mode 5 (STYLE PREVIEW) corrected the same day it
  was added.** First version output a prompt *document*; Joe's actual ask
  was rendered comparison *images*. Now: merges `content_prompt` with a
  named style, actually generates via `generate-scenes`'s mechanism, saves
  real image files to a disposable `style-previews/<Style>-scenes-<range>/`
  folder — never touches the real manifest. Also gained the two promoted
  standing rules above, a note that a bare character name is safe as
  reinforcement (not a replacement for positional phrasing), and
  `prompt-hardening-log.md` as a standard Mode 2/5 input.
- **`WORKFLOW.md` Step 5 rewritten** to match — tool, model tiers, the new
  skill mechanics, and a flagged-not-fixed inconsistency in Step 6
  (thumbnails still describe generating "in Syntx.ai, in the same style
  preset as the scenes," which is now stale since scenes no longer come
  from Syntx — out of scope for this pass). The backlog's own
  Artlist.io-vs-Syntx throughput item updated to reflect what actually
  happened (direct API, not Artlist).

## 2026-09-09 — `scene-prompter`: new Mode 5 (STYLE PREVIEW), `content_prompt` column split from `prompt`

- **Real gap Joe hit**: with the style bible now holding several candidate
  styles and no fixed channel default (see the same day's style-bible
  cleanup), Mode 2's scene prompts baked one committed style verbatim into
  every row — there was no way to see a range of scenes rendered in a
  *different* candidate style without redoing the whole manifest.
- **Mode 2's output table gains a `content_prompt` column** — the
  style-agnostic version of each row's prompt (composition, action, camera
  framing, character-by-position, text-card wording), with `prompt` itself
  now defined as `content_prompt` + a merged-in style block, not written
  independently. No change to `prompt`'s own contract (still fully
  self-contained, still what `generate-scenes` reads) — this only exposes
  the content half separately, on the same row.
- **New Mode 5 — STYLE PREVIEW.** Takes an already-generated
  `scene-prompts.md`, a named style from `content/styles/style-bible.md`,
  and a scene range (e.g. "1-15") — outputs a disposable comparison file
  (`claude/style-previews/<StyleName>-scenes-<range>.md`) with that range's
  `content_prompt`s merged with the chosen style, same column shape as the
  real manifest (so it's a drop-in `generate-scenes` input if Joe wants to
  actually render the comparison, not just read the prompt text). Never
  touches the real manifest — rerunning it for a different style on the
  same range is the normal way to compare candidates side by side. Once a
  style is picked, rebuilding the real manifest's `prompt` column from the
  winner is a Mode 3 (REVISE) job, not this mode's.
- **Self-check gained one new item** (content/style split stays clean, no
  style language leaking into `content_prompt`) and the frontmatter
  `description` now covers Mode 5.

## 2026-09-09 — `plan-ken-burns` and `apply-ken-burns`: Joe's horizontal-pan style preference logged

- **Both skills — small addition, not a structural change.** Joe stated a
  standing aesthetic preference: slow, full-scene-duration horizontal pans
  (left→right or right→left), explicitly no zoom paired with them.
  - `plan-ken-burns/SKILL.md`: noted as an independent signal for Pan
    candidacy (alongside, not replacing, the existing "multiple sequential
    elements" signal) under "Candidate discovery," and spelled out under
    "Elevated assignment" — still counts against the existing ~10% Elevated
    ceiling, direction gets recorded explicitly in the plan's `Note` column.
  - `apply-ken-burns/SKILL.md`: added a note on the Pan step clarifying what
    "no zoom" means mechanically (no *animated* `Size` change — the existing
    static `Size > 1.0` headroom scale-up is still required and doesn't
    count as a zoom) and keeping `y1 == y2` for a purely horizontal move.
    Flagged as **not yet empirically confirmed** which `Center` X direction
    reads as "pans right" on screen — verify with the screenshot/Inspector
    check the first time this style is actually executed, then update the
    note with the confirmed mapping.

## 2026-09-08 (tenth pass) — `plan-ken-burns` overhauled: three-tier scene treatment, delegated image verification

- **`plan-ken-burns/SKILL.md` — significant rewrite**, prompted by Joe
  wanting the skill to actively use the automation now proven in
  `apply-ken-burns`/`apply-particles` rather than just flag things for
  manual handling:
  - **Static tightened to text-card/papyrus scenes only** — the 4s-floor
    illustrated-scene carve-out (added the same day, in the eighth pass)
    is dropped; it never had independent evidence and directly contradicted
    the competitor-footage finding that flipped the rule to motion-by-default
    in the first place ("motion runs on nearly every scene, including short
    ones"). The ~10% cap stays as a backstop, expected to rarely bind now.
  - **New three-tier system**: Baseline (plain In/Out, the default),
    Elevated (Pan/Focal-Point Zoom on a confirmed target, ~10% ceiling,
    executed via `apply-ken-burns`), and FX-candidate (Fusion particle/glow
    suggestions, flat 5-scene cap, **suggestion-only** — this skill never
    executes FX, deliberately, since `apply-particles` is proven on exactly
    one effect so far; scaling to auto-execution is a future call once
    there's a second confirmed case). Precedence when a scene qualifies for
    more than one: FX-candidate > Elevated > Static.
  - **New candidate-discovery process**: a cheap text-only pass over the
    script/manifest shortlists candidates by prompt-text signal (off-center
    detail, multi-element composition, environmental light/fire source),
    then — per CLAUDE.md's token-hygiene rules — **only the shortlist**
    gets its actual scene image read, delegated to subagents in small
    batches (same pattern `generate-scenes`' QC already uses), which return
    a compact confirmed target coordinate or FX description rather than
    raw image tokens entering the main planning thread. This replaces the
    old blanket "never views generated images" rule with a narrow, scoped
    exception.
  - **New finding folded in**: transitions (the black-sweep effect this
    skill already planned) cannot be added via Resolve's scripting API at
    all — confirmed by reading the `davinci-resolve` MCP server's source
    directly (a comment on unrelated code already independently hit this
    wall: *"Resolve's public scripting API does not expose timeline item
    transition cloning"*). Documented as a **permanent** manual step, not
    a "not yet automated" gap. Full evidence trail in `research/inventory.md`
    §2b.
  - Output table gained an `FX` column and a stricter `Note` format
    (confirmed target coordinates for Pan/Focal, visual description +
    template pointer for FX-candidates).
  - Considered and **rejected**: renaming the skill to "claude-spielberg"
    (Joe's own joke pitch) — every other skill in this repo is plainly
    task-named and this one's cross-referenced by name in three other
    files; kept as `plan-ken-burns`.

## 2026-09-08 (ninth pass) — new `apply-particles` skill: environmental particle effects confirmed WORKING

- **New skill: `apply-particles`** (`.claude/skills/apply-particles/SKILL.md`).
  Drives Resolve via the same `davinci-resolve` MCP server to build ambient
  Fusion particle effects (dust, embers, sparks) — raw-primitive
  `pEmitter → pRender → Merge` (Screen) build, since `group_settings_load`
  needs a pre-existing named group and can't insert one from a `.setting`
  file. Built and tuned live against a real scene (Tomb Robber scene-01,
  dust drifting through a doorway light beam) through a 14-step iteration
  log (full detail in `research/inventory.md` §2b), landing on a locked
  recipe: `ParticleStyleBlob` (not `Line`, which draws direction-scaled
  streaks — wrong for ambient dust) as the starting style, and the key
  finding — a convincing directional "cone" needs a **small near-point
  source positioned at the effect's true origin plus a nonzero
  `AngleVariance`**, not a source region shaped to match the target
  spread (`AngleVariance` defaults to `0`, so without it every particle
  travels in an identical direction regardless of spawn point). Also
  documents two confirmed sign-flip traps (`RectRgn.Rotate.Z` region tilt,
  `pEmitter.Angle` travel direction — both needed the negative of the
  first guess) and a dead-end (`RectRgn.Angle`/`RectRgn.Rotation` silently
  no-op; the real input, `RectRgn.Rotate.Z`, was only found via
  `probe_fusion_tool`'s full input dump). Joe generalized the pattern
  beyond this one scene (doorways, torch/fire embers, etc.) once locked in.
- **`apply-ken-burns/SKILL.md`** — the "particle effects: not yet tested"
  row/note updated to point at the new sibling skill instead.

## 2026-09-08 (eighth pass) — `apply-ken-burns` fully rewritten: automation confirmed WORKING (zoom, focal-point zoom, pan)

- **`apply-ken-burns/SKILL.md` — rewritten from "BLOCKED" to a confirmed
  working recipe.** The render blocker from the previous pass (§ below)
  was filed upstream as
  [issue #196](https://github.com/samuelgursky/davinci-resolve-mcp/issues/196)
  and fixed by the maintainer the same day (v2.213.1/2, `StartUndo`/
  `EndUndo` around the keyframe write). Pulled and re-verified rigorously
  with real renders + `ffmpeg` SSIM/PSNR, not just API calls. Extended
  the same day to two new proven capabilities: **focal-point zoom**
  (`Pivot`, set statically, not `Center`) and **pan** (`Center` keyframed
  with `modifier: "XYPath"`, not `"Path"`). Documents two new real traps
  found along the way — a Point3D value-format bug (`set_input`/
  `add_keyframe` on `Center`/`Pivot` need a plain array `[x,y,z]`; object/
  dict forms silently no-op) and a multi-comp GUI-sync trap (a clip can
  carry more than one Fusion comp; the GUI doesn't reliably show the one
  the API is editing, and doesn't follow `timeline.set_current`) — plus a
  reusable Windows screenshot-capture technique (PowerShell +
  `user32.dll` `PrintWindow`/`PW_RENDERFULLCONTENT`) for fast iteration
  without rendering every time. Particle effects remain an untested
  stretch goal. Full evidence trail in `research/inventory.md` §2b; the
  skill itself only carries the operational recipe.
- **`plan-ken-burns/SKILL.md` — description and scope note updated back**
  to point at `apply-ken-burns` as a real, working automated-execution
  option (previously marked blocked as of the seventh pass, below).

## 2026-09-08 (seventh pass) — new `apply-ken-burns` skill: Resolve MCP automation attempted, currently BLOCKED

- **New skill: `apply-ken-burns`** (`.claude/skills/apply-ken-burns/SKILL.md`).
  Attempts to drive a running DaVinci Resolve Studio via the
  `davinci-resolve` MCP server (`tools/davinci-resolve-mcp/`, installed
  2026-09-07) to build the Fusion-comp-based Ken Burns motion a
  `ken-burns-plan.md` describes, instead of the editor keyframing every
  scene by hand. **Same-day correction**: this looked confirmed-working
  after a rendered 5-scene test video passed `render.verify_output`, but
  Joe actually watched that video and saw no zoom at all — a real,
  material finding that overturned the earlier verification. Direct
  `ffmpeg` inspection of the rendered file (not any Resolve API call)
  confirmed animated Fusion keyframes never reach a real render, even
  though they're provably correct via the API, via Fusion's own live
  playback, and via `project_settings.export_frame_as_still` — none of
  which turned out to be trustworthy proof of actual render content. A
  static (non-keyframed) Fusion effect DOES render correctly, isolating
  the blocker precisely to keyframed/animated parameters. **Skill is kept
  as documentation of what's proven vs. blocked, not as a usable
  automation path** — marked accordingly in its own frontmatter. Also
  documents the real environment gotchas found along the way
  (no-active-page media-import no-op, OneDrive import failures, unstable
  headless launch) and that `timeline_item`'s Inspector-level keyframe
  actions are separately, genuinely broken (crash on every Resolve/Python
  combination tested). Full validation history — including two separate
  false "confirmed working" conclusions in one day, both later
  overturned — stays in `research/inventory.md` §2b.
- **`plan-ken-burns/SKILL.md` — description and scope note updated
  accordingly.** Still only plans, never executes; the `apply-ken-burns`
  sibling exists but isn't currently usable for real automation, so
  applying a plan by hand remains the only proven path.

## 2026-09-08 (sixth pass) — `text-card` rows now generated through Syntx, not skipped

- **`generate-scenes/SKILL.md` — dropped the "skip `text-card` rows" rule.**
  Every manifest row now goes through the identical generate → QC → retry
  flow regardless of `scene_type`; the old "text-card = free Resolve
  graphic, never sent to Syntx" default is gone. This formalizes what Tomb
  Robber's own production already did in practice for its three text-card
  beats (`scene-prompts.md`, 2026-09-03) — a plain Resolve title didn't
  match the papyrus house style closely enough, so they went through Syntx
  like every other scene, as a scoped one-off at the time. That's now the
  standing default for every project. Mechanically: step 2 (attach
  reference images) is skipped when a row's `reference_images` column is
  empty, which is the normal case for a `text-card` row (a card is an
  object, not a person). Added a "Text-card rows" subsection under Per-scene
  QC calling out the check that matters most for this row type: AI image
  models render legible text unreliably, so the QC pass must read the
  rendered line back character-for-character against the prompt's quoted
  text, not just eyeball it as "looks textish" — and flagged that
  `text-card` rows should be expected to need retries more often than
  `illustrated` ones for exactly that reason.
- **`scene-prompter.md` Mode 2 — `prompt` is now required for every row,
  `text-card` included**, with its own discipline: a single era-appropriate
  physical object (papyrus, stone tablet, painted sign, etc.) bearing
  **exactly one line of legible text, quoted verbatim in the prompt**, with
  an explicit, flagged override of the house style's usual "no modern text
  or logos" negative for that one line only (the same kind of deliberate,
  written-down override as the mascot's browless-eyes exception to Preset
  C's face default). `characters_present / reference_images` is expected
  empty for most `text-card` rows rather than treated as a gap.
  `qc_checklist` swaps "character consistency" for a text-accuracy item on
  these rows — the exact line quoted, with an explicit "no other text/marks
  anywhere else on the card" clause.
- **`WORKFLOW.md` Step 5** — updated its `generate-scenes` bullet to state
  plainly that `text-card` rows are no longer skipped, pointing at the
  skill's own doc for the mechanical detail rather than restating it.

---

## 2026-09-08 (fifth pass) — mascot lock reflected in docs; Mode 4 retired in favor of inline per-scene QC + retry policy

- **`scene-prompter.md`, `character-bible.md`, `watcher-concept.md` — mascot
  status updated from "not yet locked" to locked.** The Watcher's Mode 1
  reference image (`Mascot-TheWatcher-BareReference.jpg`) was regenerated
  from the corrected (light grey/green-tinted skin) prompt block and saved
  to `content/watcher-pov/mascot/reference-images/`. `scene-prompter.md`'s "Channel
  mascot" section, which previously said this wasn't true yet as of
  2026-09-06, now points at the locked bible entry directly. No mechanic
  changed — this is a status update, not a rule change.
- **`scene-prompter.md` — Mode 4 (AUDIT) retired.** Per-scene visual QC
  against the bible no longer runs as a standalone, after-the-fact batch
  audit inside this agent. Reasoning: `generate-scenes`' subagents already
  `Read` every generated file to confirm it downloaded correctly, so running
  the same character/script/background comparison there reuses a read that's
  already happening, instead of paying for a second full-batch re-read once
  an entire manifest is done — and a caught problem can be retried
  immediately rather than surfacing as a punch-list item after the fact. The
  agent's frontmatter `description` and self-checks updated to match; a
  short "Mode 4 — retired" note replaces the old mode body, pointing at
  where the check actually lives now.
- **`scene-prompter.md` Mode 2 — `script_bookmark` now captures the full
  verbatim scene span, not just its opening words**, and a new `qc_checklist`
  column is written after `notes` on every manifest row — this scene's own
  scene-specific, checkable sign-off criteria (character consistency against
  named reference images, whether the image matches the actual moment in
  `script_bookmark`, background/setting adequacy, plus scene-specific extras
  like the mascot cameo line). This is what `generate-scenes`' new per-scene
  QC pass checks each image against, replacing the retired Mode 4's
  from-memory comparison with criteria written down in advance.
- **`generate-scenes/SKILL.md` — gained per-scene QC and a retry policy
  (`maxRetries = 2`), the two retries deliberately asymmetric.** The skill
  now owns the visual QC judgment call previously done in `scene-prompter`'s
  Mode 4: each generation attempt is checked against the manifest row's
  `qc_checklist` immediately after download, from the local file. **Retry 1
  (attempt 2) is a plain repeat** — identical prompt and reference
  attachments, no tweaking — preferring a native Syntx "Retry"/"Regenerate"
  control if one exists (unverified as of this pass; falls back to manually
  retyping the unchanged prompt if not). **Retry 2 (attempt 3), reached only
  if the plain retry also fails, is a targeted prompt tweak** the generating
  subagent makes itself, scoped strictly to whichever `qc_checklist` item(s)
  are logged as failing on the first two attempts — not a free rewrite, and
  not reached before the plain retry has been tried. Attempts are saved as
  numbered `<scene_id>_1/_2/_3.jpg` files (never overwritten, kept as the
  audit trail, with a one-line note on what attempt 3's tweak changed and
  why), and only a passing attempt gets copied to the canonical
  `<scene_id>.jpg` that downstream steps (Ken Burns planning, Resolve
  import) already expect. A scene that fails all three attempts is recorded
  **FAILED** in the batch summary, with which `qc_checklist` item failed on
  each attempt logged per-attempt, rather than retried indefinitely; the
  resume logic (skip if the canonical file exists) was extended so a batch
  re-run doesn't silently re-attempt an already-exhausted scene a 4th time,
  and resumes at the correct retry kind (plain vs. tweaked) for whichever
  attempt number it left off at. Subagent batching instructions updated to
  report pass/fail-by-attempt per scene rather than a flat pass/fail. **This
  asymmetric split itself is logged as still open** (`research/inventory.md`
  §5 backlog) — real batches under the policy will show whether the plain
  retry is worth keeping ahead of the tweak, or whether the order should
  change; not re-decided here, just checkable once the data exists.
- **`WORKFLOW.md` Step 5, `CLAUDE.md`'s token-hygiene section,
  `research/inventory.md`, `syntx-model-test-plan.md` — Mode 4 references
  updated to match.** Step 5's agent/skill bullets now describe three
  `scene-prompter` modes (not four) and note `generate-scenes`' new QC/retry
  ownership; `CLAUDE.md` dropped its now-redundant "delegate Mode 4 batches"
  bullet (subsumed by `generate-scenes`' existing subagent-batching pattern,
  which already covers this); the two cost-projection docs' "Mode 4 (Audit)
  re-generations" buffer line now names the successor (`generate-scenes`'
  retry policy) instead of a retired mode. Per-project historical bible/
  manifest files (Tomb Robber, Legion Marching) were **not** rewritten — they
  correctly record what those specific runs actually did under the
  since-retired process, the same convention already used for e.g.
  `watcher-concept.md`'s Test 1-3 teal-grey renders.

---

## 2026-09-08 (fourth pass) — channel voice locked, pacing figures rebaselined

- **`scene-prompter.md`, `script-writer.md`, `plan-ken-burns/SKILL.md` — all
  three rebaselined from ~145wpm/2.4wps to ~171wpm/2.85wps.** Following a
  5-voice pacing calibration (`content/watcher-pov/voice-register.md`), Joe locked
  **Jim** (deep British baritone) as the channel's voice, confirmed at
  170.9 wpm / 2.85 words/sec on a real full-script generation. This
  replaces a figure that had been silently wrong since 2026-09-05 or
  earlier — it traced back to "Roger," a voice tested once in the original
  2026-08-31 comparison and never actually used in production (Tomb
  Robber shipped with a different voice entirely, "A Top Narrator VO
  PRO"). Concretely: `scene-prompter.md`'s floor/average-range/ceiling word
  counts moved from ~10/~12-19/~22 words to ~11/~14-23/~26 words (durations
  themselves — 4s/5-8s/9s — are unchanged, only the words-per-duration
  conversion moved); `script-writer.md`'s runtime-target word count moved
  from ~2,900-3,600 to ~3,400-4,300 words for the same 20-25 min runtime,
  since a faster voice needs more script to fill the same time;
  `plan-ken-burns/SKILL.md`'s restated copy of the same numbers updated to
  match. No rule, ceiling, or cap *percentage* changed — only the
  underlying wpm the word-count math is built on.
- **`WORKFLOW.md` Step 7 — status changed from 🟡 to 🟢, voice locked.**
  Rewritten to state Jim as the confirmed voice with its measured pace,
  and to flag two things explicitly left open rather than assumed
  resolved: which exact platform Jim was found/generated on (never
  explicitly confirmed in chat), and that the stock-voice-fingerprinting
  concern raised during testing still technically applies to Jim same as
  any non-cloned voice — the Liverpool-clone plan is kept as the
  structural fix for that specific risk, not treated as superseded by
  locking a fast stock voice.

---

## 2026-09-08 (third pass)

- **`scene-prompter.md` — segmentation numbers revised again, against a
  second direct review of POVrank's CCP video.** The 2026-09-07 numbers
  (3s floor, 5s target average, 8s ceiling, ≤15% in the 7-8s band) are
  replaced: **4s floor, 5-8s average range (a band, not a single target),
  9s ceiling**, with **symmetric ≤10% caps at both the floor and the
  ceiling** rather than a ceiling-only cap. Updated everywhere the old
  numbers appeared: the hard-ceiling rule, the word-count-proxy table, the
  distribution rule, the manifest's `scene_type`/`notes` column
  descriptions, and both self-check items (#5 ceiling check, #6
  distribution check). Word-count equivalents recomputed at the same
  ~145wpm/2.4 words-per-second rate already used elsewhere (4s≈10 words,
  9s≈22 words). `plan-ken-burns/SKILL.md`'s restated copy of these numbers
  (added 2026-09-08, second pass) updated to match in the same session —
  including its own floor-band Static-eligibility rule, which used to read
  "3-4s" and now reads "the 4s floor" now that floor and average-range are
  adjacent rather than separated by a gap band.
- **`script-writer.md` — dropped "with uncertainty preserved rather than
  smoothed away" from the opening differentiator statement.** Joe's read:
  it branded *uncertainty itself* as the product, when the actual
  differentiator (already stated in the same paragraph — "being right when
  everyone else is approximately right") is rigor/honesty, with
  false-confidence-avoidance as the mechanism, not the headline. The
  underlying mechanism this phrase was summarizing — the "Preserving
  uncertainty" section, the G4 hedge-integrity gate, "hedges are content"
  — is untouched and still confirmed valid (it governs real contested
  facts, a different layer from Category B's composite/invented
  individual narrative, so there's no conflict with this session's A/B
  work). This was a phrasing fix, not a substance change.

## 2026-09-08 (second pass)

- **`plan-ken-burns/SKILL.md` — reversed the Static-by-default rule from
  2026-09-07; it was wrong.** That version reasoned from cut-rate math
  alone (~150-300 scenes is a lot of manual work, so default to static)
  without checking real footage. Joe reviewed actual competitor video
  frame-by-frame and found Ken Burns motion runs on nearly every scene —
  static is rare, not the norm. Corrected: **motion is now the default**;
  Static is capped to two cases only (text-cards, and scenes in the 3-4s
  floor band), never exceeding ~10% of a video's scenes. Restated the
  scene-length weighting numbers (3s floor/~7w, 5s target/~12w, 8s
  ceiling/~19w, ≤15% in the 7-8s band) directly in the skill since Ken
  Burns planning needs the same figures scene-prompter.md already uses.
  Also added a **new black-sweep transition** decision (~0.5s gradual fade
  to black, ~1 in 10 scenes, at deliberate beat-boundaries) — a new output
  column and a narrow, explicit carve-out from the skill's usual "doesn't
  decide transitions" boundary, since Joe wants this one specific effect
  planned rather than left to manual assembly-time judgement.
- **`WORKFLOW.md` Step 8 — updated to match**, replacing the now-wrong
  "static by default" summary with the corrected motion-default framing
  and a mention of the new black-sweep transition.

---

## 2026-09-08

- **`WORKFLOW.md` — feedback refactor pass after Joe read the whole file
  end to end.** Ten changes, all mechanical/process fixes, no new content
  decisions:
  1. Step 1's competitor-clash check now has a **freshness rule** — reuse
     the index within ~1 week, otherwise flag staleness and ask before
     re-polling, rather than silently re-spending credits.
  2. Step 1's comment-mining pass now **logs which videos got mined
     against the concept in `concepts.md`**, and Step 3's comment-mining
     pass checks that log first — the same video's comments never get
     polled twice. Cost noted inline (5 credits/call) per Joe's question.
  3. Step 1 gained a **per-candidate TLDR** requirement (~50-100 words,
     pre-research) so concepts can be compared by story shape, not just
     breakout score.
  4. Step 3.5 reframed to explicitly distinguish itself from that new
     per-candidate TLDR — it's the deeper, post-research, single-concept
     gate, not a duplicate of the same idea.
  5. **New transcript-breakdown cache** (`research/artifacts/transcripts/`,
     `index.md` + one file per video) — Step 3 item 3 and Step 4a both
     check it before pulling `vidiq_video_transcript` again, closing the
     double-pull Joe spotted. Deliberately stores a **paraphrased
     breakdown, never the verbatim transcript** — caching someone else's
     narration at length would be reproducing copyrighted material; a
     breakdown (the same pattern as `video-breakdown-povrank-egypt.md`) is
     the legitimate version of this.
  6. Step 4b's mandatory fact-check pass now explicitly states it doesn't
     conflict with Category B's inference allowance — it checks structural
     facts to full rigor and checks that composite elements are correctly
     flagged as such, never that a B-script's individual traces to one real
     person.
  7. Removed three Step 5 bullets that were commentary, not process (the
     "animation quality isn't the differentiator" aside, the now-resolved
     style-farmer per-concept comparison, the style-commitment window) —
     Preset C is locked, so per-concept style comparison is dead process.
  8. Step 8 changed from "researched, staged recommendation" to confirmed
     — Tomb Robber was actually produced in Resolve with Ken Burns and
     Fusion particle effects, this isn't a recommendation to validate
     anymore.
  9. Backlog: dropped the competitor-titles-index item (done), corrected
     the voice-register item now that the voice identity is confirmed.
  See `research/inventory.md` for the one real content resolution behind
  this pass (Tomb Robber's actual shipped voice).

---

## 2026-09-07

- **`WORKFLOW.md` Step 1 — Category A broadened; comment-mining wired in
  (second pass, same day as the full rewrite).** Joe caught that Oddlet's
  "Your Life After a $500,000 Medical Emergency" opens on "Level 1" and
  ladders through chapters despite having no organizational rank at all —
  Category A was too narrowly scoped to "your life as a role." Broadened to
  cover any narrative framing where levels are chosen for pacing (as a
  role / after an event / during a situation), with an explicit instruction
  to try a promising thread against multiple framings rather than defaulting
  to the first one. Also wired in `vidiq_video_comments` — a 2026-09-04
  finding that sat unimplemented ("neither use is built into WORKFLOW.md
  yet") — as a real step in both Step 1 (comment-mining for concept signal)
  and Step 3 (comment-mining for what the script should address), rather
  than an ad hoc habit.
- **`WORKFLOW.md` — full rewrite for conciseness and current-state accuracy
  (Joe's request: "WORKFLOW 2.0").** The file had accumulated dated
  decision-journey narrative (three-way tool tests, "guide correction"
  callouts, Sollo comparisons) alongside the actual process, making it hard
  to read as a straight how-to. Rewrite strips journey narrative throughout
  (pointing to `research/inventory.md`/`CHANGELOG.md` instead of restating
  it) and substantively reworks three steps:
  - **Step 1** now classifies every concept as **Category A** ("your life as
    a role" — levels are narrative/pacing constructs) or **Category B**
    ("every rank within a system" — levels are a real hierarchy's actual
    named tiers, dictated by the system, not chosen for pacing). Both use
    `script-writer.md`'s same rank-ladder structure — confirmed by
    rereading it, this isn't a ladder-vs-non-ladder split. Category B's
    factual-correctness bar is explicitly lower on the *individual's
    journey* (understood as an inferred composite) while staying full-rigor
    on the *real structure* — verified against POVrank's "Every Rank in the
    Chinese Communist Party" (2026-09-06) transcript, which does exactly
    this and discloses it. Added a required **competitor title-clash
    check** against a new `research/artifacts/competitor-titles-index.md`
    (scaffolded, not yet populated).
  - **Step 3** dropped the dead Sollo-structured-input backlog item and the
    Sollo-only PDF-export requirement (script-writer.md takes the `.md`
    directly — confirmed by rereading its Inputs section); the beats-output
    rule now forks explicitly by category (one beat/60-90s for A; one entry
    per real rank, structural facts + composite story beats, for B).
  - **Step 4** clarified that 4a's delivery-style check, Step 1's new
    title-clash check, and Step 3's well-trodden-angle check are three
    distinct VidIQ-driven checks, not overlapping steps — and that 4a should
    reuse Step 1's competitor identification rather than re-discovering it.
    4b dropped the three-way Sollo/VidIQ test narrative down to a plain
    tool statement.
  - **Steps 5, 6, 8** got dead-tool-reference fixes (Sollo → Syntx.ai, since
    Syntx is the confirmed current scene/thumbnail tool) and Step 8 now
    points at today's `plan-ken-burns` selective-motion rewrite instead of
    assuming universal Ken Burns.
  - **Step 7 was first flagged, then corrected same day**: initially
    flagged as an unresolved discrepancy (recommendation says Sollo,
    thought-shipped-audio was VidIQ's "Roger"); Joe corrected the actual
    tool — **Syntx.ai**, which has ElevenLabs voices built in — so Step 7
    now names that directly instead of recommending a vendor, and points at
    a new `content/watcher-pov/voice-register.md` (which voice went on which video)
    rather than assuming consistency.
  See `research/inventory.md` for the full reasoning and the transcript
  fact-check.
- **`scene-prompter.md` — title and description updated for the channel
  rename.** The channel is now Watcher POV, not HistoryPOV (see
  [research/inventory.md](research/inventory.md) for the full decision —
  this entry only covers the agent-file mechanics). Updated: the H1 title
  ("Watcher POV scene prompter") and the frontmatter `description` field.
  No behavioral change — every mode, rule, and self-check is unaffected;
  this is a naming-only edit that landed as part of a repo-wide rename
  sweep alongside the mascot's own rename (Newcomer → Watcher, a content
  decision, logged in `research/inventory.md` not here).
- **`WORKFLOW.md` — Step 9 (Publication) placeholder gained a pointer to
  drafted channel-description copy.** New "TBC — channel 'About' copy and
  the Watcher hook" note pointing at `content/watcher-pov/mascot/watcher-concept.md`'s
  viewer-facing copy section, so the draft isn't orphaned by the time this
  step actually gets built out.
- **`plan-ken-burns/SKILL.md` — motion made selective, not universal
  (Phase 3 of the pivot plan).** Built originally against Tomb Robber's
  ~45-scene manifest, where near-every scene was a viable motion candidate.
  The rank-ladder format's ~150-300 scenes/video at the same ~5-8s/scene
  target makes that the wrong default — most scenes are on screen too
  briefly for a move to register, and the cut rate itself should carry the
  rhythm. Added: a new "Motion is selective, not universal" rationale
  section; a "Static vs. motion — decide this first" gate ahead of the
  existing Direction/Ease rules, defaulting to Static unless a scene is an
  act opening, a reveal, an act closer, or already explicitly held past the
  norm; a `Static` value in the output table's `Zoom` column, documented as
  the expected common case rather than a fallback; and the `Variance` rule
  rescoped to apply only among scenes that already cleared the static/motion
  gate. No change to the Resolve Dynamic Zoom constraints or per-scene
  Direction/Ease logic itself — those are unaffected by scene count.
- **`generate-scenes/SKILL.md` — flagged the batching math as stale, not yet
  fixed (Phase 3 of the pivot plan).** New "Scale problem, unresolved"
  section: the existing 5-8-scenes-per-subagent batching manages a
  subagent's own context cost, not total throughput, and a 150-300 scene
  manifest still means 20-40+ sequential subagent dispatches (parallel
  dispatch onto one shared Chrome tab remains unverified and risky, per the
  skill's own existing caution). This was already flagged as "too slow to
  scale" at 45 scenes, before the format change made per-video scene counts
  several times larger — the skill now says so explicitly rather than
  leaving a reader to infer it. Points at `research/inventory.md` §2h's
  still-open Artlist.io MCP alternative as the recommended next step (a
  small validation batch, per the project's own Sollo lesson), without
  deciding that question here — this is a documentation flag, not a
  pipeline switch.

---

## 2026-09-06

- **`scene-prompter.md` — two additions: a channel-level style pointer, and
  the mascot easter-egg mechanic.** (1) Mode 1 now checks
  `content/styles/style-bible.md` for the channel's confirmed rendering
  register (Preset C, "Trueline") before a new project invents its own §0
  house style from scratch — promotes house style from per-project to
  per-channel, matching how Tomb Robber and Legion Marching's own styles
  were previously each invented independently. Tomb Robber and Legion
  Marching keep their existing styles unchanged; this only governs new
  projects. (2) Mode 2 gained a new segmentation rule: once a channel
  mascot is locked (not yet true — "the Watcher" in
  `content/watcher-pov/mascot/watcher-concept.md` is still a design sketch, not an
  audited Mode 1 bible entry), every video places it in **exactly one**
  scene, chosen by this agent, dense enough to hide it in, fully costumed
  to match the surrounding cast, and positioned as one of the group rather
  than beside it — a genuine *Where's Wally* easter egg, not a visible
  recurring character. Added as self-check #7. Written after a live test
  (Legion Marching's marching-column scene) staged this wrong — the
  candidate mascot rendered nude and standing apart from the column,
  watching it rather than blending into it — which is exactly the failure
  mode these rules rule out.

- **`scene-prompter.md` — added a channel-level character pattern, for the
  mascot specifically.** Mode 1 as originally written assumes a
  per-project research file and a per-project bible location; the channel
  mascot has neither (he isn't tied to any one video's research). New
  section documents the substitute: bible lives at
  `content/watcher-pov/mascot/character-bible.md` rather than nested in a project, and
  the design's own validation record (`watcher-concept.md`'s locked
  tokens and test results) stands in for a research file, labelled
  `[INVENTED — locked by design testing, not by research]` rather than
  reaching for a sourcing label that doesn't apply to a fictional alien.
  Runs once, standalone, not gated on any video existing yet.
- **The Wanderer dropped as a mascot candidate; "the Watcher" confirmed.**
  Both `content/styles/style-bible.md` and `watcher-concept.md` updated
  — Presets A/B marked dead/historical-reference-only (built around a
  visible-protagonist premise the easter-egg reframe eliminated), the
  Watcher's status changed from "a second candidate" to "the confirmed
  mascot, pending its Mode 1 pass."

---

## 2026-09-05

- **`scene-prompter.md` — added a hard 8-second hold ceiling and a distribution
  rule to Mode 2's segmentation.** Fixes the concrete Tomb Robber failure: it
  shipped scenes holding for **33 seconds** despite a stated 5-8s soft target,
  because every rule in the agent pushed scene count *down* (hold-by-default, a
  merge-only self-check, "not every beat needs a new scene") and nothing ever
  forced a cut. Added: an 8s hard ceiling with a word-count proxy (~145wpm ≈ 2.4
  words/sec, measured from this channel's own narration, so ~19 words = 8s); a
  target average of ~5s; a cap of ~15% of scenes in the 7-8s band with mandatory
  `notes` justification for each; a ~3s floor so this doesn't overcorrect into
  frantic cutting. Added self-check #5 (split-only, the counterweight to #4's
  merge-only pass) and #6 (distribution check, reported when handing back the
  manifest). Reframed `text-card` scenes from a cost saving into the cheapest
  way to hold pace under the ceiling. Corrected the POVrank rationale that
  justified unbounded holding — competitor evidence since gathered shows the
  125k-view genre breakout runs ~17 cuts/min.

- **`script-writer.md` — pivot changes: any-topic scope, rank-ladder format,
  runtime targets, composite-archetype sourcing, ladder-aware opening.**
  Added: the rank-ladder format spec (8-10 numbered levels, per-level beat
  template, rise-then-fall arc, personal thread under the ranks, cyclical
  close); runtime targets of 20-25 min / ~2,900-3,600 words at 145wpm (the file
  previously had **no** length target at all, part of why Tomb Robber came in at
  ~13 min against a genre running twice that); the **composite-archetype
  standard**, which moves G2 from "not in the research file" to "not true of the
  role and era" — a bounded relaxation that makes a 10-rung life arc possible
  without permitting invention; a ladder-aware opening rule (open *on* level one,
  relocate the hook inside it) evidenced by 9 of 11 sampled genre videos
  cold-opening on "Level one", including every breakout. De-history-ified the
  frontmatter, H1 and preamble. Voice rules deliberately **unchanged** — see
  below.

- **New research artifact: `research/artifacts/narration-registers.md`.** 10
  transcripts across 5 channels (ClipFlip POV, POVrank, Oddlet Explained,
  StickTory, Explainer Inc.), 95 VidIQ credits. Catalogues six narration
  registers and maps them to topic lanes. **Headline finding: register does not
  correlate with performance** — ClipFlip's 115k breakout and its 3,504-view
  video use the same voice; POVrank narrates Ancient Egypt and LAPD SWAT
  identically. Register is a floor, not a lever. This cancelled a planned
  rewrite of `script-writer`'s voice rules; the artifact is now referenced as a
  per-concept lookup rather than a mandate. Also validated the cyclical-close
  rule (confirmed by every sampled video) and surfaced the missing-hook finding
  above.

---

## 2026-09-04

- **New skill: `.claude/skills/plan-ken-burns/SKILL.md`.** Reads an approved
  `scene-prompts.md` manifest + script and produces a per-scene Ken Burns
  editing-suggestions table (zoom direction, ease curve, manual-Transform
  flags with a target note) for Resolve's Edit page. Written up after doing
  this by hand for all 45 Tomb Robber scenes live with Joe — encodes the
  zoom-in/out and ease-curve heuristics used there, plus a hard constraint
  discovered mid-session: Resolve's Dynamic Zoom Ease dropdown only supports
  three real direction+curve combinations (Out+Linear, In+EaseIn,
  Out+EaseOut), not free combination — "In + Linear" isn't achievable through
  that panel at all. Explicitly a draft for the editor to apply and correct
  against the real video, not an auto-apply — keeps Step 8's "editorial
  judgement stays human" principle intact.

---

## 2026-09-03

- **`content/watcher-pov/legion-marching/claude/scene-prompts.md` — added an
  explicit "plain mail, not *lorica segmentata*, not a solid red tunic"
  clause to every remaining unshot group/column scene (022, 023, 024, 026,
  028, 031).** Caught live: scene 018's first generation rendered the whole
  column in plate armor with solid maroon tunics, a direct violation of
  `character-bible.md`'s CH-01 lock (no named armour typology, cream tunic
  with red trim only) — a `character-bible`-level constraint that wasn't
  strong enough on its own to prevent drift once a wide multi-figure shot
  gave the model more room to improvise. Caught and fixed via retry that
  time; this edit gets ahead of it for every other group scene rather than
  catching it scene-by-scene during generation. **Follow-up, same day**:
  scene 027 also depicts background legionaries and was missed in the first
  pass — it drifted the same way on generation, was caught and fixed via
  retry, and the clause was added to 027 (and, preventatively, to 025, whose
  background legion is smaller/more distant but generated clean anyway) so
  neither needs a manual retry on any future regeneration.

- **`generate-scenes` skill — documented an unreliable `find` ref for the
  download icon, with a confirmed coordinate-click fallback.** Caught live
  during the legion-marching batch (scenes 001-007): a `find`-sourced ref
  for the Download button triggered a download of a stale image from an
  unrelated project (Tomb Robber), only caught because the existing
  Downloads-folder timestamp check (step 7) flagged the mismatch before
  filing — no bad file reached disk. Per-scene flow step 6 now documents the
  working fallback (fixed pixel coordinate, 3rd icon in the per-image action
  row, confirmed via its "Download" tooltip) to reach for immediately rather
  than retrying `find`.

- **`generate-scenes` skill — flagged an untested assumption in "Batching via
  subagents."** The skill bans parallel subagent dispatch on the reasoning
  that subagents "share the same live Chrome tab/window." Caught live on the
  legion-marching run: a subagent told explicitly to reuse the orchestrating
  session's existing Syntx.ai tab instead opened its own separate tab (its
  own tab group) in the same physical Chrome window — Joe spotted two
  independent "Nano Banana - SYNTX.AI" tabs open side by side. If subagents
  actually get isolated tabs by default, the stated race/corruption risk may
  not hold, and parallel dispatch could be safe (just visibly noisier). Not
  fixed yet — added a note in the skill proposing a small test (2 subagents,
  1 scene each, in parallel) before changing the sequential-only rule.

- **`WORKFLOW.md` — Steps 4a, 4b and 5 brought up to date with actual current
  practice; intro status line and Step 5's marker updated to match (Steps 1-5
  now demonstrated, not just 1-3.5/4a).**
  - **4a reframed**, caught live on the legion-marching concept: a prior
    style-breakdown reference (POVrank) bundles a transferable delivery
    register (second-person present tense) with a concept-specific structural
    device (a numbered "Levels" ranked ladder). Handing over the whole file as
    one undifferentiated "style reference" risks pulling a script toward a
    rank-journey shape even when that concept's own title deliberately chose
    a different framing — it did not cause a problem this time (the agent
    ignored the ranking system on its own), but the instruction was the
    near-miss. 4a now says explicitly: name which part is being reused.
  - **4b trimmed**: the three-way Sollo/VidIQ/Claude comparison narrative
    archived as a pointer rather than restated — the decision (`script-writer`
    agent, Mode 1) is settled. Added the actual artifact chain that was
    previously undocumented: `script.md` (script-writer) →
    `scene-prompts.md` (`scene-prompter` Mode 2) → Step 5.
  - **Step 5 tool section rewritten** for Syntx.ai / the Nano Banana family
    (Banana Pro + Banana 2 Lite, per `syntx-model-test-plan.md`), replacing
    stale Sollo-specific detail. Documents the actual two-agent execution
    system (`scene-prompter` for prompts/bible, `generate-scenes` skill for
    driving Syntx via Claude in Chrome) that wasn't previously written down
    in the workflow doc itself. Cost figures point to
    `syntx-model-test-plan.md` rather than being restated (they'll drift).
    Added a pointer to the new `style-farmer` skill as the per-concept style
    check, explicitly scoped as relevant only until the channel locks a
    cross-video visual identity.
- **`content/watcher-pov/legion-marching/concepts.md` — visual style decision
  recorded.** Leaning painterly/illustrated (Boring History Secrets register)
  after `style-farmer` frame pulls showed both flagged competitors doing
  something else entirely (Paladin: photoreal AI-video; Echoes of
  Civilizations: repurposed game-engine footage) — differentiates visually as
  well as narratively. Not yet validated against a real Syntx generation.
- **`style-farmer` skill created** (`.claude/skills/style-farmer/SKILL.md`).
  Captures a competitor video's on-screen visual/render style as a saved
  frame, for comparing a concept's style lean against what competitors
  actually show — not just their title/thumbnail. Built after a near-miss
  pulling reference frames for the Roman legion marching concept: a live
  browser screenshot doesn't produce a savable file, and the fallback of
  plain `yt-dlp` would have downloaded each competitor's entire video just to
  keep one frame. The skill's hard rule is that every `yt-dlp` call must use
  `--download-sections` to fetch only a few seconds around a timestamp before
  `ffmpeg` pulls the frame — never the full file. Includes a batching path
  (one subagent per video) for sweeps past ~3 competitors, and instructs
  logging each pull to a new `research/style-references/index.md`.

## 2026-09-02

- **`generate-scenes` skill rewritten to cut context/token cost.** The first
  real run (scenes 4-18) drove every click from a full-page screenshot +
  pixel coordinate, 6-8 images per scene, which throttled the session's
  usage limits partway through an 18-scene batch. Rewrote the per-scene flow
  to prefer `find`/`read_page` (text, not images) + `ref`-based clicks for
  every mechanical UI step, poll for generation completion via `read_page`
  instead of a screenshot loop, and do the one unavoidable visual QC by
  `Read`-ing the already-downloaded local file instead of a live browser
  screenshot — collapsing the per-scene image count toward ~1. Also added a
  "Batching via subagents" section (5-8 scenes per `Agent` dispatch, only
  the subagent's final text report re-enters the parent context) and a hard
  checkpoint fallback (suggest `/compact` every ~10-15 scenes). The find/ref
  approach hasn't been validated against Syntx's actual DOM yet — flagged in
  the skill as the first thing to confirm on resume, with a documented
  screenshot fallback if `find` can't reliably locate an element.
- **`scene-prompter.md` — hardened the sourcing table on unnamed background
  figures.** Caught live during scene generation: a mortuary-temple-officials
  scene, prompted as "plainly dressed administrative figures with no
  individual detail, no named rank or insignia," generated officials nearly
  indistinguishable from the workmen they were confronting. The rule was
  being over-applied — "no individual detail" (correct: no named
  identity/institution) was being read as "no visual distinction at all"
  (wrong: the table already allows role-typical dress like a longer robe or
  a held prop). Added an explicit clarification: unnamed figures can and
  should read as visually distinct by role using generic, plausible dress —
  banned is a specific rank/title/seal, not any signifier of a different
  role. Scene 011's prompt was revised accordingly (robe length, head-cloth,
  scroll prop, no gold/jewellery) and regenerated.
- **`generate-scenes` skill created** (first skill in this repo —
  `.claude/skills/generate-scenes/SKILL.md`). Drives Syntx.ai via Claude in
  Chrome to turn an already-written `scene-prompts.md` manifest into actual
  filed image files: attach reference(s), generate, visually verify against
  the bible, download, rename to `<scene_id>.jpg`. Encodes two real gotchas
  hit live generating Tomb Robber's scene 4: (1) the Syntx prompt box
  submits on Enter, so a prompt typed with literal newlines fires an
  incomplete, token-costing generation partway through — prompts must be
  typed as one continuous line; (2) never identify a reference image from
  its browser thumbnail alone — read the real files first. Pure execution,
  no creative judgment — that stays with `scene-prompter`.
- **`script-writer.md` — fixed hedge delivery, kept the rule.** Two real
  passages from the Tomb Robber script satisfied the "preserve uncertainty"
  rule by breaking voice — narrating a translator's confidence / a document's
  silence as meta-commentary, instead of dramatizing the doubt in-scene.
  Rewrote the "Preserving uncertainty" section with a ban on documentary-aside
  phrasing, quoted the two real offending lines as the negative example, added
  a self-check item and a Mode 3 scoring note (costs Voice points, not a G4
  gate). Also added a general craft rule: a one-word "reveal" naming an
  abstraction only works if its meaning was built earlier in the passage
  (caught via the "Not the hunger. The arithmetic." line, which wasn't).
- **`WORKFLOW.md` Step 3 — beat-count floor now scales with runtime.**
  Replaced the flat "10+ distinct facts or story beats" with ~1 beat per
  60-90s of target runtime, matching `script-writer.md`'s existing pacing rule.
  Tomb Robber (11 beats, ~13 min) logged as the worked baseline.
- **`WORKFLOW.md` — new Step 3.5, story treatment.** A short start/middle/end
  prose compression written straight from Step 3's beats, appended to the
  research file, read by Joe as a go/no-go gate before Step 4 script writing
  begins — catches a dry-but-factual concept before a full script gets
  written, not after.
- **`scene-prompter.md` — model/tier decision finalized.** Standardized on
  Banana Pro (2 tok/gen) + Banana 2 Lite (1.3 tok/gen) after a controlled
  Syntx model comparison; positional (not named) character references
  confirmed as the safe default across models, with a documented naming
  carve-out for Banana Pro specifically. Full test matrix in
  [syntx-model-test-plan.md](research/artifacts/syntx-model-test-plan.md).

## 2026-09-01

- **`scene-prompter.md` created.** New agent (Modes: DEFINE CHARACTERS,
  GENERATE, REVISE, AUDIT) generating per-scene, script-bookmarked,
  character-consistent image prompts — kept separate from `script-writer.md`
  since visual-fabrication discipline (locked appearance vs. bible/reference
  image) is a different discipline from narrative-fabrication discipline.
  Built as a universal scaffold, not Tomb-Robber-specific.
- **`/watch` skill installed** (`bradautomates/claude-video` plugin) — video
  download, frame extraction, transcript pull, for studying competitor
  channel retention/consistency mechanics.

## 2026-08-28

- **`script-writer.md` created.** Decision made after a three-way script-tool
  test (Sollo, VidIQ, Claude direct) found Sollo copying verbatim Wikipedia
  sentences and VidIQ fabricating an ancient term despite explicit sourcing
  instructions — provenance discipline needed to be architectural (no web
  tools, binding research file, sourcing contract), not dependent on a chat
  session. Established the sourcing contract, hedge-preservation rule,
  retention-informed structure rules, and the WRITE/REVISE/SCORE modes.
- **`WORKFLOW.md` Step 3 — hook-statistic requirement made mandatory.** Same
  three-way test found all three tools reaching for a hard opening number and
  none having a sourced one — Sollo omitted it, VidIQ fabricated it, Claude
  fudged it. One research gap, three different failures.
