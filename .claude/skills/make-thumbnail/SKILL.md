---
name: make-thumbnail
description: Builds a video's thumbnail in the series' locked cream-card layout — 2–3 hook words stacked on the left in the series font with one accent line, one validated scene still as a tilted outlined card on the right — from the scene images already on disk, no image generation. Writes thumbnails/<name>.jpg plus a size-check sheet. Use at WORKFLOW Step 10, after the edit; make two for YouTube's Test & Compare.
---

# make-thumbnail

Invocation: `make-thumbnail <series>/<slug>`. Layout: `.claude/conventions.md`.
Executed by `scripts/thumb.py`; colours and font are `series.md`'s `thumbnail.*` keys.

## Steps

1. **Pick the line.** 2–3 words, one per line where they fit, readable at 168 px
   wide, and **it has to land cold**, on a viewer with no context: a line
   distilled from the script's own conclusions reads as nothing to a
   scroller, however well it summarises the video. Take a concrete fact
   from the subject instead.
   **A checkable claim is checked; a characterisation is not.** A number, a
   date, an event or an attribution goes through the research file's
   fact-check section exactly as a script line does, and a contested point
   becomes a question, never a resolution. An opinion or a framing
   ("London's most dangerous gang") is not a claim and needs no source:
   a title and a thumbnail exist to earn the click, and the operator has
   ruled characterisation fair there, though it stays forbidden in
   narration. The line adds the stake and never restates the title.
2. **Pick the still.** One validated `scene-generation/` image: the protagonist
   with a strong emotion, or one striking object the line points at. Choose from
   a contact sheet of shortlisted ids (grep the beat sheet for the line's
   subject first), never by opening every image.
3. **Build** one per candidate:

   ```
   python .claude/skills/make-thumbnail/scripts/thumb.py <series>/<slug> --name <A-slug-of-line> --scene <id> --centre <0-1> --zoom <>=1> --ymid <0-1> --line WORD --line "[ACCENT]"
   ```

   `--centre` is where the card's crop sits across the still (0 left, 1 right),
   `--ymid` the same vertically, `--zoom` how far the crop punches in (1 is the
   whole scene). **Crop so the subject's head is at least 18 px at 168 px wide** —
   `head_px = head_in_still * zoom * 0.0424` for a 2752-wide still. A full-height
   scene crop of a wide shot leaves a head around 9 px, which reads as texture,
   not an expression. Zoom per still, not to a fixed number: a shot that already
   fills the frame with a figure needs 1.2, a wide one needs 2.3.
   `--card` scales the tilted card (1 is the standard layout); it slides
   right as it grows so it does not eat the text block, and its outer edge
   bleeds off the frame. Above about 1.3 the text clips anyway - check the
   168 px panel, not the big one.
   A `[bracketed]` line takes the accent colour. `--scene` takes only the
   canonical still; `--still <file>` names another file in `scene-generation/`,
   such as an attempt whose QC flaw falls outside the crop. The script stops
   rather than overwrite; `--replace` archives the old file first.
4. **Check `<name>-sizes.jpg`**: the text reads at 168 px, the subject's face
   reads at 168 px, nothing sits in the bottom-right corner where YouTube puts
   the duration. Judge the 168 px panel, never the 1280 px one — that is the
   size the click is decided at.
5. **Record** each built file in `video.md`'s `thumbnail` key with the
   `--scene`, `--centre` and `--line` arguments that made it, so it can be
   re-cut without reverse-engineering the crop; two names are the Test &
   Compare pair, uploaded together at Step 11.

## Boundaries

- Never generates or edits a scene image; a still that needs changing goes back
  through `generate-scenes`.
- `vidiq_score_thumbnail` is for blur and brightness only, never pass/fail.
