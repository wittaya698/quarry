# 18 — Paths arrive in Godot as lines, not curves

Status: needs-triage

## Parent

`.scratch/quarry-mvp/PRD.md` (user story 70) · found in issue 10

## What to build

Each Path imports as a MeshInstance3D drawing a line strip. The points are all there, laid along the ground, but it is not a Path3D with a Curve3D. So a game can't use it with PathFollow3D or as a road spline without first writing a script to convert it. The lines are also visible in the game, as thin unlit lines.

glTF has no curve type, so the `.glb` alone can't fix this. Options:

1. The `.tscn` adds a Path3D per Path, with its Curve3D written in from the same points, and the `.glb`'s line meshes are hidden.
2. Ship a small Godot import script that turns `paths/*` into Path3D nodes.
3. Keep lines, and document how to read them.

## Acceptance criteria

- [ ] A decision between the options above
- [ ] In Godot 4, each Path can drive a PathFollow3D with no hand conversion, or the docs say exactly how to get one
- [ ] The round-trip test checks whatever form the curve takes

## Blocked by

- None
