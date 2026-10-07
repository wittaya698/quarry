# 12 — Shortcut Check: catch a faster way round a forced walk

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md` · ADR-0005

## What to build

A Brief can mark a Walk Target **no Shortcut**. For every such Walk Target, a new Check looks anywhere on the ground for the fastest walkable route from its first Waypoint to its second, and misses when that route is faster than the Walk Target allows.

- **Walkable:** never climbing steeper than the Max Walkable Slope, but dropping down any slope, as a player can in the game. This makes the route one-way.
- **Timing:** measured along the ground, slope included, at the Brief's Walk Speed, the same way a Path is measured. A distance Walk Target is compared in metres.
- **Both Checkpoints:** like every Check, it runs on the Blockout and again on the Terrain.
- **Shown:** a miss carries the Shortcut's route. Checkpoint #1 draws it on the map as a red dashed line, Checkpoint #2 draws it on the Terrain, and clicking the Check highlights it.
- **Fed back:** the next Draft's input includes the latest Revision's Shortcut misses, with their times and routes, so the AI sees where its last layout leaked.
- **Unmarked Walk Targets** are never checked for Shortcuts; the player may walk anywhere.

## Acceptance criteria

- [ ] The Brief reads and writes `"no_shortcut": true` on a Walk Target, defaulting to false
- [ ] A `shortcut A→B` Check runs for each no-Shortcut Walk Target and for no other, on the Blockout and on the Terrain
- [ ] It misses when a walkable route is faster than the Walk Target's lower tolerance, and passes when none is (tested on a hill walkable straight up, and on one that isn't)
- [ ] Steep drops are walkable and steep climbs are not (tested both ways on the same cliff)
- [ ] A miss carries the route; both Checkpoint pages draw it, and nothing is drawn on a pass
- [ ] Shortcut misses reach the next Draft's input for both Claude adapters
- [ ] A Shortcut miss blocks Approval without a Waiver, like any Check
- [ ] `examples/briefs/long-climb.json` marks camp→summit no Shortcut, and the approved Round 3 long-climb Blockout now misses it with a route up the hill

## Blocked by

- None (07's Round 3 samples exist)
