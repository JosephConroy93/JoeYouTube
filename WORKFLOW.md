# Video Production Workflow

The end-to-end process for going from "a concept worth telling" to "a published
Watcher POV video." Rewritten 2026-09-07 for conciseness and current-state
accuracy — this file describes **what we do now**, not the path taken to get
here. For the reasoning, tool comparisons, and decision history behind any
step, see [research/inventory.md](research/inventory.md) and
[CHANGELOG.md](CHANGELOG.md); this file only links out to those, never
restates their journey inline.

Status legend: 🟢 refined & demonstrated · 🟡 defined, not yet run for real · 🔴 placeholder — approach not decided

---

## Folder convention

- `content/<series-or-book-slug>/<title-slug>/` — one folder per source
  book/PDF or concept. Holds the source file (if any) plus a `concepts.md`
  tracking candidate video ideas and the decision made about them. Example:
  [content/watcher-pov/](content/watcher-pov/)
- `content/watcher-pov/mascot/` — channel-level mascot assets (the Watcher)
  that aren't scoped to one video. See `scene-prompter.md`'s "channel-level"
  sections.
- `content/styles/` — the channel-level house style bible
  (`style-bible.md`), also not scoped to one video.
- `research/` — the research-phase working documents (inventory, artifacts)
  that underpin this workflow's decisions (niche, tooling, monetization).
- This file (`WORKFLOW.md`) — the process itself, project-wide, not tied to
  one video.

---

## Step 1 — Concept & research-angle discovery 🟢

**Every concept is one of two categories — classify it before researching.**
Both use `script-writer.md`'s same rank-ladder structure (numbered Levels);
the difference is what a "level" *is*, not whether the video is "laddered"
at all — confirmed against Oddlet Explained's "Your Life After a $500,000
Medical Emergency" (2026-09-07 check), which opens on "Level 1" and moves
through numbered chapters despite having no organizational rank in sight.

- **Category A — narrative/pacing levels.** Covers every framing where the
  scriptwriter *chooses* how to divide the story into escalating chapters:
  **"Your life as a [role]"** (a tomb robber, a pirate), **"Your life after
  [event]"** (a $500k medical emergency, a house fire), **"Your life during
  [situation]"** (a siege, a plague year). Levels don't need to correspond
  to any real, externally-defined numbered system — typically 8-10 for a
  20-25 min runtime, chosen for pacing. **When surfacing concepts, actively
  explore all of these framings on a given subject, not just "as a [role]"**
  — the same real premise/thread often supports several, and one may fit
  the available research or the competitive landscape better than another.
- **Category B — real-structure levels.** *"Every rank within [system]."*
  Levels **are** an actual hierarchy's real, named tiers (the CCP's cadre
  structure, a legion's rank structure, a mafia family's structure). Their
  count and names are **dictated by the real system**, not chosen for
  pacing — Step 3 has to establish what that real structure actually is
  before anyone scripts against it.

