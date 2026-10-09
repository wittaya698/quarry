# 17 — Godot names the collision body at random

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0002 · found in issue 10

## What to build

Godot strips `-colonly` from `terrain-colonly`, leaving `terrain`, which is already the display mesh's name. So it names the StaticBody3D `@StaticBody3D@19798`, and the name changes on every import. A game script cannot find the collision body by name.

Name the collision so that, once Godot strips the suffix, it does not clash with any other node in the `.glb`.

## Acceptance criteria

- [x] In Godot 4, the collision imports as a StaticBody3D with a stable, documented name
- [x] The round-trip test fails when two nodes would share a name once Godot strips its import suffixes (`-col`, `-colonly`, `-noimp` and the rest)
- [x] Landmark names are covered too: a Landmark named, say, `cave-col` must not be turned into collision

## Blocked by

- None

## Decided (2026-10-09)

- The collision is `terrain_collision-colonly`; Godot 4.7 imports it as a StaticBody3D named `terrain_collision`, the same on every clean import.
- Godot 4.7, checked by import: a hint counts after `-`, `_` or `$`. On meshes, `-col` made a curve into collision and `_noimp` dropped one; on empty anchors, `-noimp`, `-vehicle` and `-wheel` were acted on. Quarry treats every hint as acted on, wherever it is.
- The round-trip refuses any node but the collision ending in a hint, and any two siblings that would keep one name.
- The Brief Check refuses a Waypoint named with a hint, so it is caught before drafting, not at Export.
