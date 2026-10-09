# 17 — Godot names the collision body at random

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0002 · found in issue 10

## What to build

Godot strips `-colonly` from `terrain-colonly`, leaving `terrain`, which is already the display mesh's name. So it names the StaticBody3D `@StaticBody3D@19798`, and the name changes on every import. A game script cannot find the collision body by name.

Name the collision so that, once Godot strips the suffix, it does not clash with any other node in the `.glb`.

## Acceptance criteria

- [ ] In Godot 4, the collision imports as a StaticBody3D with a stable, documented name
- [ ] The round-trip test fails when two nodes would share a name once Godot strips its import suffixes (`-col`, `-colonly`, `-noimp` and the rest)
- [ ] Landmark names are covered too: a Landmark named, say, `cave-col` must not be turned into collision

## Blocked by

- None
