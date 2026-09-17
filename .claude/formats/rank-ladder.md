# Format: rank-ladder

A single second-person life or career arc, segmented into explicitly
numbered levels the narration calls out by name. Loaded by `script-writer`
when `video.md` (or `series.md`) says `format: rank-ladder`. The sourcing
contract, gates and self-check live in the agent; this file holds only what
is specific to the shape.

## Naming

Levels, spoken: every rank video uses them (operator). Readers look in
`video.md`, then this table, then `series.md`. The card is the series'
cream chapter card with the `LEVEL N` label.

| key | value |
|---|---|
| `chapter.unit` | `level` |
| `chapter.heading` | `Level N. <Rank>.` |
| `chapter.file` | `level-NN.md` |
| `chapter.spoken` | `yes` |

## Two categories — classify the concept before research

- **A — narrative/pacing levels.** The writer chooses how to divide the
  story into escalating chapters: *your life as a [role]*, *after [event]*,
  *during [situation]*. Level count is chosen for pacing.
- **B — real-structure levels.** *Every rank within [system]*. Levels are the
  real system's named tiers; their count and names are dictated by research,
  not pacing. The structure needs full sourcing; the individual's journey
  through it is a composite (the agent's composite-archetype standard),
  never presented as a documented person.

## Register

Second person, present tense. The narrator is a companion telling one
person's story, not a documentary voiceover. Warm, plain-spoken, and close
to the person it happens to: every beat says what the moment costs them.
Contractions are normal speech here.

Restraint is understatement, never absence of feeling. What is forbidden is
melodrama, portent, narrator opinion about history, adjectives doing work the
facts should do, and any feeling the research cannot support. Hedges are
dramatised in-scene, never delivered as commentary about sources.

## Opening

- Cold-open straight onto the first level callout. No preamble.
- **An animated hook earns its place only if the narration under it carries
  the stake** (operator, 2026-09-16): the moving shots are not a substitute
  for telling the viewer what is at risk. Say what this life costs inside the
  first two sentences, and name a person by the fourth or fifth.
- **Split the animation budget** (operator, 2026-09-16): the same seconds buy
  more when some of them sit later. Keep about two thirds of the clips in the
  cold open and spend the rest on the **opening scenes of the early levels**,
  so motion returns the moment a level card clears. Weight them where the
  retention curve is steepest, not evenly: Level 2 lands at the cliff, so it
  takes **two** clips and the cut between them reads as the video restarting;
  Level 3 takes one; from Level 4 on, the curve has flattened and a clip there
  buys insurance on viewers who have already stayed. The fall needs a beat,
  not motion. Only the clip **under a card** needs the ~8 s beat (the card
  covers 3.8 s, the clip plays after it); a second clip in the same level is a
  normal scene at full motion, and wants clearly different framing or the two
  read as one drifting shot. Chosen at the beat sheet; `hook-plan.md` carries
  these shots alongside the cold open's.
- Open on status, not drama: withhold what the title promised; the hook
  question (the open loop the ending pays off) lands in the **first 8
  seconds** of narration after the callout, setup after it.
- One hard, specific, sourced fact early, delivered casually. If the
  research has none, leave it out and say so in the handoff notes.
- No CTA before the first reveal; CTA policy comes from `series.md`.

## Structure

- 8–10 levels, ~300–400 words each (Category B: the real tier count).
- Each level opens with its own callout in the series' heading pattern
  (`Level four, the boatswain. You are 22 now.`): role and age/stage stated
  immediately.
- Per level: what changed, what it costs, one concrete grounded specific only
  that rung would know.
- **A level's first beat after the callout is a problem, not a description.**
  The rung is introduced by something that is already going wrong on it —
  a demand, a cost, a thing withheld — and the description of the rung
  follows. A level that opens by explaining what the rung is spends its
  best seconds on exposition, which is where a viewer leaves (an external
  review put the structure score at 7/10 for exactly this).
- **A motif changes its angle every time it returns.** A ladder repeats its
  own engine (men die and you move up; nobody says the number), and the
  repetition is the point — but each return comes at it from a different
  side: whose death, what it bought, who noticed. The same phrasing twice
  reads as thematic repetition and costs the repetition score.
- Stack small open loops; first real reveal lands as a scene ~60–90 s in.
- The arc rises then falls; the last level is loss or collapse. A ladder that
  only ascends has no ending.
- Carry a personal thread underneath the ranks.
- A one-word/one-phrase reveal only works if its meaning was built earlier in
  the same passage.

## Ending

Three beats, in this order (the shape the genre's best endings use):

1. A callback image built only from concrete things already planted in the
   script, never a restated list of facts or ranks.
2. **One reflective sentence, under 20 words**, answering a question the
   video has been building toward. Not a summary, not a new fact, not a
   moral about history.
3. A small ordinary final image in the present tense, cut cold. No sign-off
   in the narration; the outro card carries the channel.

Cyclical is the usual first beat: another person at another threshold about
to make the same choice. Never a flat stop at the peak, never an outcome the
research leaves unknown.

## Runtime

20–25 minutes. Word count = target minutes × `wpm_measured` from
`series.md`. Runtime comes from more levels and more beats per level, never
from padding; if the research can't support it, write the honest shorter
script and say so.

## Score dimensions (Mode 3, 100 points)

| Dimension | Points | Floor |
|---|---|---|
| Opening, first 30 s: withholds the title's promise (8) · hard sourced fact delivered casually (8) · multiple small open loops (7) · voice established immediately (7) | 30 | 18 |
| Ending: reflective/cyclical (8) · lands the interpretive angle (7) · does not overstate the research (5) | 20 | 12 |
| Body: escalation holds (7) · first reveal as a scene ~60–90 s (6) · open loops paid off (6) · pacing varies (6) | 25 | — |
| Voice: second-person present sustained (5) · felt stakes carried with restraint, never flat, clinical or portentous (5) · consistent register; a hedge delivered as meta-commentary, a prose tell or a spelling off `voice.english` loses points here (5) | 15 | — |
| Research utilisation: obscure specifics over generic ones (5) · hedges handled as features (5) | 10 | — |

A script below either floor fails regardless of total.

## Variant: nine-level

Selected in `video.md` as `format: rank-ladder (nine-level)`. Everything
above applies, with these overrides:

- **Exactly 9 levels.** Level 1 is a 60–75 s cold open; Levels 2–8 are even
  in length; Level 9 is a short epilogue or inversion.
- **Callout**: "Level N. <Rank title>." — bare, and the first words of the
  level. Age or stage surfaces inside the level, never in the callout.
- **Card line**: one per level, 3–6 words, a hook statement that opens a
  loop the level pays off, never the rank title and never its incident
  given away ("The dead pay better"). Listed in the handoff notes as
  `| level | card line |`; the edit sets it on the level card beside a
  half-hidden still from later in that level.
- **Per level**: the rung named → what the rung really is, deflated → one
  incident → one aphorism → a **hand-off cliff** whose last line is the next
  level's premise.
- **Companion object** planted before 0:50 and returned in the last level;
  its meaning changes each time it reappears.
- **Ending**: reversal, the cyclical image, the one reflective sentence,
  then the final image. No moral about history, no sign-off.
- **Hook**: no factual hook required in Level 1; a flash-forward stake or a
  withheld reversal carries it. A sourced hard fact still lands inside the
  first two levels.
- **Runtime**: the video's `runtime_target` wins over the 20–25 minute
  default. Length comes from beats, never padding.

## Mandatory reads before writing

- `research/artifacts/script-craft-openings-and-retention.md`
- `research/artifacts/narration-registers.md` — only §1 "Read this first" and
  §3 "A. Immersive-dry"
