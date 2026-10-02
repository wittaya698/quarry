# 10 — Verify in Godot 4 (HITL)

Status: ready-for-human

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

A human imports an exported Site into Godot 4 and confirms it works as a game space. Check that the collision Godot builds from the `-colonly` naming works when walked with a CharacterBody3D, that the Landmark anchors sit where the Checkpoint #2 preview showed them, and that the Path curves are usable. Note anything Godot imports differently from what the round-trip test assumed.

## Acceptance criteria

- [ ] The `.glb`, or the `.tscn` wrapper, imports into Godot 4 with no manual setup
- [ ] A character can walk the Terrain without falling through, and walk times feel consistent with the measured Checks
- [ ] Landmark anchors and Path curves are present and positioned correctly
- [ ] Any mismatch is filed as a new issue, and the round-trip test is updated to catch it

## Blocked by

- `09-complete-export-and-selftest.md`
