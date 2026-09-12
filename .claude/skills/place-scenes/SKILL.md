---
name: place-scenes
description: Builds the first real cut of a video's timeline in DaVinci Resolve — every scene image, hook clip, and voiceover segment placed in order at the exact positions/durations `align-scenes`' `scene-timing.md` measured from real audio. Works by pre-rendering each visual to an exact-frame-count clip with ffmpeg and importing an authored FCP7 XML timeline, because Resolve's scripting API cannot set a still's duration or trim a placed clip at all. Confirmed working end-to-end 2026-09-11 on Pharaoh's Servant (201 clips + 6 VO segments, 22:07, frame-exact). Use once a video has a complete `scene-timing.md` and before `apply-ken-burns`, which needs timeline items to exist before it can attach a Fusion comp.
---

# Place scenes — real timeline assembly from `scene-timing.md`

Turns `scene-timing.md` (from `align-scenes`) plus a project's scene images,
voiceover segments, and any hook clips into an actual Resolve timeline:
every visual in the right order, starting on the right frame, held for
exactly as long as the real narration needs. `apply-ken-burns` runs *after*
this and depends on it — it attaches a Fusion comp to an existing timeline
item rather than creating one.

**Confirmed working end-to-end 2026-09-11** on Pharaoh's Servant: 198
scenes + 3 hook clips + 6 voiceover segments, 39,813 frames (22:07) at
30fps, 207/207 media linked, video and audio coterminous to the frame.
Verified by reading placed items back *and* by capturing the Resolve GUI —
not by trusting any call's `success: true`.

## Read this first: three API walls, and why the recipe looks odd

The obvious approach — import the JPGs, place them with
`media_pool.create_timeline_from_clips`' positioned `clip_infos` — **does
not work**, and fails silently rather than erroring. Three separate walls,
all confirmed live:

1. **A still's duration cannot be set before placement.**
   `media_pool_item.set_clip_property(clip_id, "Duration", ...)` returns
   `success: false` for a still (tried a bare frame count and a timecode
   string); the property reads back unchanged at `00:00:00:01`.
2. **A still's duration cannot be set at placement.** Passing
   `start_frame`/`end_frame` for a still is silently ignored — Resolve
   substitutes its own default still duration. Measured: a requested
   34-frame still landed as **120 frames (5.0s)**. This is what makes an
   otherwise "successful" build look broken — every scene 5s long, huge
   holes wherever the real slot was longer.
3. **A clip's duration cannot be changed after placement, at all.** From
   the MCP server's own verified limitations ledger: *"TimelineItem exposes
   GetStart, GetEnd, GetDuration, GetLeftOffset, GetRightOffset and
   GetSourceStart/EndFrame, but NO matching setters. A clip cannot be
   trimmed, slipped, slid, rolled, moved to another time/track, or have its
   duration changed once it is on the timeline."*

**Consequence**: the only way to make a picture occupy exactly 4.68s is to
hand Resolve a clip that *already is* exactly 4.68s. Hence the ffmpeg
pre-render in Step 4 — it is not an optimisation, it is the only path.

A fourth trap, for any *video* source you place directly:
`start_frame`/`end_frame` are **SOURCE** frames counted in the clip's own
frame rate, not the timeline's (consistent with the `timeline` tool's own
warning that "converting at the timeline rate is silently wrong"). A 30fps
hook clip on a 24fps timeline, given `end_frame: 216` computed at 24fps,
came out 7.2s instead of 9.0s — a ~20% error that only shows up as gaps.
Conforming everything to the project's fps in Step 4 removes this whole
class of bug.

**Dead end, don't retry**: driving Resolve's Python scripting API directly
from an external process (bypassing the MCP server) segfaults on this
machine — tried under Git Bash and native PowerShell, with both the system
Python 3.11 and the MCP server's own venv; access violation every time,
while the MCP server stayed connected fine throughout. Resolve itself was
unharmed. Use the MCP server.

## ⚠️ `timeline.lift_range` ignores `track_index` — it can delete your voiceover (found 2026-09-12)

