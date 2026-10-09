# 19 — Vegetation metadata sits under `extras` in Godot

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md` (user story 71) · found in issue 10

## What to build

Godot 4.7 keeps the terrain node's glTF extras as one metadata entry named `extras`. So the density is at `get_meta("extras")["vegetation_density"]`, not at `get_meta("vegetation_density")` as the README says. JSON also turns `rows` and `columns` into floats (61.0, 101.0).

Correct the README, with a GDScript snippet that reads a density at (x, y). Decide whether the numbers should stay floats.

## Acceptance criteria

- [ ] The README shows how Godot code reads the density, checked in Godot
- [ ] The round-trip test reads the density the same way Godot does (from `extras`)

## Blocked by

- None
