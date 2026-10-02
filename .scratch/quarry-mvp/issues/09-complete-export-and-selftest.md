# 09 — Complete Export + corruption self-test

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

- **Complete Export:** besides the Terrain mesh and collision, the `.glb` carries a named empty anchor per Landmark at its exact position, a curve per Path, and vegetation as density data. An optional thin `.tscn` instances it for Godot 4. Export is refused for unapproved or Superseded Terrain, and the round-trip re-import asserts every part is present.
- **Self-test:** a `selftest` CLI command, modeled on Contour's, builds a known-good Site using the fake Agent and then applies deliberate corruptions, asserting that the relevant Check or Ledger rule catches each one. The corruptions are: a Path steepened past the Max Walkable Slope, a Landmark moved off its Pad, Pad flatness broken, Terrain changed without a Revision, an Approval attempted by the Agent, a Waiver from Checkpoint #1 reused at Checkpoint #2, and an Export of Superseded Terrain.

## Acceptance criteria

- [ ] The `.glb` contains anchors named per Landmark at their exact positions, Path curves, and vegetation density
- [ ] The optional `.tscn` instances the `.glb`
- [ ] The round-trip asserts collision, anchors and curves; Export is refused for unapproved or Superseded Terrain
- [ ] `selftest` passes on a clean install and reports each corruption as caught
- [ ] Removing any one guard makes `selftest` fail, which proves each guard can fail

## Blocked by

- `02-tracer-refine-terrain-glb.md`
- `03-all-blockout-checks.md`
- `08-going-back.md`