Called with `track_type="audio", track_index=2, start_frame=37481, end_frame=37768`
to remove a 9-second SFX bed from A2, it refused — and the items it named as
blocking were **`06-level10.mp3` and `06-level10.wav`, the voiceover clips on
A1 and A3**. The range is applied across **every** track, whatever `track_index`
says. Its error then suggests `allow_partial_item_delete=True` to proceed; that
flag deletes *whole overlapping items*, so accepting it would have removed the
entire last 3.5 minutes of voiceover to clear a 9-second effect.

**Rules:**
- Never pass `allow_partial_item_delete=True` on a timeline that has anything on
  another track over the same frames — which, once voiceover is placed, is every
  frame.
- To replace an audio item, **disable it** (`timeline_item.set_clip_enabled`,
  `enabled=false`) and place the replacement on a **new track**. Non-destructive,
  reversible, and the API happily adds tracks.
- Audio levels cannot be set through the API either (`Volume` writes return
  `false`), so **bake the level into the file** before import — measure with
  `ebur128`, gain to target, fade, export WAV at the project frame rate so source
  frames equal timeline frames. Placement is then just `append_to_timeline` with
  exact `record_frame`s, which readback-verifies.

The versioning hook archived the timeline before the refused call (v7), so even
a mistake here is recoverable — but only if you notice.


### Two more, found the same day, same family

- **A mono WAV on a stereo track renders to the LEFT channel only.** The v2
  render measured a clean −16.2 LUFS integrated with the right channel at −inf —
  Joe heard it as "distant, coming from back-left, better in mono". Export
  voiceover as **dual-mono stereo** (`ffmpeg -ac 2`) before import. And add
  **per-channel RMS** (`astats=measure_perchannel=RMS_level`) to every audio
  verification: integrated loudness sums the channels and is completely blind
  to this.
- **`timeline.set_track_enable` can return `success: true` and do nothing.**
  It worked on A1 and silently failed on A3, twice, leaving the mono voice
  summing into the left channel (+6 dB). Always read back with
  `get_track_enabled`; if it disagrees, fall back to per-item
  `timeline_item.set_clip_enabled`, which did take. Then render and measure —
  readback on this API has lied enough today that it is a hint, not proof.

## Prerequisites

- Complete `content/<series>/<slug>/claude/scene-timing.md`. **Reconcile its
  row count against the chapter manifests before trusting it** —
  `align-scenes` shipped a file missing 3 rows the first time (nested
  double quotes in the bookmark broke its parse), which would have dropped
  3 scenes from the finished video. `grep -c` both and compare.
- `scene-generation/*.jpg`, `voiceovers/*.mp3`, and `hook/*.mp4` if the
  video has a cold open.
