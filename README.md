# Quarry

A terrain-authoring tool for game developers. An AI agent drafts the terrain, and a human approves every draft at a **Checkpoint** before it counts.

You write a **Brief**: a footprint, the places you care about, how long it should take to walk between them, and a mood. The AI drafts a coarse **Blockout** with a **Reason** for each choice. Quarry then measures that Blockout against your targets rather than taking the AI's word for it. Nothing moves on until you approve one exact **Revision**.

> **Status: early.** The skeleton runs end to end from the CLI: Brief → Brief Check → Blockout (Zones, Pads, Readings) → all Blockout Checks → Checkpoint #1 → Refine Plan → Checkpoint #2 → Terrain → `.glb` with Godot collision. Both Checkpoints have a browser page: a top-down Blockout editor at #1, and a first-person walk over the Terrain at #2, where every Check runs again on the real ground. The Export holds only the terrain mesh and its collision so far. Drafts come from Claude by default, or from an offline fake with `--agent fake`. See [the roadmap](#roadmap).

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

Save the Brief below as `brief.json`, then run:

```sh
uv sync
export ANTHROPIC_API_KEY=...     # or skip it and pass --agent fake to draft and refine
uv run quarry new island --brief brief.json
uv run quarry draft island
```

```
drafted Revision 1
  pass    walk spawn→lighthouse  2:45 / 3:00 ±10%
  MISS    walk spawn→village  231 m / 80 m ±10%
  pass    slope spawn→lighthouse  0.0° ≤ 30.0°
  pass    slope spawn→village  0.0° ≤ 30.0°
  pass    pad spawn  0.0° ≤ 3.0°
  pass    pad lighthouse  0.0° ≤ 3.0°
  pass    pad village  0.0° ≤ 3.0°
  pass    reading gentle hills  13.5° ≤ 15.0°
  —       reading cozy exploration  not measurable: a feel to judge by eye
```

A Brief that's provably impossible, for example a Walk Target naming an undefined Waypoint or one too long to fit in the footprint, fails the **Brief Check**. `status` lists the problems, and `draft` is refused until the Brief is fixed.

Review the Blockout in the browser:

```sh
uv run quarry open island
```

The page shows the Blockout top-down, with Zones (Combine Mode and Stacking Order), Landmarks and their Pads (★ marks one the AI chose), Paths, Readings and every Reason, plus live Check results.
- Drag a Landmark or Zone to move it, or a Zone's rim to resize it.
- Set a Zone's height, Combine Mode or Stacking Order, or a Reading's limit, in the side panel.
- Each edit is a new Revision. The Checks re-measure straight away, with no Agent call, and the edited element's Reason becomes yours.
- Approve the Revision named on the button (with a Waiver for each missed Check), or reject it with a note.

Once the Blockout is approved and a Refine Plan is drafted (`quarry refine island`), `quarry open island` shows Checkpoint #2 instead:
- Walk the Terrain in first person at the Brief's Walk Speed. Click the view, then use W A S D and the mouse. Anything steeper than the Max Walkable Slope blocks you, and O toggles an overview.
- Every Check is shown again, measured on the Terrain.
- Each surface's Refine Plan values and Reasons are listed next to the view. Editing one makes a new Revision and rebuilds the Terrain in well under a second.
- Approve, with fresh Waivers for the Terrain's misses, or reject with a note.

The walk preview loads three.js from cdn.jsdelivr.net, so it needs internet access.

Or do it all from the terminal, waiving the miss at each Checkpoint:

```sh
uv run quarry approve island 1 --waive "walk spawn→village=the village can be farther"
uv run quarry refine island
uv run quarry approve island 1 --waive "walk spawn→village=still farther on the Terrain"
uv run quarry export island island.glb
```

```
exported island.glb from Blockout Revision 1 and Refine Plan Revision 1; collision verified
```

### The Brief

```json
{
  "footprint": [400, 400],
  "mood": "gentle hills, cozy exploration",
  "waypoints": ["spawn", "lighthouse", "village"],
  "walk_targets": [
    { "from": "spawn", "to": "lighthouse", "time": 180, "tolerance": 0.1 },
    { "from": "spawn", "to": "village", "distance": 80, "tolerance": 0.1 }
  ]
}
```

| Field                | Meaning                                                    | Default |
| -------------------- | ---------------------------------------------------------- | ------- |
| `footprint`          | Site extent in metres, `[x, y]`                            | —       |
| `waypoints`          | Named places; the AI decides where each goes               | —       |
| `walk_targets`       | A `time` in seconds or a `distance` in metres between two Waypoints, with a fractional `tolerance` | `[]` |
| `mood`               | Plain-language description of the place                    | `""`    |
| `walk_speed`         | Player pace in m/s, used to turn a time into a distance    | `1.4`   |
| `max_walkable_slope` | Steepest incline a player should walk, in degrees          | `30`    |

## Commands

