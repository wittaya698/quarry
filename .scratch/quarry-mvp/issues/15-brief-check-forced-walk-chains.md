# 15 — Brief Check: a forced walk that other Walk Targets undercut

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0005

## What to build

The Brief Check should refuse a Brief whose Walk Targets contradict a no-Shortcut Walk Target, before anything is drafted.

Found in review (issue 13): long-climb forced camp→summit to 10:00 ±5%, but also asked for camp→spring in 0:20 and spring→summit in 5:00. If those two Paths met their targets, camp→spring→summit would take about 5:20 and be a Shortcut. The AI noticed this, missed spring→summit on purpose and said why in its Reason. A Brief Check should catch it instead, and tell the user which targets conflict.

- **The rule:** for each no-Shortcut Walk Target A→C, find the fastest chain of other Walk Targets from A to C, followed in their own direction, A→B, then B→…, then →C. Each step counts at its upper bound: time × (1 + tolerance), or distance × (1 + tolerance) ÷ Walk Speed. If the chain's total is below A→C's floor, time × (1 − tolerance), the Brief is impossible.
- **The message** names the forced walk and the chain, with both times, e.g. "walk camp→summit is marked no Shortcut, but camp→spring→summit may take only 5:30, under its 9:30 floor".
- **Open question for the implementer:** the Path slope Check judges a step by its own climb, while the Shortcut Check judges the ground's slope (decided in issue 12). So a Path can pass its slope Check and still not count as a walkable route, for example where it traverses a steep side slope. That makes the chain argument slightly short of a proof. Either align the Path slope Check with the ground-slope rule, or word the Brief Check result as a refusal that can be overridden. Raise this with the human before choosing.
- **Decided (2026-10-09):** a hard refusal. The only Brief it wrongly refuses is one whose chain Paths cross ground the walk view already won't let a player walk, and fixing a Brief only means editing numbers. Aligning the Path slope Check is `16-path-slope-ground.md`.

## Acceptance criteria

- [x] The original long-climb targets (spring→summit 5:00) are refused by the Brief Check, with a message naming camp→spring→summit
- [x] The corrected long-climb Brief (spring→summit 10:00) passes
- [x] A chain that only runs the wrong way, such as summit→spring, never refuses a forced walk
- [x] Unmarked Walk Targets are never refused this way

## Blocked by

- None
