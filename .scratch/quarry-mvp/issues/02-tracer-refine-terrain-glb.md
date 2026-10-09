# 02 — Tracer: Refine Plan → Terrain → `.glb`

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

The second half of the skeleton. Once a Blockout is approved, the fake Agent drafts a **Refine Plan** (per-Zone slope profile, falloff width, roughness, seed and vegetation density, each with a Reason). The Ledger refuses a Refine Plan on an unapproved Blockout. The **Terrain Builder** deterministically turns Blockout + Refine Plan into **Terrain** (a height grid) that records both source Revisions (ADR-0001). The developer approves the Refine Plan via the CLI, and **Export** writes a `.glb` with a terrain mesh and collision named by Godot 4's import convention (ADR-0002). The Export is re-imported and re-measured to prove the collision is present.

## Acceptance criteria

- [x] A Refine Plan can only be drafted on an approved Blockout; anything else is refused
- [x] The same Blockout + Refine Plan always builds byte-identical Terrain; all randomness comes from Refine Plan seeds
- [x] Terrain names the Blockout Revision and Refine Plan Revision it was built from
- [x] Refine Plan Approval and Rejection follow the same Ledger rules as Checkpoint #1
- [x] The CLI Export writes a `.glb` only when the Refine Plan is approved; otherwise it is refused
- [x] Collision meshes use Godot's `-colonly` naming; a round-trip re-import asserts they exist and match the Terrain's extent
- [x] Tests cover determinism, traceability, the Export refusal and the round-trip

## Blocked by

- `01-tracer-brief-to-approved-blockout.md`