| Command                                          | What it does                                                 |
| ------------------------------------------------ | ------------------------------------------------------------ |
| `quarry new SITE --brief FILE`                   | Create a Site from a Brief                                   |
| `quarry new SITE --from OTHER_SITE`              | Create a variant Site from a copy of another Site's Brief, with its own history |
| `quarry draft SITE [--agent claude\|fake]`       | Ask the Agent for a new Blockout Revision, answering the latest Rejection note if there is one |
| `quarry refine SITE [--agent claude\|fake]`      | Ask the Agent for a new Refine Plan Revision (needs an approved Blockout) |
| `quarry open SITE [--port N] [--no-browser]`    | Serve the current Checkpoint's page on 127.0.0.1 and open it; Ctrl-C stops it |
| `quarry status SITE`                             | Both Checkpoints' state, Revisions and Check results, or Brief Check problems before the first Draft |
| `quarry show SITE N`                             | Revision N of the Draft at the current Checkpoint (Landmarks and Pads, Paths, Zones in Stacking Order, Readings), each choice with its Reason |
| `quarry approve SITE N [--waive "CHECK=WHY"]...` | Approve Revision N at the current Checkpoint; every missed Check needs a Waiver |
| `quarry reject SITE N --note TEXT`               | Reject Revision N at the current Checkpoint, saying what was wrong |
| `quarry revive SITE N`                           | Copy a rejected Revision forward as a new one                |
| `quarry export SITE OUT.glb`                     | Write the `.glb` (needs an approved Refine Plan), then re-import it to verify the collision |

The Agent is Claude (`claude-opus-5-5`, with the API key read from `ANTHROPIC_API_KEY`) unless you pass `--agent fake`, which drafts the same deterministic layout every time without a network call.

`approve`, `reject`, `revive` and `show` act on the Blockout at Checkpoint #1, and on the Refine Plan once the Blockout is approved.

A Site is a directory containing `brief.json` and `history.jsonl`. The history is append-only: entries are added, never edited or deleted.

## Checks

Checks measure a surface: the Blockout's coarse **Surface** at Checkpoint #1, then the built **Terrain** at Checkpoint #2, against the same targets and under the same names. A Path that passed on the Blockout but got steeper in refining misses at #2.

| Check            | Passes when                                                                   |
| ---------------- | ----------------------------------------------------------------------------- |
| `walk A→B`       | The distance along the ground (so a climb counts for more than its map length), or that distance ÷ Walk Speed, is within the target's tolerance |
| `slope A→B`      | The Path's steepest stretch is no steeper than `max_walkable_slope`           |
| `pad NAME`       | The Landmark's Pad is no steeper than 3° anywhere                             |
| `reading PHRASE` | A measurable Reading's limit holds across the footprint (max slope or max height) |

Unmeasurable Readings are listed without a pass or miss. Decorative Paths aren't measured. AI-chosen Landmarks are marked `[AI-chosen]` in `show`, and still stand on a checked Pad.

The Brief Check flags a Walk Target only when no route could meet it: one longer than a 4 m-wide route winding back and forth across the whole footprint at the Max Walkable Slope. A hard but possible target passes, and if the Draft then misses it, the Path's Reason says so. The Brief is never rewritten to fit.

## Rules the core enforces

- **Every Draft is validated before it is kept.** Whatever the Agent returns is checked first, and a bad Draft is refused whole, with nothing recorded. The checks: the output is well formed; every choice has the AI's own Reason; every Waypoint has exactly one Landmark; every Walk Target has exactly one Path; it doesn't restate the Brief's targets; it sets nothing the other stage owns ([ADR-0003](docs/adr/0003-each-property-owned-by-exactly-one-stage.md)); it attempts no human act. The Claude Agent is offered no tools, so it can only answer with a Draft.
- **Approval names one exact Revision.** Approving any Revision other than the current one is refused, and so is approving a rejected one.
- **Misses are never silent.** Approval is refused while any missed Check lacks a Waiver.
- **Human acts are human-only.** Only a human can approve, waive or reject. The Site refuses these acts from the Agent or from any automated caller, and no setting turns this off. When the CLI is run without a terminal (from a pipe, script or CI), it passes an automated identity, so the act is refused. See [ADR-0004](docs/adr/0004-checkpoint-acts-are-human-only-enforced-in-core.md).
- **Edits make Revisions.** A human edit (moving a Landmark, which brings its Paths' ends along; moving, resizing, re-heighting or recombining a Zone; restacking Zones; changing a Reading's limit) applies to the current Revision only and creates the next one, recording who made it. Whatever it touched gets a human Reason, and everything else keeps the AI's. Edits are human-only, and an approved Blockout can't be edited.
- **The page acts as you, or as no one.** `quarry open` fixes its caller at launch: you, when run from a terminal, otherwise an automated caller, so every act the page sends is refused. The page listens only on 127.0.0.1, and every request must carry the random token in the URL it printed.
- **Rejections need a note** and keep the Revision. A rejected Revision stays viewable and can be revived.
- **Nothing is built on an unapproved Blockout.** A Refine Plan is refused until the Blockout is approved, and the Refine Plan passes its own Checkpoint under the same rules.
- **One definition of height.** Zones combine in Stacking Order by their Combine Mode (`add`, `max` or `replace`). Each point takes its surface values, such as roughness and vegetation, from its topmost Zone alone, never from a blend. Checks and the Terrain Builder share this one definition.
- **Each Checkpoint gets its own Waivers.** Approving the Refine Plan needs a Waiver for every Check that misses on the Terrain, even one that was waived at Checkpoint #1.
- **Pads are flattened.** The Terrain Builder holds every Pad level at its centre's height and eases it back into the ground beyond. The Pad Check then measures it on the Terrain.
- **The Refine Plan shapes edges, and nothing else of the Blockout's.** Each Zone's edge eases in over its `falloff_width`, centred on the rim so the Zone keeps its size, following its `slope_profile` (`linear`, `smooth` or `steep`). Refine Plan edits can change only slope profile, falloff width, roughness, seed and vegetation density, and each edit makes a new Revision.
- **Terrain is built by code, not the AI.** The same Blockout and Refine Plan always give byte-identical Terrain, whose only randomness is the Refine Plan's seed. Terrain names the Blockout Revision and Refine Plan Revision it came from. See [ADR-0001](docs/adr/0001-approved-blockout-is-the-contract.md).
- **Export is verified, not trusted.** Export is refused until the Refine Plan is approved. The `.glb` names its collision mesh `terrain-colonly`, so Godot 4 builds a collision body on import. Each Export is re-imported, and its collision is re-measured against the Terrain before the file is kept. See [ADR-0002](docs/adr/0002-standalone-core-browser-checkpoints-glb-export.md).

