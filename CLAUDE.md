# AI YouTube Project — Faceless Channel Automation

## Phase: first video shipped (2026-09-04) — graduation trigger fired, not yet acted on

Research converged (closed 2026-09-02). Niche (Watcher POV — Horrible
Histories-sourced ancient Egypt content), core toolchain (Claude direct for
scripts, VidIQ for research/titles/voiceover/edit-assembly, Syntx.ai + the
`generate-scenes` skill and `scene-prompter` agent for scene art, DaVinci
Resolve for editing) and the end-to-end process (`WORKFLOW.md`) were settled
by running a real practice video (Tomb Robber, 2026-08-28 → 09-04), not just
compared on paper. That run is also why the toolchain isn't identical to the
original guide's: Sollo was tried, spent real credits on a 50-scene batch,
and was dropped for Syntx.ai after consistency problems surfaced (see
`research/inventory.md` §2a) — a worked example of validating a tool at
small scale before trusting it at full scale, not just a plan.

**Tomb Robber published 2026-09-04** (`jtCPu2DFD8I`, confirmed via VidIQ) —
this file previously said publication was still the remaining gap; it
wasn't, and went untracked here for several days across multiple sessions
purely because it never got mentioned in chat. **Don't treat this file's own
narrative as current-state truth going forward** — for what's actually true
right now, check `research/index.md`'s "Where we left off" (or pull real
data via VidIQ/the filesystem directly) rather than trusting a status
paragraph here, which is exactly the kind of thing that goes stale between
sessions. This section is being kept intentionally thin from here on for
that reason.

**One concrete, live gap this surfaced**: the channel is still titled
**"HistoryPOV"** on YouTube with its original pre-pivot About copy — the
Watcher POV rename and mascot-dedication copy drafted in research were never
actually applied to the real channel. Tomb Robber shipped under the old
identity. **Deliberately deferred (Joe, 2026-09-08), not an oversight**: the
rename happens just before the *next* video is ready, not now.

**Graduation trigger named below has now fired.** This file said "that
graduation point is the first published video, not before" — a video is
published. Whether/how to formally graduate out of "Proof of Concept" into
something with its own execution-scoped structure hasn't been decided yet;
raise it explicitly next time this file gets touched for real, don't let it
quietly not-happen the way the publish date did.

## Why this exists

Joe started by evaluating a workflow proposed in a "Sollo AI + Claude" guide
for running a faceless YouTube channel end-to-end with AI tools (niche
research → scripting → scene generation → voiceover → editing → thumbnails →
performance analysis). The guide was a useful starting skeleton, not gospel —
research stress-tested each step, found better/alternative tooling in several
places (see Phase note above), and worked through the parts the guide glossed
over (niche selection methodology, monetization mechanics for a new channel,
analytics literacy). That groundwork is why the current toolchain and
`WORKFLOW.md` look the way they do.

Source guide (summarized in chat, not fetched live): a Notion doc walking through
Sollo.ai + a Claude Project as the core toolchain for a faceless channel.

## Where things live

- [research/index.md](research/index.md) — **start here.** A lightweight reading
  guide: current status per topic, what to actually read and when, an explicit skip
  list for settled/dead threads (e.g. the whole Sollo saga), and where things left
  off. Keep it in sync whenever inventory.md's status changes.
- [research/inventory.md](research/inventory.md) — the live working document. Agenda
  items, findings, open questions, tooling comparisons, and decisions get logged here
  as we go — the running record behind the current toolchain and workflow.
- `research/artifacts/` — supporting material we pull in or produce along the way:
  screenshots, competitor breakdowns, exported reports, PDFs, tool comparison exports,
  etc. Reference these from inventory.md rather than duplicating content inline.
- [WORKFLOW.md](WORKFLOW.md) — the end-to-end video production process (concept →
  research → script → scenes → thumbnail → voiceover → editing → publishing).
  Started once the flagship niche was settled; several steps are still placeholders
  — see its own status markers and the backlog in `research/inventory.md` §5.
- `content/<series-or-book-slug>/<title-slug>/` — one folder per source book/PDF
  used for video concepts (e.g. `content/watcher-pov/`), holding
  the source file and a `concepts.md` tracking candidate ideas and decisions. See
  WORKFLOW.md Step 1 for the process that produces these.
- [CHANGELOG.md](CHANGELOG.md) — dated log of changes to `WORKFLOW.md`, agents
  (`.claude/agents/`), and skills only — not research findings or content
  decisions, which stay in inventory.md. Add an entry whenever one of those
  changes.

## Working agenda (current)

