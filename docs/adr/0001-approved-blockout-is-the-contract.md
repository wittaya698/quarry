# The approved Blockout is the contract; Terrain is a pure function of it (plus a Refine Plan)

Quarry borrows Contour's model without sharing its code: an approved Blockout is the single source of truth, and Terrain is regenerated deterministically from it rather than generated directly by the AI. We chose this over letting the agent produce terrain from the brief (or re-interpret the Blockout at refine time) because it is the only way the Checkpoints mean anything — the reviewed artifact is exactly what gets built, every Terrain is traceable to one Approval, and a cheap edit to the Blockout rebuilds Terrain without a fresh AI pass.

## Consequences

- The AI authors Blockouts and Refine Plans (per-zone values with reasons); it never authors Terrain geometry. Code builds Terrain deterministically from Blockout + Refine Plan, so a Checkpoint #2 edit like "less steep" changes one value and rebuilds with no new AI pass.
- Quarry keeps its own vocabulary (Blockout, Terrain, Checkpoint) rather than Contour's (spec, revision, mark), because terrain is a walked space, not an asset.