## Development

```sh
uv run pytest
```

Tests use only the public interfaces, and they never call a live LLM.

```
quarry/
  site.py       Site: Brief + append-only history; Checkpoint rules for both Drafts
  edits.py      Human edits: one change to a Blockout or Refine Plan → the next Revision
  page.py       Checkpoint server (127.0.0.1, token-guarded) for whichever Checkpoint a Site is at
  checkpoint1.html  The Checkpoint #1 page: top-down SVG editor, plain JavaScript
  checkpoint2.html  The Checkpoint #2 page: first-person Terrain walk (three.js) and Refine Plan editor
  checks.py     Checks: walk, slope, Pad and Reading Checks, measured on any surface
  surface.py    Surface: Ground + Zones (+ Refine Plan edges) → height and topmost Zone at any point
  agent.py      Agent port and the deterministic FakeAgent
  claude_agent.py  The Agent's Claude adapter: prompts and output schemas
  validation.py The validation layer every Agent output passes before it is kept
  brief.py      Brief and Walk Targets, loaded from JSON; the Brief Check
  blockout.py   Blockout: Landmarks with Pads, Paths, Zones and Readings, each with a Reason
  refine.py     Refine Plan: how each surface looks up close, with a Reason
  terrain.py    Terrain Builder: Surface + Refine Plan → height and vegetation grids
  export.py     .glb writer with Godot collision naming, and its re-import
  identity.py   Human, Automated, and the Agent's identity
  cli.py        Thin CLI wiring over the core
tests/
```

## Design docs

- [CONTEXT.md](CONTEXT.md): the domain glossary. Code and docs use these terms, and avoid the alternatives it lists.
- [docs/adr/](docs/adr/): architecture decisions:
  - [0001](docs/adr/0001-approved-blockout-is-the-contract.md): the approved Blockout is the contract, and the AI never authors geometry
  - [0002](docs/adr/0002-standalone-core-browser-checkpoints-glb-export.md): a standalone core, browser Checkpoints, and `.glb` export with Godot 4 as the first target
  - [0003](docs/adr/0003-each-property-owned-by-exactly-one-stage.md): each property is owned by exactly one stage
  - [0004](docs/adr/0004-checkpoint-acts-are-human-only-enforced-in-core.md): Checkpoint acts are human-only, enforced in the core
- [.scratch/quarry-mvp/PRD.md](.scratch/quarry-mvp/PRD.md): the MVP product requirements

## Roadmap

The MVP is planned as ten vertical slices in [.scratch/quarry-mvp/issues/](.scratch/quarry-mvp/issues/):

1. ✅ Tracer: Brief → Blockout → Checks → Approve/Reject via CLI
2. ✅ Tracer: Refine Plan → Terrain → `.glb`
3. ✅ All Blockout Checks: overlapping Zones, slope-aware walking, Brief Check, Readings, Pads
4. ✅ Checkpoint #1 page: a top-down Blockout view in the browser, with edits and human acts
5. ✅ Checkpoint #2: Checks on Terrain, Waivers per Checkpoint, and a walkable preview
6. ✅ Live Agent: a Claude-backed adapter with a validation layer
7. Draft quality review (human)
8. Going back: Reopen, carry-forward and Edit Requests
9. Complete Export and the corruption self-test
10. Verify in Godot 4 (human)
