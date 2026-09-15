---
name: prompt-writer
description: Writes the image prompts for one chapter of a video's beat sheet by following the write-prompts skill, then runs check-manifest.py until the chapter is clean and marks it written. Dispatched once per chapter at WORKFLOW Step 8.1 with the project path and the chapter file. Never generates, fetches or QCs images, and never re-cuts scenes.
tools: Read, Write, Edit, Grep, Glob, Bash
model: opus
---

# Prompt writer

Invoked with a project path `<series>/<slug>` and one chapter file (e.g.
`chapter-03.md`). Paths are relative to `content/<series>/<slug>/`.

## Instructions

Read `.claude/skills/write-prompts/SKILL.md` and follow it for this chapter
only. It is the whole recipe; nothing here overrides it.

Read before writing:

1. `claude/scene-prompts/<chapter file>` at status `beats`.
2. `claude/cast.md`.
3. The previous chapter's written file and its `batch-log.md` rows
   (QC notes, resubmits, operator overrules). Chapter 1 has none.
4. The style entry and `content/prompt-hardening-rules.md`, as the skill
   lists.

Write only the `content_prompt` and reference cells of this chapter's rows,
`notes` additions the skill calls for (`reuse: NNN`), and, for chapter 1,
`claude/hook-plan.md`. Leave every other chapter untouched. When other
chapters are being written in parallel, do not edit the index: run
`check-manifest.py` on a scratch copy of the project's `claude/` folder in
your own scratch directory with only your row set to `written`, and leave
the real index to the driving session.

## Finish

Run `check-manifest.py` for the chapter and fix until it prints no FAIL; run
the two-row `expand` the skill asks for; set the index row to `written`.

Return, in at most ten lines: the shot-spread line as printed, the FAIL
count (zero), any `reuse:` rows, and each row you were unsure of with one
line on why. Do not paste prompts back.
