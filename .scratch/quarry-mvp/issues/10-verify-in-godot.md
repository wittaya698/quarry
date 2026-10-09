# 10 — Verify in Godot 4 (HITL)

Status: ready-for-human

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

A human imports an exported Site into Godot 4 and confirms it works as a game space. Check that the collision Godot builds from the `-colonly` naming works when walked with a CharacterBody3D, that the Landmark anchors sit where the Checkpoint #2 preview showed them, and that the Path curves are usable. Note anything Godot imports differently from what the round-trip test assumed.

## Acceptance criteria

- [x] The `.glb`, or the `.tscn` wrapper, imports into Godot 4 with no manual setup
- [x] A character can walk the Terrain without falling through, and walk times feel consistent with the measured Checks (measured headless, and walked first-person by the user: all good)
- [x] Landmark anchors and Path curves are present and positioned correctly (curves are lines, not Path3D: issue 18)
- [ ] Any mismatch is filed as a new issue, and the round-trip test is updated to catch it (filed as 17, 18 and 19; the round-trip updates are part of each; 17 is fixed)

## Blocked by

- `09-complete-export-and-selftest.md`

## Results (2026-10-09, Godot 4.7.2, headless)

I ran it with Godot from Steam, on two Sites:
- `meadow`: the fake Agent's Site from the self-test.
- `long-climb`: a scratch copy of the review Site (a live-model Blockout), approved as Human("tester") with a Waiver for its Blockout slope miss. The real review Site is untouched.

Each was exported with `--tscn` and imported into an empty project. The scripts are in `review/godot/`:
- `inspect.gd` dumps the scene.
- `walk.gd` walks a capsule CharacterBody3D along each Path's imported curve, under gravity and on Godot's own collision, at 1.4 m/s along the ground.

- **Import:** no errors and no warnings, from either the `.glb` or the `.tscn`.
- **Collision:** a StaticBody3D with a ConcavePolygonShape3D (12,000 and 20,000 faces).
- **Walks:** none fell through and none got stuck. Feet stayed within 6 cm of the ground.

  | Path | Godot | Check |
  |---|---|---|
  | meadow spawn→cave | 57.9 s | 57.6 s (80.6 m) |
  | long-climb camp→summit | 601.9 s | 600.6 s |
  | long-climb camp→spring | 19.9 s | 19.9 s |
  | long-climb spring→summit | 299.8 s | 298.1 s |

- **Anchors:** Node3D at the exact positions and heights, e.g. summit at (100, 20, 100).
- **Mismatches, each filed:**
  - **17:** the collision body gets a random name, because its stripped name clashes with the `terrain` mesh.
  - **18:** Paths arrive as line-strip meshes, not Path3D/Curve3D.
  - **19:** the vegetation density sits under the `extras` metadata entry, and its rows/columns arrive as floats.

## First-person walk (2026-10-09)

The user walked the Sites first-person in `review/godot/project` (see `walk_here.gd`). It felt right: no falls through the ground, the Landmarks stood on flat Pads, the slopes were walkable and the climb felt long.