- `ffmpeg`/`ffprobe` on PATH.
- Resolve Studio running; `davinci-resolve` MCP server v2.213.2+.
- A local staging path outside OneDrive (`C:\Users\<user>\Videos\<slug>-<fps>\`).
  `media_storage.import_to_pool` intermittently returns `imported: 0` with
  no error for OneDrive-synced files.

## Step 1 — Pick the frame rate, on a fresh project, before any timeline

**Match the project to the only real motion footage you have.** Pharaoh's
Servant's hook clips are natively 30fps and everything else is stills
(frame-rate agnostic), so the project was set to **30fps** — no frame-rate
conversion on the one genuinely moving footage, and marginally smoother
slow Ken Burns moves. A 24fps project would have forced a 30→24 conversion
(dropping 1 frame in 5) on precisely the video's most dynamic 21 seconds.

Two hard constraints, both confirmed live:

- `project_settings.set_setting("timelineFrameRate", ...)` **fails once the
  project contains a timeline** (`success: false`). Set it on a freshly
  created project, before building anything.
- `timelinePlaybackFrameRate` **cannot be set from the API at all** — the
  server carries this as a verified limitation across versions. **Ask the
  operator to set it by hand**: Project Settings → Master Settings →
  Playback frame rate, before the first timeline exists, then read it back
  to confirm. If it stays mismatched, playback in the viewer runs
  off-cadence and audio *looks* out of sync even when the edit is perfect —
  a very convincing false alarm.

Also set `timelineResolutionWidth`/`Height` (both writable).

## Step 2 — Measure real durations, never assume them

`ffprobe -v error -show_entries format=duration -of csv=p=0 <file>` on every
voiceover segment; `cumulative_offset[segment_i] = sum(durations before i)`.
This is the offset `scene-timing.md` deliberately leaves out (its times are
segment-relative).

For video sources read the **video stream**, not the container: the hook
clips' `format=duration` said 9.031995s while the stream was exactly 270
frames @ 30/1 = 9.000s. The container figure is padded and will put your
frame maths out.

## Step 3 — Compute the plan, and close the gaps

Global position per scene: `cumulative_offset[segment] + start_seconds`.

**Critical: a scene must run until the *next scene starts*, not until its
own last narrated word.** Bookmarks end at a word; the next one begins
after a breath. On Pharaoh's Servant, honouring each scene's own end
produced **165 gaps totalling 109 seconds** of black frames. So:

```
duration_frames = frames(next_scene.global_start) - frames(this.global_start)
```

for every scene, with the last one running to the end of the final
segment's audio. Take the difference of the two *rounded frame numbers*
(not the rounded difference of the seconds) so rounding can never
accumulate drift. This also absorbs the handful of small negative gaps
where fuzzy-matched bookmarks overlap slightly (2 on this video).

Then assert, before touching Resolve: every scene's start equals the
previous scene's end (zero holes), no zero-length scenes, and the last
frame equals `frames(total_audio_duration)`.

## Step 4 — Pre-render every visual to an exact-frame clip

One clip per visual, at the project's fps, exactly as many frames as the
plan says, **and centre-cropped to true 16:9**.

Aspect matters here: Gemini returns 2K 16:9 as **2752×1536** (= 1.7917:1,
because its output dimensions quantise to multiples of 32 and exact 16:9 at
1536 tall would be 2730.67), and Wan returned the hook at 1926×1076 — so
*nothing* is exactly 16:9 and all of it would letterbox by ~4px on a 1080p
timeline. Crop, don't scale: keep native 2K height so Ken Burns has real
zoom headroom instead of softening on every push-in. Only upscale sources
that are genuinely below 1080p (this video's 10 text-cards are 1376×768 —
worth generating at 2K next time to avoid the 1.4x upscale).

```bash
# still -> exact-frame clip at the project's fps
ffmpeg -y -loop 1 -i "<scene>.jpg" -frames:v <N> -r <fps> \
  -vf "crop=<16:9 crop>" -c:v libx264 -crf 18 -preset veryfast \
  -pix_fmt yuv420p -an "<scene>.mp4"

# hook/video clip -> trimmed to its beat, conformed to the project's fps
ffmpeg -y -i "<hook>.mp4" -frames:v <N> -r <fps> \
  -vf "crop=<16:9 crop>" -c:v libx264 -crf 18 -preset veryfast \
  -pix_fmt yuv420p -an "<hook>.mp4"
```

- **`-frames:v <N>`, never `-t <seconds>`** — `-t` rounds up to the next
  frame boundary (`-t 1.41667` produced 35 frames where 34 were wanted).
- **`-an`** — strip audio. The original hook MP4s carry audio streams which
  otherwise land on A1 and get mistaken for the voiceover.
- **Verify each output's real frame count** with `ffprobe -count_frames`
  against the plan. All 201 matched on this video; a silent mismatch here
  becomes a silent sync error later.
- **Parallelise it** — 201 clips of 2K footage is ~36k frames. Serial was
  heading for 15-30 min; an 8-way thread pool over `subprocess` did it in a
  couple of minutes. Background the whole batch.
- Cost: ~260MB of intermediates for a 22-minute video (less than the source
  JPGs) and one generation of CRF-18 re-encode — visually transparent on
  held stills, and far gentler than YouTube's own transcode. Drop to CRF 12
  if it ever matters; near-identical frames make it cheap.

## Step 5 — Hook clips: cut at the narration's beats

A hook is footage running under the same audio segment that carries the
spoken hook narration, so its clips' arbitrary generated lengths have no
reason to match the narration. Check explicitly:

```
overrun = sum(hook clip durations) - first_body_scene.global_start
```

Pharaoh's Servant: 27.000s of footage against a 21.40s cue — a 5.60s
overrun. **Do not resolve this by trimming the last clip to fit** (the
first attempt did, gutting the hook's payoff shot from 9.0s to 3.3s — wrong).
Cut each clip where **its own narration beat ends**, read from the Whisper
transcript's word timings: an inter-beat pause of ~0.8s+ marks a boundary,
while normal within-beat gaps on this channel's voice run 0.4–0.6s.

| Beat | Narration ends | Clip | Slot | Trim from 9.00s |
|---|---|---|---|---|
| 1 | 7.92s | `006` (premise) | **7.92s** | −1.08s |
| 2 | 13.90s | `159` (reveal) | **5.98s** | −3.02s |
| 3 + 4 | 21.40s cue | `154` ("Chosen") | **7.50s** | −1.50s |

Sums to the cue exactly — no gaps, no gutted clip, modest trims, and the
last clip deliberately holds across beat 4's question ("So… how exactly did
that happen?", 18.24–20.60s), which is where the parked hook→Level-1
snap-zoom transition belongs.

There were 4 beats and 3 clips here; don't assume 1:1. Read which clip
covers which beat from the script's `## Hook` section.

**Root cause worth fixing upstream, not here**: this whole mismatch exists
only because the hook footage was generated blind at an arbitrary 9s before
the voiceover existed. Generating the voiceover right after script lock
(now flagged on `WORKFLOW.md` Step 7) means clips get cut to the beat in the
first place, and none of this arises.

## Step 6 — Author an FCP7 XML and import it

Do **not** try to assemble 200 clips through `create_timeline_from_clips`
or per-clip appends: the positioned form needs a media-pool UUID per clip
(unworkable at this scale through tool calls), and plain appends can't
place audio under the video — `AppendToTimeline` appends at the *timeline*
end, which after the video is laid down puts the voiceover after the
picture.

Instead author a single FCP7 XML (`<xmeml version="5">`) from the plan —
file paths, frame in/out, and record positions — and import it with
`timeline.import_timeline_checked(path)`. This places video and audio, at
exact frames, in one call, with no UUIDs involved.

Shape: one `<sequence>` with the project's `<rate><timebase>`, a
`<video><track>` of `<clipitem>`s (each with `<start>`/`<end>` as timeline
frames, `<in>0`/`<out>N`, and a `<file>` carrying `<pathurl>`), then an
`<audio><track>` of the segments, each with
`<sourcetrack><mediatype>audio</mediatype></sourcetrack>`.

- **Validate the XML locally before importing** (`xml.etree` parse). A
  mismatched tag — `</media></audio>` instead of `</audio></media>` — got
  the first attempt rejected, and the raw importer's own error was only
  *"Failed to import timeline (Resolve created no timeline)"*, which points
  at missing media rather than at the real syntax fault. `sanitize_media:
  true` is what surfaced the actual line number.
- Check `media.linked` vs `media.total` in the result (`207/207 linked, 0
  offline` here). Anything offline means a path problem.
- Import media into named bins first (`media_pool.add_subfolder` +
  `set_current_folder` per folder) so the pool is navigable — Hook /
  Scenes / Voiceover.
- Pathurls: `file://localhost/C:/...` with spaces percent-encoded.

## Step 7 — Verify against the plan

Never on `success: true` alone. Check:
- `timeline.get_current` → `end_frame` equals the planned total.
- `timeline_item.get_name`/`get_start`/`get_end`/`get_duration` on the
  first item, the last item, anything trimmed, and the first body scene.
  On this video: item 0 = hook `006` at 238 frames; item 2 = 225 frames
  (the trimmed `154`); item 3 = `001_level-one-title` starting at frame
  **642** = the 21.40s cue; item 200 = `198_...` ending at **39813**.
- The last audio item ends on the same frame as the last video item —
  picture and narration coterminous.
- Capture the GUI (PowerShell `PrintWindow` with `PW_RENDERFULLCONTENT`,
  recipe in `apply-ken-burns`) and *look at it*. The original broken build
  passed every numeric position check while being visibly full of holes,
  because only durations were wrong. A screenshot catches what readback
  doesn't.

## What this skill does NOT do

- **No Ken Burns motion or FX** — `apply-ken-burns`/`apply-particles`, run
  after this, on the items this creates.
- **Does not build the hook→body transition** — Step 5 leaves the window
  for it; the snap-zoom itself is parked, separate work.
- **No captions, loudness, colour, or export.**
- **Does not judge whether a measured duration reads well on screen** —
  editorial, same disclaimer `align-scenes` carries.
