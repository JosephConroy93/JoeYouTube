---
name: channel-farmer
description: Turns one YouTube channel into everything this pipeline needs to make an adjacent video in its visual and narrative style — a channel dossier (stats, title patterns, structure, register, audience signals, concept seeds), transcript breakdowns, competitor-index rows, on-screen frames, a validated style-bible entry with exemplar, and a format module if the channel's shape isn't already covered. Use when the operator names a channel worth emulating or checking against.
---

# Channel farmer

Invocation: `channel-farmer <channelId | @handle> [--lean "<what to make of it>"] [--images N]`.
Layout and credentials: `.claude/conventions.md`. Heavy phases run in
subagents so frames and transcripts never enter the main thread.

## Output set

| Artefact | Path | Convention |
|---|---|---|
| Dossier | `research/channels/<channel-slug>/dossier.md` | sections below |
| Titles | `research/artifacts/competitor-titles-index.md` → channel section with pulled date | existing |
| Transcript breakdowns | `research/artifacts/transcripts/<videoId>.md` + index row | existing; paraphrased, never verbatim |
| Frames | `research/style-references/<Channel> - NN.png` + index rows | existing (`style-farmer`) |
| Style entry | `content/styles/style-bible.md` → `## <StyleName>` with STYLE/NEGATIVE blockquote; exemplar `content/styles/examples/<StyleName>.jpg` | existing |
| Format module | `.claude/formats/<format>.md` (only if no existing module fits) | 🟡 until a video runs on it |
| Series proposal | a `series.md` value block inside the dossier (never written to `content/`) | operator copies it |

## Budget (state it before starting; stop at the cap)

- VidIQ: stats 5 · videos 5–10 · trends 5 · outliers 5 · transcripts 5 each (×3) · `vidiq_video_watch` 25 (×1) → about 60–65 credits.
- Gemini: up to **10 images** (`--images`, default 10) for style validation, ≈ £0.37 at 2K.
- `/watch` in a subagent: one video, `efficient` detail (≤50 keyframes), never in the main thread.

## Phase A — data (main thread, cheap)

1. Resolve the channel (`vidiq_channel_search` by handle if only a name is known).
2. Grep `competitor-titles-index.md` for this channel's heading and read only that section; if it was pulled within a week, reuse it; otherwise pull `vidiq_channel_videos` popular + recent (long) and write/refresh the section with today's date.
3. `vidiq_channel_stats`, `vidiq_channel_performance_trends`, `vidiq_outliers` with `channelIds`.
4. Choose **three study videos**: the top breakout, the most-viewed, and a recent typical upload (median views). Record ids, titles, durations.

## Phase B — narrative (subagents)

1. One subagent per study video: pull `vidiq_video_transcript` (check the transcript index first), write the breakdown file in the cache's format: structure with timestamps, opening device, chapter/section unit and callout wording, register (person, tense, temperature), runtime and pace, hook fact placement, CTA placement, ending device, well-trodden angles. Return a 10-line summary.
2. One `vidiq_video_watch` on the top video with the prompt: "scene-by-scene: what is on screen per section, how often the visual changes, text overlays, title cards, transitions, motion (static/zoom/pan/animated), character or mascot recurrence". Poll `vidiq_job_poll`; save the walkthrough to `research/channels/<slug>/watch-<videoId>.md`.
3. Optional audience pass: `vidiq_comment_insights` discover on the channel's niche.

## Phase C — frames (subagent)

1. `style-farmer/scripts/grab-frames.sh <url> <out> "<Channel>" auto:6` on each study video (18 frames), saved to `research/style-references/` with index rows.
2. `/watch` the top video at `--detail efficient --max-frames 40` inside the subagent; it keeps the 6 most representative keyframes (copied to the same folder) and returns a written visual description, never the frames: production method, line/paint/render treatment, palette and lighting, character proportions and face treatment, background density, text and UI habits, aspect and framing habits, what changes between wide and close shots.

## Phase D — style entry and validation (subagent + Gemini)

1. **Measure before writing** (subagent, Sonnet, pixel measurement not eyeballing) on at least 8 frames that show full figures, **including figures with bare arms or legs**: head-heights tall, head width vs shoulders, head shape, exposed-skin colour sampled against the head, outline stroke width on head vs body vs background, eyes, neck, hands, whether heads are tinted by scene light. If no study frame shows bare skin, grab frames that do before writing.
2. Write the `## <StyleName>` entry from those numbers: plain description, the **STYLE:**/**NEGATIVE:** blockquote (same shape as existing entries; hard numbers for proportions; an explicit skin rule; no fixed palette unless the channel has one; 16:9), a `Source frames:` line listing 4–6 of the measured frames by path, and an `Identity:` line (`faces` or `costume`). Name it for the look, not the channel.
3. `scripts/style-test.ps1 -Style <StyleName> -Out research/channels/<slug>/style-test/round-1 -Count 3`. The test prompts must include **one figure with bare arms and legs** and one wide shot, so skin and proportions are exercised, not hidden by clothing.
4. **Judge renders against the source frames, never against other renders.** Build a side-by-side (render beside a source frame at the same height) and check the measured numbers on the render. If two or more miss, revise once and render round 2; stop at the image cap regardless.
5. **Operator gate**: show the side-by-sides to the operator. The entry is not usable until the operator approves it against the channel's frames. Only then save the exemplar `content/styles/examples/<StyleName>.jpg` and record the validation result (images, measured numbers, what still drifts) in the entry.

## Phase E — dossier and format (main thread)

`research/channels/<slug>/dossier.md` sections: Identity (id, handle, subs, cadence, country, niche) · Performance (trend curve, breakout ratio, top 5 titles with views) · Title patterns · Format (which existing module fits, or the new one) · Structure and register (from Phase B) · Visual style (from Phase C/D, with the style name) · Audience signals · Three adjacent concept seeds (each: title, hook, why it clears the competitor-clash check) · `series.md` proposal block · Sources (every file written).

Format decision: if the channel's structure is `rank-ladder` or `explainer`, name the module and note any deviations worth a future variant. Otherwise draft `.claude/formats/<format>.md` with the standard headings (Register · Opening · Structure · Ending · Runtime · Score dimensions · Mandatory reads), marked 🟡, with the study videos as evidence.

## Rules

- `vidiq_video_watch` describes *content* well and *motion* badly: it reported rigged animation on a body that is stills with Ken Burns. Motion classification comes from the frames pass (measure: a uniform scale between two frames of one shot = Ken Burns; local change with a static background = image-to-video) or from the operator, never from the walkthrough.
- `/watch` on Windows needs `PYTHONUTF8=1` (its focused-mode line prints a non-cp1252 character) and copies the yt-dlp cookie file into its working directory: delete the work dir when done. Keep the yt-dlp config's cookie path in forward slashes.

- Never store a transcript verbatim; breakdowns only.
- Frames are references for describing a style, not assets to reuse.
- The style entry must be reproducible from its own text: a validation that only works with a reference image attached is a failure.
- Say which of the four VidIQ-based steps were skipped and why, so a later run can fill them.

## Status

🟢 First full run done (The Explainer Boss, 2026-09-13): ~50 VidIQ credits, 6 Gemini images, dossier + Eggline entry + three breakdowns + 36 frames. Audience pass skipped that run.
