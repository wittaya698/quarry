# 04 — Checkpoint #1 page: view, edits and acts

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

A local browser page for Checkpoint #1, opened from the CLI. It shows the current Blockout top-down within a few seconds: Zones (with Combine Mode and Stacking Order), Landmarks (with AI-chosen ones marked), Pads, Paths, Readings, a Reason on every element, and live Check results with target and measured value.

The developer edits directly by dragging a Landmark, moving or resizing a Zone, or changing a Zone's height, Combine Mode, Stacking Order or a Reading. Each edit creates a new Revision in the Ledger with no Agent call, Checks re-measure immediately, and the edited element's Reason becomes "by you". From the page the developer Approves the current Revision (giving a Waiver for each missed Check) or Rejects it with a note. Every act carries the user's identity.

## Acceptance criteria

- [ ] The CLI opens the page for a Site; the Blockout renders within a few seconds
- [ ] Every element shows its Reason; every Check shows target, measured value and pass/miss
- [ ] Each edit creates a new Revision and re-runs the Checks without any Agent call
- [ ] An edited element's Reason is replaced with a human-authored one
- [ ] The Approve control names the Revision on screen and requires a Waiver per missed Check; Reject requires a note
- [ ] Acts from the page are recorded with identity, and the core's refusal rules still apply
- [ ] The page works with Blockouts from the fake Agent

## Blocked by

- `01-tracer-brief-to-approved-blockout.md`
- `03-all-blockout-checks.md`
