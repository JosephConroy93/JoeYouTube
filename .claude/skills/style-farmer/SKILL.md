---
name: style-farmer
description: Pulls representative on-screen frames from named competitor YouTube videos for comparative visual-style analysis, downloading only short clip sections (never a full video) and extracting one frame each. Saves to research/style-references/ and logs an index row. Use when a concept's visual-style lean needs checking against what competitors actually render on screen, or when a competitor's render style needs capturing as a saved reference image.
---

# Style farmer — competitor frame capture

## Hard rule

Every `yt-dlp` call that fetches video includes `--download-sections`. A
call without it downloads the whole video; stop and fix it. No step here
needs the full file — a few seconds around one timestamp yields one frame.

## Prerequisites

- `yt-dlp` and `ffmpeg` on PATH: `which yt-dlp ffmpeg`.
- Know which video(s) to pull: a URL, or a title + channel from a concept's
  research file. This skill does no competitive discovery.
- Output folder: `research/style-references/` unless the operator names
  another.
- Scratch: the session's absolute scratchpad directory, never a folder
  inside the project.

## Per-video flow

`scripts/grab-frames.sh <url> <out-dir> <label> [MM:SS,MM:SS | auto:N]` does
steps 2–5 in one call (4 s windows at ≤720p, one PNG per timestamp) and is
what `channel-farmer` invokes. The manual steps below are the same thing
spelled out.

1. **Resolve the URL.** With only a title + channel:
   ```bash
   yt-dlp "ytsearch1:<title> <channel>" --print "%(title)s | %(channel)s | %(webpage_url)s" --no-warnings
   ```
   Confirm the printed title and channel match what was asked for before
   downloading anything.
2. **Get duration** (metadata only):
   ```bash
   yt-dlp --print duration --no-warnings "<url>"
   ```
3. **Pick 2–3 timestamps** at roughly 25%, 50%, 75%. Skip the first and
   last ~5% (bumper, sponsor read, outro) unless the video is too short for
   that to leave anything.
4. **Download a ~5 s window per timestamp**, one call each (easier to redo
   a single bad timestamp):
   ```bash
   yt-dlp -f "bv*[height<=720]/b[height<=720]/bv*/b" --download-sections "*MM:SS-MM:SS" \
     -o "<scratch>/<label>.mp4" "<url>" --no-warnings --force-keyframes-at-cuts
   ```
   `bv*` takes the video-only stream (signed-in sessions get no muxed `best`); 720p is enough for a style reference.
5. **Extract one frame per clip:**
   ```bash
   ffmpeg -y -i "<scratch>/<label>.mp4" -frames:v 1 -q:v 2 "<scratch>/<label>.png" -loglevel error
   ```
6. **Read the candidates and pick one.** Reject frames on a burned-in
   caption, mid-roll ad, logo bumper or title card; reroll a nearby second
   (`MM:SS+2`) via steps 4–5 rather than settling.
7. **Save and name** as `research/style-references/<Channel Name>.png`, or
   `<Channel Name> - <label>.png` for several frames from one channel.
   Strip `< > : " / \ | ? *` from the name.
8. **Clean up** the scratch clips and frames. A just-read `.mp4` can hold a
   Windows file lock briefly; if deletion fails once, retry a moment later
   rather than looping.

## Comparative note — the deliverable

Files alone are not the output.

- Classify each channel's production method in plain terms: painterly or
  illustrated, photoreal AI video, 3D render, game-engine footage,
  stick-figure or simple 2D, live action. Usually obvious from one frame,
  and the biggest single differentiation signal.
- Append one row per saved frame to `research/style-references/index.md`
  (create it with the header if absent), matching its existing columns:
  ```
  | File | Channel | Video | Timestamp | Style | Date | Notes |
  ```
  `Video` is a markdown link, `Style` a one-line descriptor, `Notes` which
  concept or question the pull served.
- If the run served a specific concept, add a short note to that concept's
  research file (competitive-check section) so the finding sits next to the
  decision it informs.

## Batching

More than ~3 videos: one general-purpose subagent per video running steps
1–8, returning only the saved path plus a one-line descriptor; 3–4
concurrent at most.

## Gotchas

- **Confirm the search hit** (step 1). A wrong video saved under the right
  channel name is worse than a slow search.
- **A frame is a snapshot.** A channel can switch style mid-video
  (establishing shots versus close-ups). If the first frame looks ambiguous,
  pull another timestamp before writing the note.