**Factual-correctness bar differs between them, deliberately — A is the
higher bar.** A Category A video's beats should trace to real documented
specifics (per Step 3 below). Category B's *structure* (rank names, tier
counts, real institutional mechanics) needs the same rigor, but the
*individual's personal journey through it* is understood as a plausible,
inferred composite, not a documented true story — because for a genuinely
opaque system (an internal one-party state's cadre promotions, a spy
agency's internal ladder), no such documented individual account exists to
source. This isn't a shortcut invented for this channel: verified directly
against POVrank's "Your Life as Every Rank in the Chinese Communist Party"
(2026-09-06) — its structural facts check out (Youth League founded 1922,
~74M members; CCP's ~98M members; the five-tier cadre hierarchy; a 24-member
Politburo; a 7-member Standing Committee; a 205-full/171-alternate Central
Committee) while its named characters and their specific incidents are
invented illustrations — and the video's own description discloses exactly
that ("events or details may be dramatized... this is not a documentary").
This already matches `script-writer.md`'s existing composite-archetype
standard (its G2 gate); Category B just applies it across a whole hierarchy
rather than one profession.

**Process**:
1. Identify candidate concepts — a source book/PDF dropped into
   `content/<slug>/`, or a real system/institution worth a rank-ladder
   treatment, not necessarily sourced from one book.
2. Claude reads the full source or scopes the real system's actual
   structure, and abstracts 3+ candidates, each built around a specific,
   obscure, or surprising thread — not a broad retelling. **For a
   promising thread, actively try it against multiple Category A framings**
   (as a role / after an event / during a situation) as well as checking
   whether it supports a genuine Category B treatment — don't default to
   the first framing that comes to mind.
3. **Classify each candidate A or B.** For B, confirm a real, discoverable
   rank/tier structure actually exists before treating it as viable — a
   system with no researchable structure isn't a Category B concept.
4. **Competitor-clash check.** Check
   `research/artifacts/competitor-titles-index.md` for a near-identical
   existing title on the same specific angle. The goal is avoiding a clash
   on the *specific angle*, not the general topic — multiple channels
   covering "pirates" is normal in this genre. **Freshness rule (added
   2026-09-08): each channel's section carries its own last-pulled date.**
   Within about a week, use it as-is — don't re-poll. Older than that (or
   the file/channel section doesn't exist yet), **don't silently re-poll —
   flag the staleness and ask Joe whether a refresh is worth the credit
   spend** before pulling `vidiq_channel_videos` again (see
   [inventory.md](research/inventory.md)'s "Competitor Tracking" for the
   current tracked list). Log whatever titles do get pulled, hit or not, so
   the index keeps growing, and update that section's pulled-date.
5. Each surviving candidate is checked against live VidIQ breakout/outlier
   data for its specific topic — validated, not just interesting, means
   real signal that content in that specific space is currently breaking
   out.
6. **Comment-mining pass (2026-09-04 idea, wired in 2026-09-07 — was never
   built into this file before now).** Pull `vidiq_video_comments` (**5
   credits/call**) on the strongest 2-3 competitor videos on the same
   subject. Comments surface which angles, figures, or events viewers keep
   asking for or complaining are missing — genuine concept-research signal,
   not just a script-polish check (Step 3 also uses this tool, for a
   different purpose — see there). **Log which videos got mined and what
   was found directly in `concepts.md`, against the concept** — Step 3
   checks this log first once a concept is chosen, and only pulls comments
   on videos not already covered here, so the same video is never polled
   twice.
7. Findings go into a new `concepts.md` in the content folder — every
   candidate considered, tagged A or B, **each with a short (~50-100 word)
   TLDR of the story shape** (what the hook/arc would plausibly be — not
   sourced yet, just enough to compare candidates by story shape rather
   than breakout score alone) — not just the winner. This TLDR is
   deliberately lightweight and pre-research; it's a different, deeper
   checkpoint from Step 3.5's treatment below, which only exists for the
   one already-chosen concept once it's actually been researched.
8. Joe and Claude agree which concept proceeds; the decision and *why* are
   recorded in the same file.

**Copyright note**: a source book is never reproduced or quoted at length —
facts are paraphrased and independently verified/deepened in Step 3, never
scripted from the book's own phrasing or jokes.

---

## Step 2 — Title selection 🟢

Generate and score title candidates using `vidiq_generate_titles` (seeded
with real proven titles from tracked competitors as `competitorTitles`) and
`vidiq_score_title`, iterating until something scores **90+**.

---

## Step 3 — Deep research phase 🟢

**The most important step for staying differentiated.** A source (where one
exists) identifies a real thread worth telling; the script needs
independently verified, deeper research, never a retelling of a
simplified/secondary source.

**Process**:
1. Identify real sources to deepen the concept's thread — primary sources
   where they exist, academic/specialist material, museum/archive material.
   Check [content/SOURCES.md](content/SOURCES.md) first — the central,
   growing index of sources acquired for any video — before sourcing
   something new.
2. For any **paid** source, propose it with a stated justification of what
   edge/specificity it adds.
3. Cross-check what's already been said on the topic using
   `vidiq_video_transcript` (**5 credits/call**) on existing videos covering
   the same subject, to deliberately identify and avoid the well-trodden
   angle (see [research/inventory.md](research/inventory.md) §4). **Check
   `research/artifacts/transcripts/index.md` first** — if a video's
   breakdown is already cached there (pulled here, in Step 4a, or by a past
   video's research), reuse it rather than paying for another pull. After
   any pull, write a **distilled breakdown** — structural facts, register/
   pacing notes, well-trodden-angle findings, paraphrased — to
   `research/artifacts/transcripts/<videoId>.md` and add it to the index
   immediately. **Never save the verbatim transcript itself** — a
   paraphrased breakdown (the same pattern as
   `video-breakdown-povrank-egypt.md`) is the legitimate cache; storing
   someone else's narration at length isn't. This is a content/angle
   check — distinct from Step 1's title-clash check and from Step 4a's
   delivery-style check below; all three use VidIQ but answer different
   questions.
4. **Comment-mining pass, second use of the same tool as Step 1's (2026-09-04
   idea, wired in 2026-09-07).** Pull `vidiq_video_comments` on the same
   competitor videos checked in step 3 above and read ~100 comments for
   recurring questions/frustrations viewers raise about the topic — bake
   these into the beats below rather than treating the topic as fully
   covered once the transcript check passes. Step 1's use of this tool is
   about *which concept* to pick; this one is about *what the script should
   actually address* once a concept is chosen.
5. Record what was used in `content/<slug>/sources.md` — pointers to the
   central index, or new sources (which then get added to the central index
   too).
6. **Source the opening hook statistic — required, not optional.** One
   hard, specific, verifiable number deliverable casually inside the first
   30 seconds (reference: StickTory's *"nearly 40% of kids like you don't
   make it this far. Congrats."*). Sourced to the same standard as every
   other fact, cited in `sources.md`. Ideally it doubles as setup for the
   story's turn. **If none can be sourced, record that explicitly as a
   known gap** — a stated gap is safe; a silently missing one invites
   fabrication downstream.
7. **Output the beats, scaled to category:**
   - **Category A**: distinct facts/story beats forming the narrative
     arc/timeline, roughly **one beat per 60-90 seconds of target runtime**
     (a 20-min video needs ~14-20 beats). Treat as a floor — more is fine,
     fewer means the middle sags.
   - **Category B**: one entry **per real rank/tier identified in Step 1**
     (typically 8-10, but the *actual* count for that system, not a
     genre-convention default). Each rank's entry needs (a) real
     structural/institutional facts about that rank — scope of authority,
     real title, real mechanisms — sourced to the same standard as any
     other fact, and (b) one or two illustrative story beats for that rank,
     understood as a composite/inferred individual case per the
     factual-correctness note above, not a documented true story. Plus an
     overarching through-line connecting the ranks (a personal thread, or
     the escalating stakes themselves) — the ranks are the spine, the
     through-line is why anyone watches all of it.
   Either way, this — plus the hook statistic — is the actual handoff
   artifact to Step 4, not raw research notes. **Every fact carrying
   uncertainty must be flagged in a dedicated fact-check section** —
   `script-writer.md` treats these flags as binding and fails any script
   that states a flagged fact as certain.

**Avoid**: basic/widely-known information, surface-level explanations.
**Focus on**: specific examples, unusual details, verifiable specifics that
make a viewer think "I've never heard this before."

---

## Step 3.5 — Story treatment (condensed start/middle/end) 🟢

A cheap go/no-go read before the full script gets written — catches
"accurate but dry" concepts early, when the cost of being wrong is a few
minutes, not a full draft. **Distinct from Step 1's per-candidate TLDR**
(written pre-research, lightweight, to help choose *between* candidates) —
this is a fuller, source-grounded treatment of the *one already-chosen*
concept, written after Step 3's deep research, gating Step 4.

**Process**: from Step 3's sourced beats and hook statistic, write a short
(~150-300 word) prose compression — what opens the story, the turn/escalation
in the middle, how it resolves or reflects at the end. A recombination of
already-vetted facts, not new research. Claude writes this directly, no
dedicated agent.

**Output**: a new `## Treatment` section in the same `research-*.md` file,
right after the beats.

**Gate**: Joe reads it and decides go/no-go on Step 4. A list of facts
rather than a story with a shape is a signal to find a stronger angle or
drop the concept, not something to patch later.

---

## Step 4 — Script generation

### 4a — Delivery-style reference 🟢

Before writing, check whether a directly comparable existing video exists.
**Check `research/artifacts/transcripts/index.md` first** — if Step 3 (or a
past video's Step 3 or 4a) already cached a breakdown for this video, reuse
`research/artifacts/transcripts/<videoId>.md` rather than pulling it again.
Otherwise pull it via `vidiq_video_transcript` (**5 credits/call**), write a
paraphrased breakdown (never the verbatim transcript — see the index file's
own caution) to that same location, and use that. Study **delivery and
structure only** — narration tense, pacing, section breakdown — never the
narrative content itself. **If Step 1's competitor-clash check already
surfaced a directly comparable video, reuse that identification here rather
than re-discovering it.**

**When handing a prior breakdown to `script-writer`, name explicitly which
part is being reused.** A breakdown usually bundles two different things:
the narration register (second-person, present-tense — almost always
transferable, and already baked into `script-writer.md`'s house style
regardless) and a structural device like a numbered ladder (only relevant if
this concept's own chosen angle is actually a rank/completionist journey —
check `concepts.md`'s category). Handing over the whole file as one
undifferentiated "style reference" risks pulling a Category A script back
toward a structural device its own concept decision rejected.

### 4b — Script generation tool 🟢

**Tool: the `script-writer` agent** (`.claude/agents/script-writer.md`),
Mode 1 (WRITE). (Tool comparison archived in
[research/artifacts/tooling-comparison-script-generators.md](research/artifacts/tooling-comparison-script-generators.md)
if the history is ever needed — not required reading for running this step.)

**Inputs**: the research file (Step 3 — beats/ranks, hook statistic,
fact-check flags — the sole factual authority), `concepts.md`
(category/angle/title), `sources.md`, and the delivery-style reference from
4a (register only, per 4a's caution above).

**Output**: `content/<series>/<slug>/claude/script.md`, plus a `## Handoff
notes` section covering any beat/rank left out, any research gap, and the
agent's own self-check result. **A mandatory fact-check pass is required on
every script, both categories** — run the same agent's Mode 3 (SCORE)
before treating a draft as final; see `script-writer.md` for the accuracy
gates (G1-G4).

**This doesn't conflict with Category B's inference allowance.** The
fact-check verifies that real structural facts (rank names, institutional
mechanics, counts) are sourced and accurate to the normal standard, and
that composite/inferred individual elements are correctly presented as
illustrative rather than stated as certain documented fact. It never
requires a Category B script's individual narrative to trace to one real,
named person — that would contradict Step 1's whole premise for that
category. This is `script-writer.md`'s existing composite-archetype (G2)
standard, not a special exception Category B needs to work around.

### Handoff into Step 5

The approved `script.md` is not itself a scene-generation manifest. The
`scene-prompter` agent's Mode 2 (GENERATE) segments the approved script into
a per-scene, script-bookmarked manifest — a `scene-prompts.md` index plus
chapter files at `content/<series>/<slug>/claude/scene-prompts/level-NN.md`
(25 scenes max each, since 2026-09-10) — which is the actual input Step 5's
`generate-scenes` skill executes against. Mode 1 (DEFINE CHARACTERS) must
already have produced an audited character bible with passed reference
images before Mode 2 runs; see `scene-prompter.md` for both modes. **Step
4.5 below runs before Mode 2, not after** — it feeds Mode 2, rather than
patching its output.

---

## Step 4.5 — Visual reference pass 🟡 (new, 2026-09-11 — Pharaoh's Servant dog-breed/wall-decoration QC findings)

**Step 3's research is scoped to narration accuracy — what the script is
allowed to *say*. Nothing checks visual accuracy — what a scene is allowed
to *show*.** A script can pass every fact-check gate while still containing
elements (an animal, a garment, an object, a building's decoration) whose
real appearance was never researched. Left unconstrained, `scene-prompter`
Mode 2 either invents a visual with no sourcing behind it, or leaves it
generic enough that the model defaults to something anachronistic at
generation time — a modern golden-retriever-coated dog standing in for a
First Dynasty hunting dog, a Greco-Roman toga on an unconstrained background
steward (the original 2026-09-09 pilot finding this generalizes from — see
`prompt-hardening-log.md`), a palace hall with no wall decoration because
none was specified either way. Same root failure mode as that promoted
finding, caught one step earlier: at prompt-writing time, not generation-QC
time.

**Why this is its own step, not folded into Mode 2**: `scene-prompter` has
no web-research tool (Read/Write/Edit/Grep/Glob only, confirmed against its
own tool list) — it cannot look anything up, only write from what's already
on disk. The actual lookup has to be done by whoever's driving the
pipeline (the same session doing Step 3's research), using `WebSearch`/
`WebFetch`, before Mode 2 starts writing prompts for the affected chapter.

**Process**:
1. Once `script.md` is locked (post Step 4b fact-check), scan it for
   elements that will need real visual specificity once Mode 2 segments it
   into prompts — named or implied animals, distinctive garments/objects,
   architectural decoration — anything where "generic, era-appropriate"
   isn't precise enough guidance for an image model to get right on its
   own.
2. For each, check whether Step 3's research file already covers its
   *appearance* (not just its existence or narrative role — Step 3 often
   covers the latter without the former, since it was never asked to).
3. If not covered, do a targeted, sourced lookup (same sourcing bar as
   Step 3 — real sources, not assumed general knowledge) and append a
   **properly-caveated visual-reference addendum** to the research file,
   near the fact it supports. State plainly what's confirmed vs. still
   debated in the sources, and whether the visual detail is tied to this
   video's specific setting/site or just the general era — see
   `research-pharaohs-servant.md`'s 2026-09-11 dog-appearance addendum
   (beat 12) for the worked example and format.
4. **This is visual-only — it never asserts a new narration fact and never
   triggers a script rewrite.** If a visual lookup surfaces something that
   actually contradicts a narration claim already in the script, that's a
   real Step 3 gap, not a Step 4.5 one — flag it back rather than quietly
   patching around it with a visual note.

**Output**: zero or more new visual-reference addenda in the research file.
`scene-prompter` Mode 2 (and Mode 3, on a revision) reads these the same
way it already reads fact-check flags before writing a `content_prompt` —
see `scene-prompter.md`'s own updated Mode 2 doctrine. **If a visually-
specific element has no research-file coverage and this step hasn't been
run for that chapter yet, Mode 2 flags it in the row's own `notes` rather
than inventing or leaving it bare** — a visible gap is safer than a silent
guess, same principle as every other flagged-gap convention in this
project.

**Gate**: informal, no separate Joe go/no-go required (unlike Step 3.5) —
but a chapter with a flagged, unresolved visual gap shouldn't go to
`generate-scenes` without either running this pass or a deliberate decision
to accept the gap.

**Status**: defined, not yet run as its own deliberate pass on a video from
the start — it was reconstructed after the fact on Pharaoh's Servant once
the gap surfaced at QC. Next video should run it for real, before Mode 2
starts, as the actual test of whether this closes the gap rather than just
documenting it.

---

## Step 5 — Scene generation / animation style 🟢 (rebuilt 2026-09-09 — direct Gemini API, superseding Syntx.ai)

Qualitative style findings (tool-agnostic, still relevant):
[research/artifacts/animation-style-research.md](research/artifacts/animation-style-research.md).
**Tool/cost detail below reflects the current direct-API pipeline** — the
Syntx.ai-era references (`syntx-model-test-plan.md`, `syntx-ai-research.md`)
are historical, kept for the archived skill version, not the current
mechanism.

- **Tool: the Google Gemini API, called directly** (no browser automation,
  no ToS conflict — Syntx.ai's own ToS explicitly banned the scripted
  access the prior pipeline relied on). Standardized on
  **`gemini-3.1-flash-image`** (Nano Banana 2) for anything needing
  character-reference consistency; `gemini-3.1-flash-lite-image` for
  `text-card` rows (no reference support needed there); `gemini-3-pro-image`
  as a targeted escalation, not a default. Full detail, real pricing, and
  the 2026-09-09 pilot's findings in `research/inventory.md` §2k and
  `research/artifacts/archive-style-bible-validation.md`.

- **Execution system — one agent for judgment, five skills for execution
  (re-modularized 2026-09-10, `chain-scenes` layered on the same day)**:
  1. **`scene-prompter` agent** (`.claude/agents/scene-prompter.md`) — Mode 1
     (DEFINE CHARACTERS) locks each character's appearance into a bible with
     audited reference images; Mode 2 (GENERATE) segments the approved
     script into a per-scene manifest bookmarked back to the *full verbatim*
     script text each scene covers, writes the style-agnostic
     `content_prompt` plus (only if a style has actually been chosen) a
     `style` name looked up at generation time, and, once per video (not
     per scene), a shared `qc-checklist.md`. **Chapter-at-a-time and
     resumable since 2026-09-10**: defaults to writing just the first
     chapter, takes "the next N" / "the rest" to continue — never rewrites
     a whole manifest in one pass. Mode 3 (REVISE) rounds out the agent.
     **No longer has the old Mode 4 or Mode 5** — batch QC and style-preview
     generation both moved to standalone skills (below) since this agent
     has no Bash and can't execute either itself (confirmed by a real
     failed Mode 5 dispatch, 2026-09-10). **The Mode 4 slot was reused the
     same day** for an unrelated new capability — CHAIN (two sub-steps:
     4a analyzes a chapter for consistency-linked scene groups, 4b rewrites
     a group's dependent rows once its seed image is real) — driven only by
     the new `chain-scenes` skill below, never invoked directly. Still pure
     creative/prompt judgment, no browser/API tools. Checks
     `content/styles/style-bible.md` for named candidate styles and
     `content/watcher-pov/prompt-hardening-log.md` for known QC failure
     modes before writing prompts.
  2. **`generate-scenes` skill** (`.claude/skills/generate-scenes/SKILL.md`)
     — builds and submits requests only. Calls the Gemini Batch API
     (always exactly one batch, one chapter by default or an explicit
     "next N chapters"/"rest"), logs the submission to a new per-project
     `batch-log.md`, and **stops** — no waiting, no polling, no fetching,
     no QC.
  3. **`get-scenes` skill** (`.claude/skills/get-scenes/SKILL.md`, new
     2026-09-10) — one status check per pending `batch-log.md` row, no poll
     loop. Not ready → logs the check, exits, safe to run again any time
     later. Ready → decodes and files results to
     `content/watcher-pov/<slug>/scene-generation/<scene_id>.jpg`, marks
     the row `fetched`. Purely mechanical, no content judgment.
  4. **`validate-scenes` skill** (`.claude/skills/validate-scenes/SKILL.md`,
     new 2026-09-10) — QC against a `fetched` batch's images, checked
     against `qc-checklist.md`'s four coarse checks (scene match, character
     consistency, major era violations only, nothing malformed) plus
     text-cards' own exact-text rule, in small 5-8-image subagent groups.
     Failures logged to `content/watcher-pov/prompt-hardening-log.md`.
     **No automatic retries** — marks pass/fail and why, then leaves it to
     whoever's driving the session to decide between a plain resubmission
     (via `generate-scenes` again) or a prompt revision first (`scene-prompter`
     Mode 3). The session should also offer Joe the choice of reviewing
     fetched images himself before spending an automated QC pass at all.
  5. **`preview-style` skill** (`.claude/skills/preview-style/SKILL.md`,
     new 2026-09-10, replacing scene-prompter's old Mode 5) — ad-hoc,
     standalone: generates a real comparison batch of images for a scene
     range in a candidate style, before committing a whole project to one.
     Defaults to fast/direct generation (not the batch-log flow — real
     usage confirmed direct calls are right at preview scale), reuses
     `generate-scenes`' request-building mechanism and `validate-scenes`'
     QC. Never touches the real manifest or `scene-generation/`.
  6. **`chain-scenes` skill** (`.claude/skills/chain-scenes/SKILL.md`, new
     2026-09-10) — **situational, not part of the default linear chain
     above.** Invoked deliberately for a chapter known or suspected to have
     consistency-linked scene groups (same location, held pairings
     generated as separate requests). Dispatches `scene-prompter` Mode 4a
     to find groups and pick a seed scene per group (no groups found → says
     so, defers to a plain `generate-scenes` call); submits just the
     seed(s) via `generate-scenes`, polls narrowly via `get-scenes` until
     that small batch resolves, quick-QCs the seed(s) via `validate-scenes`,
     dispatches `scene-prompter` Mode 4b to rewrite the group's dependent
     rows with a second positional reference to the real seed image (plus a
     mandatory pose/composition guard — see that mode's own doc), then
     submits the remainder of the chapter via `generate-scenes` as normal.
     Calls all three execution skills exactly as documented, unmodified —
     a pure orchestrator, not a change to any of their contracts. Prompted
     by a real finding on Pharaoh's Servant level-01 (`016`/`017`/`018`
     drifted when generated independently; fixed by hand first, then
     scripted). **Deliberately reopens a bounded version of the
     "request-then-poll" pattern** the split above moved away from — scoped
     to a handful of seed images per chapter, confirmed with Joe as the
     right scope before building it. **Status: unproven beyond one manual
     precedent** — first real use is scoped to one chapter, not rolled out
     across every remaining chapter at once.

  **Why split this far**: Joe's call after living with the single-skill
  version for real — submitting a batch, waiting on it, and QC-ing it were
  bundled into one operation, and a genuinely trivial QC finding (invented
  marks on a background prop nobody would zoom in on) cost the same
  automatic multi-attempt retry escalation as a real anachronism. Splitting
  at "submit / fetch / validate," dropping the automatic retry loop for a
  human-reviewed decision, and making Mode 2 resumable chapter-by-chapter
  are all aimed at the same thing: no single operation in this pipeline
  should require reading or rewriting more than one chapter's worth of
  material. Full reasoning in `CHANGELOG.md`'s 2026-09-10 entries.

  **Still genuinely open**: real batch throughput/reliability at production
  scale (~150-300 scenes) is untested — the 2026-09-09 pilot validated the
  mechanism at 4 requests, not volume. Pilot in small chapter-sized batches,
  per this project's standing "validate small before trusting at scale"
  discipline, before assuming this scales cleanly.

- **Granular control within a style**: supply audited bible reference
  images, attached **positionally** ("the man shown in the first attached
  reference image...") — re-confirmed 2026-09-09 directly against Google's
  own docs, no structured name/ID binding exists in the API either. A bare
  character name in prompt text is safe as reinforcement, never a
  replacement for positional phrasing.

- **Known follow-up, not yet done**: Step 6 (below) still describes
  generating thumbnails "in Syntx.ai, in the same style preset as the
  scenes" — now inconsistent, since scenes no longer come from Syntx.
  Flagged, not resolved here; Step 6 wasn't in scope for this rebuild.

---

## Step 6 — Thumbnail 🟢 (first real test done — Tomb Robber, 2026-09-04)

> ### ⚠️ Run this *after* Step 8 (video editing), immediately before Step 9 (publication)
>
> Numbered here, but it belongs after the edit: a thumbnail is easier to
> get right once the real finished footage exists to pull a frame or a
> moment from, and it's the last thing needed before upload anyway.
> Renumbering is parked — see the banner on Step 7 and
> `research/inventory.md`'s Parking lot.

Full findings: [research/artifacts/thumbnail-research.md](research/artifacts/thumbnail-research.md).

> ### ⚠️ Check thumbnail text against the research guardrails before rendering it
>
> Thumbnail copy is a factual claim, and it is the *first* claim a viewer sees.
> Check every candidate line against the video's own
> `research-<slug>.md` "what not to overstate" guardrails, exactly as script
> lines are checked — the thumbnail currently skips that gate entirely.
>
> **Real miss, 2026-09-12 (Pharaoh's Servant)**: "BURIED ALIVE" was drafted,
> rendered onto all three thumbnail variants, and recommended — before Joe
> asked "were they buried alive though??". They were not. That video's own
> research says cause of death is **genuinely unresolved** (strangulation and
> poison both live proposals) and explicitly instructs: *"Do not present either
> method as the single documented truth for all victims."* The script says as
> much on screen.
>
> Two compounding failures worth naming:
> 1. **It contradicted the video within minutes of the click** — click "buried
>    alive", hear "poison, strangulation, we don't know which". That is a
>    retention and trust cost, not just an accuracy one.
> 2. **It was a competitor's framing.** The same research file lists Past
>    Unlocked's *"What If You Were Buried Alive as a Pharaoh's..."* among the
>    competing videos. The concept was chosen for being *differentiated* from
>    exactly that, so copying its inaccurate hook gave away the only edge.
>
> **Rule**: the strongest accurate hook beats the strongest inaccurate one,
> because the video has to pay off the thumbnail. Where the research flags
> something as contested, the thumbnail may not resolve it. Prefer a
> differentiated fact the research *does* support — here, the pre-dug graves
> waiting while you were still alive and working ("YOUR GRAVE IS READY"), which
> no competitor uses.
>
> Thumbnail text should also **add** the stake rather than restate the title.

**Confirmed live, not just in research**: Tomb Robber's thumbnail was
generated via VidIQ, then scored low by `vidiq_score_thumbnail` **on its own
generated image** during the actual upload — a real-world repeat of the
exact unreliability already flagged below, not a new finding, just no longer
theoretical.

**⚠️ Don't use `vidiq_score_thumbnail` as a pass/fail gate** — it penalises
the minimalist white-background style that's actually winning here (scores
StickTory's 2.16M-view thumbnail lower than a 112k-view one). Use it for
**technical** checks only (blur/sharpness, brightness).

**Starting template** (adapted from StickTory, the strongest performer):
- White / very light background — high contrast against a feed of dark,
  busy thumbnails
- One character, our consistent protagonist design, with era-identifying
  costume detail
- Exaggerated facial emotion
- 2-3 words of high-contrast text, readable at 100px wide
- One saturated colour accent
- Locked layout across every video

**Style matching**: generate thumbnails **in Syntx.ai, in the same style
preset as the scenes**, reusing the same character reference images used
for scene consistency (Step 5). Same tool + same references = automatic
match.

---

## Step 7 — Voiceover 🟢 (voice locked, pace confirmed)

> ### ⚠️ Run this immediately after Step 4 (script lock) — *before* Steps 4.5 and 5
>
> **The number is wrong; the position in this list is not yet renumbered.**
> Generate the real voiceover, then transcribe and align it
> (`align-scenes` → `scene-timing.md`), as soon as the script is signed
> off. Everything downstream then works from **measured** pacing instead
> of a calibration estimate.
>
> **Why (real cost, Pharaoh's Servant, 2026-09-11)**: the hook clips were
> generated blind at an arbitrary 9.000s each, and the voiceover was
> retrofitted to them afterwards. The narration's real beats came in at
> 7.92s / 5.98s / 7.50s, so all three clips had to be trimmed
> (−1.1s / −3.0s / −1.5s) — 5.6s of generated footage paid for and thrown
> away, plus a wasted attempt at resolving the mismatch by gutting the
> hook's payoff shot. Generating in the *other* order would have produced
> clips cut to the beat in the first place.
> Same lesson, second instance: measured delivery ran ~159.5wpm against
> the 170.9wpm figure baked into `scene-prompter.md`'s word-count bands, so
> every scene's *planned* duration was an estimate that then had to be
> re-derived from real audio anyway.
>
> Renumbering this file properly (which also moves Thumbnail after
> editing — see Step 6) is parked in `research/inventory.md`'s Parking lot
> as a deliberate pass, deliberately not done mid-video while Pharaoh's
> Servant is being cut against the current numbers.

> ### ⚠️ Normalise the voiceover to ~-16 LUFS before it goes anywhere near the timeline
>
> **VidIQ generates voiceover at roughly -30.8 LUFS** (measured across all six
> Pharaoh's Servant segments, 2026-09-12). That is about **17 dB below** what
> YouTube expects. YouTube normalises to ~-14 LUFS but only turns loud content
> *down*, never quiet content up — so a mix left at source level plays back
> markedly quieter than every video around it, and reads to a viewer as thin and
> lifeless rather than simply quiet. Joe's note on first watch-through was "the
> audio is too low... giving a bit of scarcity of viewer experience", which is
> exactly this.
>
> Do it **once, at the file, right after generation** — before `align-scenes`.
> Gain does not change timing, so the transcript and `scene-timing.md` stay valid:
>
> ```bash
> # measure
> ffmpeg -i in.mp3 -af ebur128 -f null - 2>&1 | grep -A1 Integrated
> # apply: gain to target, limiter only catches isolated transients
> ffmpeg -i in.mp3 -af "volume=<target - measured>dB,alimiter=limit=0.8414:level=disabled:attack=5:release=50" \
>        -ar 48000 -ac 1 -c:a pcm_s24le out.wav
> ```
>
> **`level=disabled` is required** — `alimiter` auto-normalises by default and
> will *raise* the level instead of taming it.
>
> Target **-16 LUFS integrated, true peak ≤ -1.5 dBFS**, leaving headroom for
> beds/SFX to sit underneath. Check the loudness range afterwards: this voice
> moved only 3.6 → 3.0 LU, i.e. the limiter caught isolated peaks and left the
> speech alone. A large LRA collapse means over-compression — back the gain off.
>
> Export **WAV at the project frame rate**, not MP3: source frames then equal
> timeline frames, which makes frame-exact placement trivial.
>
> On Pharaoh's Servant this was retrofitted after the first full render — new VO
> on a fresh audio track, original track disabled rather than deleted. Doing it
> at Step 7 avoids a wasted 22-minute render.

Full findings: [research/artifacts/voiceover-research.md](research/artifacts/voiceover-research.md).

**Voice: Jim** — deep British baritone, "C-suite executive authority...
without the performance." Locked 2026-09-08 after a 5-voice pacing
calibration (Aaden, Adam, Chris, Jim, Michael — full detail and audio
samples in [`content/watcher-pov/voice-register.md`](content/watcher-pov/voice-register.md)).
**Confirmed pace: 170.9 words/minute / 2.85 words/second**, measured on a
real full-script generation (393 words, 138 seconds) — not a short sample.
This figure is now baked into `scene-prompter.md`, `script-writer.md`, and
`plan-ken-burns/SKILL.md`, replacing an inherited ~145wpm figure that
traced back to "Roger," a voice tested once in 2026-08-31 but never
actually used in production. Governs future videos only — Tomb Robber
already shipped with a different voice ("A Top Narrator VO PRO") and isn't
being re-recorded.

**Tool**: Syntx.ai (already the scene-generation tool, Step 5) has
ElevenLabs voices built in; VidIQ is also ElevenLabs-backed and has a free
`vidiq_voiceover_generate`/`vidiq_voiceover_list_voices` MCP route used for
part of this calibration. **Exact platform Jim was found/generated on
wasn't explicitly confirmed in chat** — not one of VidIQ's ~21 stock
voices, so likely Syntx.ai's own library, but worth confirming directly the
first time voiceover is actually generated for a real video rather than
assumed here.

**Log every video's voice in
[`content/watcher-pov/voice-register.md`](content/watcher-pov/voice-register.md).** Even with a
voice locked, keep logging — a future change (deliberate or accidental)
should stay visible at a glance, not get discovered later.

**Still open, not blocking**: the "overused synthetic voice gets
algorithmically flagged" concern (`research/inventory.md`'s Loves/Hates
section, never confirmed or ruled out) applies to Jim same as any
non-cloned stock voice. The Liverpool-voice-clone plan below remains the
structural fix if that risk ever needs fully closing out — record the same
~30s hook three ways (natural / modulated / wife's voice) and compare
against Jim as the current baseline, in whichever tool actually supports
cloning (unresolved — see `voiceover-research.md`'s open thread on
Syntx/VidIQ cloning availability). Not urgent now that a fast, distinctive
stock voice is locked; revisit if the fingerprinting risk ever gets
confirmed as real.

**⚠️ Guide correction (still valid)**: any claim that a specific TTS vendor
avoids demonetization risk is marketing FUD — YouTube's inauthentic-content
policy turns on original value, not on which TTS vendor produced the audio.

---

## Step 8 — Video editing 🟢 (confirmed — Tomb Robber produced this way)

Full findings: [research/artifacts/video-editing-research.md](research/artifacts/video-editing-research.md).

**Sound effects and ambience**: [content/sfx/sfx-index.md](content/sfx/sfx-index.md)
is the catalogue of what the owned libraries actually contain, backed by
[content/sfx/cinematic-bundle-metadata.tsv](content/sfx/cinematic-bundle-metadata.tsv)
— a searchable `description / duration / path` index of all 7,842 files in the
Cinematic bundle, built from embedded BWF metadata. **Search the TSV, never the
filenames** — that pack is bulk-renamed to meaningless names while the real
professional keywords survive in the file headers. Index any newly-bought pack
the same way with `content/sfx/index-pack.sh <pack-root>` *before* auditioning
anything by hand.


**Tool: DaVinci Resolve, confirmed in production, not a standing
recommendation.** Tomb Robber was assembled, Ken Burns'd, and given Fusion
particle effects in Resolve — this is the working tool, already used
end-to-end on a real video. Free, no per-render credit cost, no 240-second
cap, real Python/Lua scripting API + MCP servers as the eventual automation
path if manual assembly ever becomes the bottleneck. CapCut was ruled out —
no automation at all, a dead end for a pipeline.

**Placement comes first**: `.claude/skills/place-scenes/SKILL.md` imports
every scene image, hook clip, and voiceover segment and builds the actual
timeline — each scene at the exact position/duration `align-scenes`
measured from real audio — before any motion is applied. `apply-ken-burns`
attaches a Fusion comp to an *existing* timeline item, so this step has to
run first.

**Motion is Ken Burns pan/zoom, and it's the default on nearly every
scene** — see `.claude/skills/plan-ken-burns/SKILL.md` (corrected
2026-09-08 against real competitor footage, reversing an earlier
theory-only "static by default" version). Static frames are a capped, rare
exception (text-cards and very short 3-4s scenes only, ≤10% of a video's
scenes) — the norm is motion throughout. The same skill also plans a
**black-sweep transition** (~0.5s gradual fade to black) on roughly 1 in 10
scenes, at deliberate beat-boundaries. Vary focal point/direction on the
scenes that do get motion — uniform centre-zoom on every scene reads as the
"AI slop" pattern drawing real criticism elsewhere in this genre.

**Ken Burns matters regardless of tool**: scenes are still images, and
"image slideshows without original video footage" is a named
inauthentic-content trigger (`research/inventory.md` §4). Motion is what
makes stills read as video.

**⚠️ Don't over-automate this step.** §4 names "templated video structure"
as an inauthentic-content trigger. Automate the *mechanical* (sequencing,
audio sync, loudness, captions, export); keep human judgement on the
*editorial* (pacing, emphasis, where a beat holds).

---

## Step 9 — Publication 🟡 (happened once, informally, for Tomb Robber — not yet a repeatable designed process)

**Tomb Robber published 2026-09-04** (`jtCPu2DFD8I`) — this went untracked
in this file for several days purely because it never came up in chat, not
because the video wasn't live. **Don't trust this file's status markers over
`research/index.md`'s "Where we left off"** for what's actually true right
now; that's the living pointer, this is process documentation.

**Description construction — used, not just planned.** Tomb Robber's actual
upload used the citation-list-plus-"People & Sites Mentioned" pattern
described below. Whether it was applied exactly as drafted or adapted on
the fly during upload hasn't been checked line-by-line against the real
YouTube description yet — worth doing once, to confirm the pattern actually
holds before leaning on it as designed for future videos.

**Account warm-up timing** ([research/inventory.md §4](research/inventory.md),
3-7 days immediately pre-launch) — not confirmed either way whether this was
actually followed before Tomb Robber's upload. Worth checking, not assumed.

**Channel "About" copy and the Watcher hook — confirmed NOT applied.** The
live channel is still titled "HistoryPOV" with its original pre-pivot About
copy; Tomb Robber shipped under that old identity. **Deliberately deferred
(Joe, 2026-09-08) until just before the next video**, not an oversight —
the draft copy in
[`content/watcher-pov/mascot/watcher-concept.md`](content/watcher-pov/mascot/watcher-concept.md)'s
"Viewer-facing copy" section is still the plan, just not applied yet.

**Still genuinely undesigned**: this happened once, informally, for one
video — there isn't yet a repeatable, written-down upload/scheduling
process a future video could just follow. That design work is still
outstanding, now informed by one real run instead of zero.

---

## Open backlog

Full detail lives in [research/inventory.md §5](research/inventory.md). Summary:
- `content/watcher-pov/voice-register.md` — Tomb Robber's voice confirmed ("A Top
  Narrator VO PRO," ElevenLabs, via Syntx.ai); still open: real usage over
  more videos to settle consistency-vs-iteration, and the Liverpool-voice
  three-way test (Step 7) if a different identity is still wanted.
- `research/artifacts/transcripts/` — new cache convention (2026-09-08), one
  file per video plus an `index.md`; needs real usage across a few videos
  to confirm it's actually preventing double-pulls as intended.
- `generate-scenes` throughput at 150-300 scenes/video — **resolved
  differently than planned**: rather than the Artlist.io MCP path floated
  in §2h, the project moved scene generation to the direct Gemini API
  (2026-09-09), which sidesteps the sequential-browser-tab bottleneck
  Artlist would have fixed too. Real batch throughput at full manifest
  scale is still untested (see the rewritten skill's own "Batch sizing"
  section) — the open item now is validating that, not choosing between
  Artlist and Syntx.
- Thumbnail-to-animation-style consistency, once a first real thumbnail test
  runs.
- Publication process design (Step 9).
- Whether/how the best-performing prompts from this process get captured as
  a reusable skill — raised by Joe, not yet decided.
