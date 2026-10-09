# 03 — All Blockout Checks: Surface overlap, slope, Brief Check, Readings, Pads

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

Make the Blockout and its Checks complete, end to end through the fake Agent and `status`.
- **Surface:** **Zones** may overlap. Height combines in **Stacking Order** according to each Zone's **Combine Mode** (add, max, replace), and every surface value comes from the topmost Zone alone. Checks and the Terrain Builder share this single definition of height.
- **Slope-aware walking:** walk time now accounts for slope along the Path, and a Max Walkable Slope Check runs on every measured Path.
- **Brief Check:** before any Draft, flag *provable* impossibilities, namely a Walk Target that cannot fit in the footprint, or a reference to an undefined Waypoint. A failing Brief Check blocks drafting. Hard-but-possible Briefs pass.
- **Readings:** the Blockout carries the AI's interpretation of each mood phrase, with a Reason. Measurable Readings become Checks; unmeasurable ones are shown but not checked.
- **Pads:** every Landmark has a Pad, which the Blockout sizes and a flatness Check verifies. AI-chosen Landmarks are marked, and decorative Paths are allowed.
- **Misses:** when a target is missed, the Blockout is still delivered with a Reason owning the miss. The Brief's targets are never rewritten.

## Acceptance criteria

- [x] Overlap fixtures pass for each Combine Mode and for Stacking Order; surface values come from the topmost Zone only
- [x] A Path over a known slope gives the expected slope-adjusted walk time, and fails the Max Walkable Slope Check above the limit
- [x] Brief Check flags a Walk Target that is too long for the footprint and an undefined Waypoint, and blocks drafting; a hard-but-possible Brief passes
- [x] Measurable Readings appear as Checks; unmeasurable ones appear without pass/miss
- [x] Each Landmark has a Pad with a flatness Check; AI-chosen Landmarks are flagged; decorative Paths are not measured
- [x] A Blockout that misses a target is still produced, with a Reason naming the miss, and the Brief is unchanged
- [x] All Checks run identically on any surface, so the same Check code serves Checkpoint #2 later
- [x] Tests cover all of the above through public interfaces

## Blocked by

- `01-tracer-brief-to-approved-blockout.md`
