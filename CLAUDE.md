# AI YouTube Project — faceless channel pipeline

## Phase: production

Two videos have been made end-to-end (Tomb Robber, published 2026-09-04;
Pharaoh's Servant, rendered 2026-09-12). The toolchain is locked and the
pipeline is being run repeatedly, not designed. For what is true right now,
read [research/index.md](research/index.md)'s "Where we left off" — never
this file's narrative.

## Where things live

- [WORKFLOW.md](WORKFLOW.md) — the as-is process, Step 0 to Step 12.
- [.claude/conventions.md](.claude/conventions.md) — invocation contract
  (`<series>/<slug>`), folder layout, every schema and status vocabulary.
  Change a schema here first.
- `.claude/agents/` (`script-writer`, `scene-prompter`), `.claude/skills/`
  (one folder per step, with `scripts/` where the step is code),
  `.claude/formats/` (script formats: `rank-ladder`, `explainer`).
- `content/<series>/series.md` and `content/<series>/<slug>/video.md` —
  the only place series- or video-specific values live (voice, style,
  chapter naming, mascot, fps). Agents and skills never hardcode them.
- `content/styles/style-bible.md`, `content/prompt-hardening-rules.md`
  (read every chapter) with `content/prompt-hardening-log.md` (its incident
  archive, read on demand), `content/sfx/` — channel-level assets.
- **Files agents read on every run stay short.** Rules, configs and format
  modules are one line per rule; history and incidents live in archives
  that are opened only when needed.
- `research/` — the research record: `index.md` (start here: status table
  and where we left off, kept short), `index-history.md` (older hand-offs,
  on demand), `inventory.md` (findings and decisions), `artifacts/`.
- [CHANGELOG.md](CHANGELOG.md) — one line plus the why for every change to
  WORKFLOW, an agent, a skill or a format. Diffs live in git.

**Reading large files**: read by section, never whole. `inventory.md`,
`competitor-titles-index.md`, `concepts.md`, `sources.md`, `SOURCES.md`,
`style-references/index.md` and every `batch-log.md`: grep for the heading
or row, read that. `CHANGELOG.md` is append-only: add the line, don't read
the file. A new session reads `research/index.md` and nothing else until
the work needs it.

## Source control

The project root is a git repo; only the core is tracked (`.claude/`,
`WORKFLOW.md`, `CLAUDE.md`, `CHANGELOG.md`, `.mcp.json`, `tools/`).
`content/` and `research/` are local. Commit each core change with a
CHANGELOG line; branch for anything larger than a fix. The Resolve MCP
server is a submodule under `tools/`.

## Working rules

- **Validate at small scale before trusting at full scale** — a few items,
  then the batch.
- **Judge against the source, never against our own output.** Style checks
  compare renders with the channel frames the style came from; an approved
  render or reference is never the benchmark, because it can carry the same
  drift. A flagged style deviation stops the batch.
- **Nothing is done until a rendered or measured artefact proves it.** A
  `success` return or a readback alone is not proof (seven false-success
  checks in one session taught this).
- **Docs are run instructions.** No dates, no "confirmed", no tool
  comparisons, no incident narrative in agents, skills or WORKFLOW. History
  goes in CHANGELOG and commits.
- **Series-agnostic core.** A new series or format is a new `series.md` or
  format module, never an edit to an agent.
- **Costs always in sterling.** Convert USD source pricing before writing it down.
- **Keep pushing back** where a tool is vague or a cheaper/better route exists.
- Deletion of anything under `content/` is the operator's manual step;
  skills archive, they don't delete.

## Model routing

Pin the model on every subagent dispatch (`model` on the Agent call, or
`model:` in an agent's frontmatter). The main session stays on the model
the operator chose.

| Model | Work | Why |
|---|---|---|
| **Opus** | `script-writer` (write, revise, score); `write-prompts` (the driving session, Step 8); Step 3 research synthesis; any call where a lookup contradicts the script | Judgment: contested sources, tone, consistency across a whole video. Errors here cost the most downstream. |
| **Sonnet** | `scene-prompter` beat sheet; Step 6 visual lookups; transcript breakdowns and comment mining; `channel-farmer` data, frame and `/watch` passes; image QC against a checklist (`validate-scenes`, reference-image audits, `plan-ken-burns` image confirmation); style-render comparisons | Structured search-and-summarise or checklist work against a precise brief. |
| **Haiku** | Batch-log reconciliation, archiving, status polls, word counts, file inventories | Pure mechanics. |

Escalate a single disputed item one tier up; never re-run a whole batch on
a bigger model because one result looked wrong.

## Token hygiene

Every turn re-sends the whole conversation, so a heavy payload left in
context is paid for on every later message.

- **Delegate before the heavy step**: image reads, video frames, large
  VidIQ dumps and multi-file audits go to subagents that return a short
  written result. `validate-scenes` (5–8 images per subagent) is the
  template.
- **Compact** once a heavy payload has been distilled into a file and
  nothing in context still needs it; never mid-task.
- **Clear or start a fresh session** when moving to a different agenda item,
  after a discrete deliverable, or when a compact would process more than
  ~150k tokens and nothing undocumented remains. Clearing is near-free;
  compacting is not.
- Don't delegate cheap text-only calls; the overhead isn't worth it.
- **Long subagent tasks write their deliverable file first and update it as
  they go.** A status line or summary claiming work is done means nothing
  until the file it points to exists: a research pass once wrote "research
  complete" into `concepts.md` and was cut off before the research file was
  ever created.
