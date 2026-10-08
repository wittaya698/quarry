# 07 — Draft quality review (HITL)

Status: ready-for-human

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

A human judges whether the live Agent's Drafts are actually good. Run it on 3–5 contrasting sample Briefs (for example "gentle cozy forest", "steep coastal cliffs", a tight 100 m footprint, a Brief whose targets are hard to meet). At Checkpoint #1 and Checkpoint #2, judge whether the Readings are sensible interpretations of the mood, whether placements honor the Walk Targets, whether the Reasons are truthful and specific, and whether misses are owned honestly. Tune the prompts until the Drafts are acceptable.

## Acceptance criteria

- [x] Sample Briefs are committed as fixtures (`examples/briefs/`)
- [x] For each sample, the reviewer records which Readings, placements and Reasons they would accept or reject, and why
- [x] The prompts are revised and the samples re-run until the reviewer accepts the Drafts as a reasonable starting point
- [x] Any new domain term that comes up is added to `CONTEXT.md`

## Blocked by

- `04-checkpoint-1-page.md`
- `06-live-agent.md`
- `11-subscription-agent.md` (tune on the subscription, not per-token billing)
- `12-shortcut-check.md`, `13-cut-paths.md` (long-climb: the summit must not be climbable straight up)
- `14-pad-blend.md` (tight-courtyard's Terrain misses "flat" because of the Pad blend)
