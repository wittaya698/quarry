# 05 — Checkpoint #2: Checks on Terrain, Waivers per Checkpoint, walkable preview

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

Make Checkpoint #2 real. Every Check runs again on the built **Terrain** against the same targets: walk times, Max Walkable Slope, Pad flatness and measurable Readings. A Waiver given at Checkpoint #1 never covers a miss at Checkpoint #2.

A local browser page lets the developer walk the Terrain in first person at the Brief's Walk Speed (three.js). It shows the Refine Plan alongside the Terrain, with the Check results. The developer edits Refine Plan values directly, which creates a new Revision and rebuilds the Terrain within seconds with no Agent call, then Approves (with Waivers) or Rejects with a note. The Terrain Builder flattens Pads.

## Acceptance criteria

- [x] All Checks run on Terrain; a Walk Target that passed on the Blockout but is steeper on the Terrain shows as missed
- [x] Checkpoint #1 Waivers do not satisfy Checkpoint #2 misses; Approval requires fresh Waivers
- [x] Pads are near-flat on the built Terrain, and the Pad Check verifies it
- [x] The page offers a first-person walk at Walk Speed, with collision against the Terrain
- [x] The Refine Plan values and their Reasons are shown next to the Terrain; editing one creates a new Revision and rebuilds the Terrain within seconds
- [x] Approve and Reject from the page follow the Ledger rules and record identity
- [x] Tests cover Checks on Terrain and the Waiver-per-Checkpoint rule

## Blocked by

- `02-tracer-refine-terrain-glb.md`
- `03-all-blockout-checks.md`
- `04-checkpoint-1-page.md`
