# 16 — Path slope Check judges the ground's slope too

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0005

## What to build

The Path slope Check judges each step only by its own climb along the Path. The Shortcut Check, and the walk view at Checkpoint #2, also refuse a climbing step where the ground's steepest slope is over the Max Walkable Slope (decided in issue 12). So a Path can pass its slope Check while it climbs across a face too steep to walk, and the walk view stops the player there.

Make the Path slope Check use the same rule as the Shortcut Check, so a Path that passes is one the player can walk. This also makes the Brief Check's chain refusal (issue 15) a proof rather than nearly one.

## Decided (2026-10-09)

- **Both ways.** A Path is walked back, too, so any ground on it steeper than the Max Walkable Slope misses, whichever way the Path climbs. On every review Site this gives the same results as one-way.
- **The steeper of two measures.** The Check reports the larger of the Path's own climb and the ground's steepest slope along it. The ground's slope is read over 2 m, which softens a sheer step, so it adds to the old measure rather than replacing it, and nothing that missed before can pass now.
- **Review Sites:** only Round 2 long-climb (never approved) changes result. See `review/review.md`.

## Acceptance criteria

- [x] A Path that climbs gently across a slope steeper than the Max Walkable Slope misses its slope Check (tested)
- [x] A Cut Path's strip still passes (its ground is level across the strip)
- [x] The review Sites' results before and after are logged

## Blocked by

- None
