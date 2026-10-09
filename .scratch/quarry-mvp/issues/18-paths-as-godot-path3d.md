# 18 — Paths arrive in Godot as lines, not curves

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md` (user story 70) · found in issue 10

## What to build

Each Path imports as a MeshInstance3D drawing a line strip. The points are all there, laid along the ground, but it is not a Path3D with a Curve3D. So a game can't use it with PathFollow3D or as a road spline without first writing a script to convert it. The lines are also visible in the game, as thin unlit lines.

glTF has no curve type, so the `.glb` alone can't fix this. Options:

1. The `.tscn` adds a Path3D per Path, with its Curve3D written in from the same points, and the `.glb`'s line meshes are hidden.
2. Ship a small Godot import script that turns `paths/*` into Path3D nodes.
3. Keep lines, and document how to read them.

## Acceptance criteria

- [x] A decision between the options above
- [x] In Godot 4, each Path can drive a PathFollow3D with no hand conversion, or the docs say exactly how to get one
- [x] The round-trip test checks whatever form the curve takes

## Blocked by

- None

## Decided (2026-10-09)

- **Option 1.** The `--tscn` scene adds a `paths` Node3D with a Path3D per Path, named `start→end`. Its Curve3D holds the same points as the `.glb`'s line, with no handles. The scene hides the `.glb`'s own `paths` node (`terrain/paths`) through an editable-instance override. The `.glb` itself is unchanged.
- `write_tscn` takes the points from the written `.glb`, which the Export has already verified, so the scene can't drift from it.
- **Round-trip:** `read_tscn` reads the scene back without the writer's help. The tests check each Path3D's curve against its Path and the Terrain, the same way the `.glb`'s curves are checked, and check that the lines are hidden.
- **Checked in Godot 4.7.2, headless,** on the self-test's Site:
  - The scene imports with no errors.
  - `terrain/paths` is hidden.
  - spawn→cave is a Path3D 80.62 m long, matching the walk Check.
  - A PathFollow3D at `progress_ratio = 0.5` sits at (100.0, 3.14, 60.0), on the ground at the rise.
