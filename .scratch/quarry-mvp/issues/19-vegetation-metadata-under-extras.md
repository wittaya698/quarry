# 19 — Vegetation metadata sits under `extras` in Godot

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md` (user story 71) · found in issue 10

## What to build

Godot 4.7 keeps the terrain node's glTF extras as one metadata entry named `extras`. So the density is at `get_meta("extras")["vegetation_density"]`, not at `get_meta("vegetation_density")` as the README says. JSON also turns `rows` and `columns` into floats (61.0, 101.0).

Correct the README, with a GDScript snippet that reads a density at (x, y). Decide whether the numbers should stay floats.

## Acceptance criteria

- [x] The README shows how Godot code reads the density, checked in Godot
- [x] The round-trip test reads the density the same way Godot does (from `extras`)

## Blocked by

- None

## Decided (2026-10-09)

- **The numbers stay as they are.** Godot's glTF importer reads every JSON number as a float, whatever the file writes, so nothing Quarry writes can make `rows` an int. The README snippet casts with `int()`.
- **Checked in Godot 4.7.2, headless:** the README's `vegetation_density()` was run on a fresh Export of the fake Agent's Site. At six points, including the footprint's far corner and one on the rise (0.6 against 0.3 around it), it returned what Quarry's Terrain holds.
- `read_glb` now returns metadata as Godot imports it: a node's extras under one `extras` entry.
