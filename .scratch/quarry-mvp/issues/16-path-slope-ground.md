# 16 — Path slope Check judges the ground's slope too

Status: needs-triage

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0005

## What to build

The Path slope Check judges each step only by its own climb along the Path. The Shortcut Check, and the walk view at Checkpoint #2, also refuse a climbing step where the ground's steepest slope is over the Max Walkable Slope (decided in issue 12). So a Path can pass its slope Check while it climbs across a face too steep to walk, and the walk view stops the player there.

Make the Path slope Check use the same rule as the Shortcut Check, so a Path that passes is one the player can walk. This also makes the Brief Check's chain refusal (issue 15) a proof rather than nearly one.

## Open questions

- Should the Path slope Check stay symmetric (drops count too) or become one-way like a Shortcut? A Path is walked both ways; a Walk Target only one.
- How many approved review Sites change result? Measure before and after, as in issue 14.

## Acceptance criteria

- [ ] A Path that climbs gently across a slope steeper than the Max Walkable Slope misses its slope Check (tested)
- [ ] A Cut Path's strip still passes (its ground is level across the strip)
- [ ] The review Sites' results before and after are logged

## Blocked by

- None