1. **Tomb Robber shipped (2026-09-04, `jtCPu2DFD8I`)** — resolves the old
   "does it ship as video one" question. The channel is still under its
   pre-pivot "HistoryPOV" name/About copy — renaming to Watcher POV and
   applying the drafted mascot-dedication copy is **deliberately timed for
   just before the next video ships**, not now (Joe's call, 2026-09-08). The
   icon/banner art is generated and finalized (see
   `content/watcher-pov/mascot/channel-rebrand-prompts.md`) for whenever that rename
   actually happens — not yet applied to the real channel.
2. **Choose the next real video concept** — Pharaoh's Servant is the current
   lean (`content/watcher-pov/concepts.md`), now under
   the actual post-pivot format (rank-ladder, Trueline, the Watcher cameo),
   unlike Tomb Robber which shipped pre-pivot.
3. **Close the open backlog** in `research/inventory.md` §5 as it comes up —
   monetization mechanics/timeline (§4), the video-editing-automation
   thread (§2b — Resolve MCP under validation as of 2026-09-08), and any new
   tooling questions a real video surfaces. This is no longer the main
   thread, just upkeep alongside building.

This list is expected to keep evolving — update the agenda in `inventory.md`,
not just here, and check `research/index.md`'s "Where we left off" for the
most current pick-up point.

## Working style for this phase

- This is build-and-validate, not discussion-and-decide. Scaffolding
  automation (agents in `.claude/agents/`, skills in `.claude/skills/`) is
  expected — that's how the pipeline actually gets run, not just planned.
- Validate a new tool or step at small scale before trusting it at full
  scale — the Sollo lesson (`research/inventory.md` §2a): a 50-scene batch
  surfaced consistency problems only after the credits were spent. A few
  items first, then the full batch.
- Keep findings, decisions, and open questions in `inventory.md` as we go,
  not just in chat — it's the live index of what's settled and what's still
  open, and other files (`WORKFLOW.md`, agents, skills) point back to it
  rather than duplicating it.
- Log any change to `WORKFLOW.md`, an agent, or a skill in `CHANGELOG.md` —
  see "Where things live" above.
- Keep pushing back where a tool or the original guide is vague or a
  cheaper/better alternative exists — that instinct is what got the toolchain
  to its current state and shouldn't stop just because the phase changed.
- **Costs always in sterling (£/GBP), never dollars** — whenever a cost gets
  echoed back in chat or written into a skill/agent/research doc (API
  pricing, per-image/per-video costs, subscription fees), convert to £
  first. Source pricing (Google's Gemini API docs, Syntx, etc.) is often
  quoted in USD — do the conversion, don't just relabel the number.

## Token usage hygiene

This project leans on tools that can each burn tens of thousands of tokens in a
single call — `/watch` (~50-80k tokens per video at the default `balanced`
detail, via extracted frames), and `generate-scenes` (Claude-in-Chrome
screenshots, plus the per-scene QC image reads that replaced
`scene-prompter`'s old Mode 4 batch-audit as of 2026-09-08 — see that
skill's own doc). Every turn re-sends the full conversation so far, so an early
heavy dump that stays in context keeps getting paid for on every subsequent
message, not just the turn it arrived on — that compounding is what actually
burns through a 5-hour usage window, more than any single call does. These
rules exist to stop that from happening silently.

**Why this matters mechanically**: a compact's cost scales almost 1:1 with
however much context exists when you run it — it has to read the whole thing
and rewrite a summary, a full cache-write every time. It is never free.
`/clear` or a fresh session, by contrast, cost close to nothing — there's
nothing to re-read, just a reset. So the real question is never "does this
feel like the same task," it's "does anything in context still need to
survive that isn't already written down somewhere" — if not, clearing is
strictly cheaper, regardless of session length.

**Compact when:**
- A heavy visual/data payload (frames, screenshots, image reads, a large
  VidIQ dump) has already been distilled into a written note in
  `inventory.md`, `concepts.md`, `scene-prompts.md`, or the changelog — the
  raw payload has no further reference value, so keeping it in context is
  pure waste.
- You're about to run another heavy operation of the same kind in the same
  session (e.g. `/watch`-ing a 3rd competitor video) and earlier
  frames/screenshots are still sitting there unused.

Don't bother compacting mid-task, while you're still actively reasoning about
the visual detail currently in context — compacting loses fidelity right when
it's needed.

**`/clear` or a fresh session instead of compacting, when:**
- Moving to a genuinely different agenda item (e.g. done with tooling
  research, moving on to monetization research) — nothing in the old thread
  carries forward; just point the new session at `inventory.md`.
- A discrete deliverable just finished (a scene batch, a scored script) —
  that's a natural seam.
- The session is already near the usage cap. `/compact` has to read the whole
  bloated context to summarize it, so late in an expensive session a fresh
  start can be cheaper than compacting.
- **Concrete guardrail**: if a compact would process more than ~150k tokens
  and nothing currently in context is undocumented, default to `/clear` or a
  fresh session instead — a token count is a firmer trigger than "does this
  still feel like the same task," which is easy to talk yourself past
  mid-flow. (One real session on this project ran 8 days across the entire
  research phase under one continuous thread and compacted four times at
  500k-800k tokens each before this was caught — the agenda-item trigger
  above was true many times over in that window, but nothing forced the
  question. Don't repeat that.)

`/clear` and a fresh session cost the same (both near-zero) — they differ in
scope, not price. Use `/clear` to drop dead context without leaving the
window; use a fresh session when the work itself has moved on and a separate,
cleanly-titled transcript is worth having for later reference.

**Delegate to a subagent (`Agent` tool) *before* the heavy step, not after:**
anything about to dump images/frames/large payloads into context, where only
a small distilled result is actually needed back, should be dispatched to a
subagent up front rather than run directly and cleaned up with a compact
afterward. `generate-scenes` already does this — batches of 5-8 scenes per
subagent, final `.jpg` files land on disk, only a short pass/fail summary
re-enters the main thread — use that as the template. Apply the same pattern
to:
- `/watch`, when reviewing several competitor/outlier videos in one research
  pass (one subagent per video or small batch; written retention/structure
  notes come back, not the frames)
- Any VidIQ call whose useful output is a verdict/comparison rather than the
  raw per-item media data

Don't over-delegate cheap text-only calls (a single inventory.md edit, one
VidIQ keyword lookup) — subagent dispatch has its own overhead and breaks the
interactive back-and-forth this project benefits from.
