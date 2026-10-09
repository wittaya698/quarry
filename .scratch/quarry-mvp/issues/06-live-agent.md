# 06 — Live Agent: Blockout and Refine Plan drafting with validation

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

Replace the fake with a real Claude-backed adapter behind the Agent port. The fake stays available for tests.
- **Blockout drafting:** the adapter drafts a Blockout from a Brief, folding in the latest Rejection note when there is one. It produces Zones, Landmarks, Pads, Paths and Readings, all with Reasons, and owns any target it misses rather than rewriting it.
- **Refine Plan drafting:** it drafts per-Zone values with Reasons, including how they affect each Path (for example "kept roughness low along the Path so the walk stays at 3:05").
- **Validation:** every Agent output passes a validation layer before it reaches the Ledger. Malformed output, missing Reasons, a Waypoint without exactly one Landmark, a Walk Target without exactly one Path, rewritten Brief targets, and writes to a property owned by the other stage (ADR-0003) are all rejected.
- **No human acts:** the Agent has no access to Approval, Waiver, Rejection or Reopen.

## Acceptance criteria

- [x] The Claude adapter drafts Blockouts and Refine Plans; it uses the latest Claude model, with the API key read from the environment
- [x] A Rejection note is included in the next Blockout Draft's input
- [x] The validation layer rejects each invalid case listed above (tested with the fake returning bad output)
- [x] The Agent cannot perform Approval, Waiver, Rejection or Reopen (tested)
- [x] No test makes a live LLM call
- [x] The CLI and pages work unchanged with either adapter

## Blocked by

- `03-all-blockout-checks.md`
- `05-checkpoint-2.md`
