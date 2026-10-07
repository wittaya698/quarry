# 14 — Pad blend: flattening a Pad never steepens the ground around it

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

The Terrain Builder holds each Pad level out to its radius plus a 3 m margin, then eases back over 6 m by blending the *height* from the Pad's level to the natural ground (`_flatten_pads`). Where the natural ground is already falling away beyond the Pad, this squeezes the fall into the blend and steepens it.

Found in 07: tight-courtyard's refined Surface peaks at 13.0°, but its Terrain peaks at 17.6°, 14 m from the terrace's centre. That misses the "flat" Reading (15°) and steepens fountain→terrace from 11.9° to 16.7°. The terrace's flat top was already level out to 11 m, so the Pad didn't need any flattening.

Ease the *correction* instead (the Pad's level minus the natural ground at the Pad's edge), so that ground already level under a Pad comes out unchanged.

## Acceptance criteria

- [ ] Where the ground under a Pad and its margin is already level, flattening changes no height anywhere (tested)
- [ ] A Pad on a slope is still level on the Terrain, and the Pad Check still passes (existing tests)
- [ ] The approved Round 3 tight-courtyard Terrain passes its "flat" Reading

## Blocked by

- None
