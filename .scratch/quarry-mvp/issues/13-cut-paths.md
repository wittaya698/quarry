# 13 — Cut Paths: a Path that grades its own strip of ground

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0005

## What to build

The AI can mark a Path as a **Cut Path**. Its strip of ground then rises evenly from its start Landmark's height to its end Landmark's, whatever the Zones beneath it do. This lets the AI force a route: a hill steeper than anyone can climb, with one trail winding up it.

- **Blockout:** a Path gains `cut` (default false) and, when cut, a `width` of at least 4 m, both justified in its Reason. Validation refuses a Cut Path narrower than 4 m. The Blockout owns both (ADR-0003, as extended by ADR-0005).
- **Ground at Checkpoint #1:** inside the strip the height follows the Path's even grade; at its edges the banks are sheer, like a flat Zone's rim. The strip lies above every Zone.
- **Refine Plan:** each Cut Path is a surface of its own, named for its Path (e.g. `camp→summit`) and refined exactly once, with its own roughness, vegetation, seed, slope profile and falloff. The falloff eases its banks, and its values win along the strip. Validation requires each Cut Path to be refined exactly once.
- **Terrain and Export:** the Terrain Builder builds the strip, and the `.glb` collision carries it.
- **Pages:** Checkpoint #1 draws a Cut Path as a band of its width. Checkpoint #2 lists its refinement next to the Zones'.
- **Prompts:** the Blockout prompt says when to use a Cut Path (a no-Shortcut walk, or a road into a slope), how its grade is worked out (height gained ÷ length), and that the hill around it must be steeper than the Max Walkable Slope to block Shortcuts. The Refine Plan prompt says to keep a Cut Path smooth and to ease its banks without making them climbable.
- **Reopen:** a Cut Path is touched, and so not carried forward verbatim, if it was edited or overlaps the edited shape.

## Acceptance criteria

- [ ] A Blockout round-trips `cut` and `width`; validation refuses a Cut Path under 4 m wide, and a Refine Plan that doesn't refine each Cut Path exactly once
- [ ] On the Blockout, height along a Cut Path rises evenly from start to end, and its banks are sheer (tested)
- [ ] A non-cut Path never changes the ground (tested)
- [ ] The Refine Plan's values for a Cut Path win along its strip, and its falloff eases the banks (tested)
- [ ] The Terrain and the `.glb` carry the strip
- [ ] Both pages show Cut Paths
- [ ] Reopen carry-forward treats Cut Paths like Zones (tested)
- [ ] The long-climb sample is redrafted with the live Agent and passes its Shortcut Check at both Checkpoints, and in the walk view the summit can't be climbed straight up

## Blocked by

- `12-shortcut-check.md`
