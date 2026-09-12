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
- `content/styles/style-bible.md`, `content/prompt-hardening-log.md`,
  `content/sfx/` — channel-level assets.
- `research/` — the research record: `index.md` (start here, status,
  where we left off), `inventory.md` (findings and decisions), `artifacts/`.
- [CHANGELOG.md](CHANGELOG.md) — one line plus the why for every change to
  WORKFLOW, an agent, a skill or a format. Diffs live in git.

## Source control

The project root is a git repo; only the core is tracked (`.claude/`,
`WORKFLOW.md`, `CLAUDE.md`, `CHANGELOG.md`, `.mcp.json`, `tools/`).
`content/` and `research/` are local. Commit each core change with a
CHANGELOG line; branch for anything larger than a fix. The Resolve MCP
server is a submodule under `tools/`.

## Working rules

- **Validate at small scale before trusting at full scale** — a few items,
  then the batch.
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
