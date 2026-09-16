---
name: make-thumbnail
description: Builds a video's thumbnail in the series' locked cream-card layout — 2–3 hook words stacked on the left in the series font with one accent line, one validated scene still as a tilted outlined card on the right — from the scene images already on disk, no image generation. Writes thumbnails/<name>.jpg plus a size-check sheet. Use at WORKFLOW Step 10, after the edit; make two for YouTube's Test & Compare.
---

# make-thumbnail

Invocation: `make-thumbnail <series>/<slug>`. Layout: `.claude/conventions.md`.
Executed by `scripts/thumb.py`; colours and font are `series.md`'s `thumbnail.*` keys.

## Steps

1. **Pick the line.** 2–3 words, one per line where they fit, readable at 168 px
   wide. Check it against the research file's fact-check section exactly as a
   script line is checked; a contested point becomes a question, never a
   resolution. The line adds the stake and never restates the title.
2. **Pick the still.** One validated `scene-generation/` image: the protagonist
   with a strong emotion, or one striking object the line points at. Choose from
   a contact sheet of shortlisted ids (grep the beat sheet for the line's
   subject first), never by opening every image.
3. **Build** one per candidate:

   ```
   python .claude/skills/make-thumbnail/scripts/thumb.py <series>/<slug> --name <A-slug-of-line> --scene <id> --centre <0-1> --line WORD --line "[ACCENT]"
   ```

   `--centre` is where the card's crop sits across the still (0 left, 1 right);
   a `[bracketed]` line takes the accent colour. `--scene` takes only the
   canonical still; `--still <file>` names another file in `scene-generation/`,
   such as an attempt whose QC flaw falls outside the crop. The script stops
   rather than overwrite; `--replace` archives the old file first.
4. **Check `<name>-sizes.jpg`**: the text reads at 168 px, the card crop keeps
   the face or object, nothing sits in the bottom-right corner where YouTube
   puts the duration.
5. **Record** each built file in `video.md`'s `thumbnail` key with the
   `--scene`, `--centre` and `--line` arguments that made it, so it can be
   re-cut without reverse-engineering the crop; two names are the Test &
   Compare pair, uploaded together at Step 11.

## Boundaries

- Never generates or edits a scene image; a still that needs changing goes back
  through `generate-scenes`.
- `vidiq_score_thumbnail` is for blur and brightness only, never pass/fail.
