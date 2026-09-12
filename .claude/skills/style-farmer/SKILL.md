---
name: style-farmer
description: Pulls representative on-screen visual-style frames from competitor YouTube videos for comparative art-style analysis — grabbing only short clip windows via yt-dlp `--download-sections`, never the full video, then extracting a frame with ffmpeg. Saves each to `research/style-references/<channel-name>.png` and writes a short comparative note. Use when a video concept needs its visual-style lean checked against what competitors are actually rendering on screen (not just their title/thumbnail), when Joe references a style lean and asks how it'd land against competitors, or whenever a competitor's animation/render style needs capturing as a saved reference image.
---

# Style farmer (competitor visual-style capture)

## Why this exists

Built 2026-09-03 after grabbing two competitor frames for the Roman legion
marching concept the slow way: opened a live browser tab, played the video,
screenshotted it — which doesn't produce a savable file — then, needing an
actual file, defaulted to `yt-dlp` with no section flag, which would have
pulled each competitor's **entire video** just to keep one frame. Joe caught
it before it ran. The fix that shipped instead — `yt-dlp --download-sections`
to fetch only a few seconds around a timestamp, then one `ffmpeg` frame pull —
is the whole point of this skill: never re-derive it under time pressure,
never default back to a full download.

## Hard rule

**Every `yt-dlp` call in this skill downloads video, not the whole video.**
If a call doesn't include `--download-sections`, stop — that's the exact
mistake this skill exists to prevent. There is no step in this flow that
needs the full file; a few seconds around one timestamp produces one frame.

## Prerequisites

- `yt-dlp` and `ffmpeg` on PATH — confirm with `which yt-dlp ffmpeg` before
  starting, don't assume.
- Know which competitor video(s) to pull from: a direct URL, or a
  title + channel from prior research (a concept's `concepts.md` /
  `research-*.md` "Competitive check" section, or a channel Joe names
  directly). **This skill does not do competitive discovery itself** — that's
  VidIQ's job in Step 1/3. This skill only captures what a video *looks like*
  once you already know which video matters.
- Default save location: `research/style-references/`. Use a different
  folder only if Joe names one.

## Per-video flow

1. **Resolve the URL.** If you only have a title + channel, confirm the
   right video before downloading anything:
   ```bash
   yt-dlp "ytsearch1:<title> <channel>" --print "%(title)s | %(channel)s | %(webpage_url)s" --no-warnings
   ```
   Check the printed title/channel actually match what was asked for — search
   can surface a wrong or near-duplicate video, and that's cheap to catch
   here versus after downloading.

2. **Get duration** (metadata only, no video bytes):
   ```bash
   yt-dlp --print duration --no-warnings "<url>"
   ```

3. **Pick 2-3 sample timestamps** spread through the video body — roughly
   25%, 50%, 75% of duration. Skip the first ~5% (intro bumper, sponsor read)
   and last ~5% (outro/CTA) unless the video is short enough that this leaves
   nothing.

4. **Download a short clip window per timestamp** — a `~5` second window is
   plenty for one clean frame:
   ```bash
   yt-dlp -f "best[height<=480]" --download-sections "*MM:SS-MM:SS" \
     -o "_tmp/<label>.mp4" "<url>" --no-warnings --force-keyframes-at-cuts
   ```
   `height<=480` keeps the clip small — this is a style/composition reference,
   not a quality benchmark. Run one call per timestamp rather than stacking
   multiple `--download-sections` flags in one call — simpler to reason about
   and to redo a single bad timestamp without re-running the others.

5. **Extract one frame per clip:**
   ```bash
   ffmpeg -y -i "_tmp/<label>.mp4" -frames:v 1 -q:v 2 "_tmp/<label>.png" -loglevel error
   ```

6. **Read each candidate frame and pick the best one.** Skip frames that land
   on: a burned-in caption/subtitle line, a mid-roll ad, a channel
   logo/bumper, or a title card — reroll to a nearby second (`MM:SS+2` or so)
   and re-run steps 4-5 rather than settling for a bad frame just because a
   timestamp guess landed wrong.

7. **Save and name.** Move the chosen frame to
   `research/style-references/<Channel Name>.png`. Sanitize the channel name
   for Windows filenames — strip/replace `< > : " / \ | ? *`.

8. **Clean up.** Delete the `_tmp/` clip and frame files once the best one is
   saved. A just-downloaded `.mp4` can still hold a Windows file lock
   immediately after `ffmpeg` reads it — if `rm -rf _tmp` fails once, don't
   loop-retry; a bare `rmdir _tmp` a moment later is enough, or just leave the
   empty directory, it's harmless.

## Comparative analysis output

Once frames are collected, actually compare them — that's the deliverable,
not just the files:

- Categorize each competitor's production method in plain terms: painterly/
  illustrated, photoreal AI-video-generated, 3D cinematic render, repurposed
  video-game-engine footage, stick-figure/simple 2D animation, live-action,
  etc. This is usually visually obvious from one frame and matters more for
  differentiation than any other single factor.
- Log each pull to `research/style-references/index.md` (create it if it
  doesn't exist yet) as one row: channel, video title + URL, timestamp
  sampled, one-line style descriptor, date. This turns the folder into a
  running index instead of a pile of unlabeled images, matching how
  `content/SOURCES.md` works for research sources.
- If this run was for a specific video concept, also append a short note
  (or extend the existing "Competitive check" section) in that concept's
  `research-*.md`, so the finding sits next to the decision it's informing
  rather than only living in a side index.

## Batching (more than ~3 competitor videos in one pass)

Dispatch one `Agent` (general-purpose) per video, same pattern as
`generate-scenes`: the subagent runs steps 1-8 for its one video and reports
back only the saved file path + one-line style descriptor. Clip bytes and
intermediate frame candidates never need to re-enter the parent conversation
beyond the one chosen frame each subagent reads to make its pick. Don't
parallelize past what's reasonable for local disk/bandwidth — 3-4 concurrent
subagents is plenty.

## Gotchas

- **Don't open a browser tab for this.** The earlier attempt used Claude
  Browser to play the video and screenshot it — that produces an image in
  the conversation, not a file on disk, and doesn't actually solve the
  "save a frame" problem. Reach for a browser only as a last resort, if
  `yt-dlp` can't reach a specific video (private/geo-blocked/deleted), and
  say so explicitly rather than silently falling back to it.
- **Confirm the search hit before downloading**, per step 1 — a wrong video
  saved under the right channel name is a worse outcome than a slow search.
- **A frame is a snapshot, not the full story.** One or two frames can miss
  a channel that switches style mid-video (e.g. establishing shots vs.
  character close-ups). If the first frame looks ambiguous or unrepresentative,
  pull a second timestamp before writing the comparative note, rather than
  generalizing from a single lucky/unlucky frame.
