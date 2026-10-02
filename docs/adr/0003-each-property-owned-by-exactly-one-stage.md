# Every terrain property is owned by exactly one stage

The Blockout owns *where and how big* — Zone shapes, heights, Combine Modes, Stacking Order, Landmarks, Paths and Readings. The Refine Plan owns *how it looks up close* — slope profile, falloff width, roughness, seed and vegetation. No property belongs to both. We chose a hard split over letting refinement nudge Blockout properties (e.g. lowering a hill to satisfy "less steep") because any shared property would let Checkpoint #2 quietly change what Checkpoint #1 approved, making the first Checkpoint cosmetic and breaking ADR-0001's traceability.

## Consequences

- An Edit Request at Checkpoint #2 that needs a Blockout-owned change is never applied there: the AI says which property and offers a Reopen, which supersedes the Terrain.
- Some requests that feel small ("a bit less steep") cost a full return to Checkpoint #1. That is deliberate.
