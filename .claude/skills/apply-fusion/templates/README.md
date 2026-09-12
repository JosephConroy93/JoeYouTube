# templates/

`DoorwayDust.setting` — a Fusion group (`DoorwayEmitter` pEmitter →
`DoorwayRender` pRender → `DoorwayMerge`, Screen) for dust drifting from a
top-left doorway light source. The Merge's Background is the group's input:
connect the plate (or an upstream tool) there; the group output feeds the
Transform. No Glow is included — build one per scene if wanted.

**Baked values to adjust per clip** (from the clip it was exported on):
`DoorwayRender.Width 2752`, `Height 1536`, `GlobalOut 119` — set to the
clip's resolution and last frame, or the render is cropped/short.

**Reference emitter values**: `Number 4, Lifespan 200, Velocity 0.025,
VelocityVariance 0.01, Angle −30, AngleVariance 15, ParticleStyleBlob,
RectRgn 0.11×0.15 at Translate (−0.279, 0.05), ParticleStyle.Size 0.4,
Green 0.78, Blue 0.4`. Retune `Velocity × Lifespan` to ≤ ~0.4 for ambient dust.
