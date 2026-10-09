# Quarry

A terrain-authoring tool for game developers. An AI agent drafts the terrain, and a human approves every draft at a **Checkpoint** before it counts.

You write a **Brief**: a footprint, the places you care about, how long it should take to walk between them, and a mood. The AI drafts a coarse **Blockout** with a **Reason** for each choice. Quarry then measures that Blockout against your targets rather than taking the AI's word for it. Nothing moves on until you approve one exact **Revision**.

> **Status: early.** The skeleton runs end to end from the CLI: Brief → Brief Check → Blockout (Zones, Pads, Readings) → all Blockout Checks → Checkpoint #1 → Refine Plan → Checkpoint #2 → Terrain → `.glb` with Godot collision. Both Checkpoints have a browser page: a top-down Blockout editor at #1, and a first-person walk over the Terrain at #2, where every Check runs again on the real ground. The Export carries the terrain mesh, its collision, an anchor per Landmark, a curve per Path and vegetation density, with an optional Godot scene; `quarry selftest` proves every guard can fail. Drafts come from Claude on your subscription by default, through the Claude Code CLI; `--agent api` uses the Anthropic API instead, and `--agent fake` an offline fake. See [the roadmap](#roadmap).

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Drafting on your Claude subscription also needs [Claude Code](https://code.claude.com) 2.1.280 or newer, logged in once to Quarry's own profile:

```sh
CLAUDE_CONFIG_DIR=~/.quarry/claude-code claude    # then type /login, and exit
```

That profile keeps your own CLAUDE.md, memory, hooks and MCP servers out of every Draft. To try Quarry without Claude, pass `--agent fake` to `draft` and `refine`.

Save the Brief below as `brief.json`, then run:

```sh
uv sync
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

A Brief that's provably impossible, for example a Walk Target naming an undefined Waypoint or one too long to fit in the footprint, or a Waypoint whose name ends in a Godot import hint such as `-col` or `_noimp`, fails the **Brief Check**. `status` lists the problems, and `draft` is refused until the Brief is fixed.

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
uv run quarry export island island.glb --tscn
```

```
exported island.glb from Blockout Revision 1 and Refine Plan Revision 1; collision, anchors and curves verified
wrote island.tscn, which instances it
```

### In Godot

The `terrain` node carries the vegetation density. Godot keeps a node's glTF extras as one metadata entry, `extras`, and reads every number in it as a float. To read the density at a point:

```gdscript
# x and z in the terrain node's own space: Quarry's (x, y) is Godot's (x, z)
func vegetation_density(terrain: Node3D, x: float, z: float) -> float:
	var v: Dictionary = terrain.get_meta("extras")["vegetation_density"]
	var columns := int(v["columns"])
	var column := clampi(roundi(x / v["spacing"]), 0, columns - 1)
	var row := clampi(roundi(z / v["spacing"]), 0, int(v["rows"]) - 1)
	return v["density"][row * columns + column]
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
| `quarry draft SITE [--agent subscription\|api\|fake]` | Ask the Agent for a new Blockout Revision, answering the latest Rejection note if there is one |
| `quarry refine SITE [--agent subscription\|api\|fake]` | Ask the Agent for a new Refine Plan Revision (needs an approved Blockout) |
| `quarry open SITE [--port N] [--no-browser] [--agent …]` | Serve the current Checkpoint's page on 127.0.0.1 and open it; `--agent` answers its Edit Requests. Ctrl-C stops it |
| `quarry open SITE --refine-plan N`               | Walk a Superseded Refine Plan Revision's Terrain, read-only    |
| `quarry status SITE`                             | Both Checkpoints' state, Revisions and Check results, or Brief Check problems before the first Draft |
| `quarry show SITE N [--refine-plan]`             | Revision N of the Draft at the current Checkpoint (Landmarks and Pads, Paths, Zones in Stacking Order, Readings), each choice with its Reason; `--refine-plan` shows a Refine Plan Revision, Superseded ones included |
| `quarry request SITE "WORDS" [--agent …]`         | An Edit Request: the Agent answers with a new Revision at the current Checkpoint, or at Checkpoint #2 with "needs Reopen" naming the Blockout property it would take |
| `quarry reopen SITE`                             | Withdraw the Blockout's Approval to change it; its Refine Plans and Terrain become Superseded |
| `quarry brief SITE --brief FILE`                 | Change the Brief; after Approval this Reopens the Blockout     |
| `quarry approve SITE N [--waive "CHECK=WHY"]...` | Approve Revision N at the current Checkpoint; every missed Check needs a Waiver |
| `quarry reject SITE N --note TEXT`               | Reject Revision N at the current Checkpoint, saying what was wrong |
| `quarry revive SITE N`                           | Copy a rejected Revision forward as a new one                |
| `quarry export SITE OUT.glb [--tscn]`            | Write the `.glb` (needs an approved, non-Superseded Refine Plan), then re-import it to verify collision, anchors and curves; `--tscn` adds a Godot 4 scene that instances it |
| `quarry selftest`                                | Build a known-good Site with the fake Agent, export it, then corrupt it seven ways and report each one caught; exits 1 if any gets through |

The `--agent` choices:

| `--agent`              | Who drafts                                                                     | Paid by |
| ---------------------- | ------------------------------------------------------------------------------ | ------- |
| `subscription` (default) | Claude through the Claude Code CLI (`claude -p`), in Quarry's own profile, with no tools | Your Claude subscription |
| `api`                  | Claude through the Anthropic API; needs `ANTHROPIC_API_KEY`                     | Per token |
| `fake`                 | The same deterministic layout every time, with no network call                 | Free |

Both Claude choices draft with `claude-opus-5-5` at `high` effort and the same prompts. An API key in your environment never changes the default, and `subscription` hides it from the CLI so it can't bill per token.

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
- **Human acts are human-only.** Only a human can approve, waive, reject, Reopen or change the Brief. The Site refuses these acts from the Agent or from any automated caller, and no setting turns this off. When the CLI is run without a terminal (from a pipe, script or CI), it passes an automated identity, so the act is refused. See [ADR-0004](docs/adr/0004-checkpoint-acts-are-human-only-enforced-in-core.md).
- **Edits make Revisions.** A human edit (moving a Landmark, which brings its Paths' ends along; moving, resizing, re-heighting or recombining a Zone; restacking Zones; changing a Reading's limit) applies to the current Revision only and creates the next one, recording who made it. Whatever it touched gets a human Reason, and everything else keeps the AI's. Edits are human-only, and an approved Blockout can't be edited.
- **The page acts as you, or as no one.** `quarry open` fixes its caller at launch: you, when run from a terminal, otherwise an automated caller, so every act the page sends is refused. The page listens only on 127.0.0.1, and every request must carry the random token in the URL it printed.
- **Rejections need a note** and keep the Revision. A rejected Revision stays viewable and can be revived.
- **Nothing is built on an unapproved Blockout.** A Refine Plan is refused until the Blockout is approved, and the Refine Plan passes its own Checkpoint under the same rules.
- **One definition of height.** Zones combine in Stacking Order by their Combine Mode (`add`, `max` or `replace`). Each point takes its surface values, such as roughness and vegetation, from its topmost Zone alone, never from a blend. Checks and the Terrain Builder share this one definition.
- **Each Checkpoint gets its own Waivers.** Approving the Refine Plan needs a Waiver for every Check that misses on the Terrain, even one that was waived at Checkpoint #1.
- **Pads are flattened.** The Terrain Builder holds every Pad level at its centre's height and eases it back into the ground beyond. The Pad Check then measures it on the Terrain.
- **The Refine Plan shapes edges, and nothing else of the Blockout's.** Each Zone's edge eases in over its `falloff_width`, centred on the rim so the Zone keeps its size, following its `slope_profile` (`linear`, `smooth` or `steep`). Refine Plan edits can change only slope profile, falloff width, roughness, seed and vegetation density, and each edit makes a new Revision.
- **Terrain is built by code, not the AI.** The same Blockout and Refine Plan always give byte-identical Terrain, whose only randomness is the Refine Plan's seed. Terrain names the Blockout Revision and Refine Plan Revision it came from. See [ADR-0001](docs/adr/0001-approved-blockout-is-the-contract.md).
- **Going back supersedes, never patches.** A Reopen withdraws the Blockout's Approval. Every Refine Plan Revision built on it becomes Superseded: still viewable, and its Terrain still walkable read-only, but closed to every act and never exportable. Changing the Brief after Approval Reopens first. Terrain changes only through a new Blockout or Refine Plan Revision.
- **Carry-forward keeps what didn't change.** The first Refine Plan after a Reopen keeps the Superseded plan's values for every surface the new Blockout left untouched, each with a Reason naming the Revision it came from. It still needs its own Approval. A Zone or Cut Path is touched if it was edited (including restacked), or if it overlaps the old or new shape of anything edited: a Zone, a Cut Path's strip or a Landmark's Pad.
- **Edit Requests never apply silently.** At Checkpoint #1 the Agent answers with a new Blockout Revision. At Checkpoint #2 it answers with a new Refine Plan Revision, or with "needs Reopen" naming the Blockout property, and nothing changes until you Reopen. The answer is validated like any Draft. It may hand back an unchanged choice with that choice's Reason, even a human one, but never put a human Reason on something it changed.
- **Export is verified, not trusted.** Export is refused until the Refine Plan is approved, and for Superseded Terrain always. The `.glb` names its collision mesh `terrain_collision-colonly`, so Godot 4 builds a StaticBody3D named `terrain_collision` on import. No other node may end in a Godot import hint, and no two sibling nodes may keep the same name once Godot strips one. Under `landmarks` is an empty anchor per Landmark, standing on its Pad; under `paths`, a line-strip curve per Path, laid along the ground; on `terrain`, vegetation density in its glTF extras, which Godot reads as `get_meta("extras")["vegetation_density"]` (spacing, rows, columns, and one value per height sample, row by row from the footprint's corner; see [In Godot](#in-godot)). Each Export is re-imported and re-measured before the file is kept: every node name as Godot will read it, every collision height against the Terrain, every anchor against its Landmark, every curve against its Path.
- **Every guard is proven able to fail.** `quarry selftest` steepens a Path, moves a Landmark off its Pad, tilts a Pad, changes Terrain without a Revision, has the Agent approve, reuses a Checkpoint #1 Waiver at #2 and exports Superseded Terrain, and each must be caught by the guard meant for it. The tests switch each guard off in turn and check that the self-test then fails. See [ADR-0002](docs/adr/0002-standalone-core-browser-checkpoints-glb-export.md).

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
  claude_agent.py  The Claude adapters' shared prompts, schemas and model; the API adapter
  claude_code_agent.py  The subscription adapter: `claude -p` in an isolated profile
  validation.py The validation layer every Agent output passes before it is kept
  brief.py      Brief and Walk Targets, loaded from JSON; the Brief Check
  blockout.py   Blockout: Landmarks with Pads, Paths, Zones and Readings, each with a Reason
  refine.py     Refine Plan: how each surface looks up close, with a Reason
  terrain.py    Terrain Builder: Surface + Refine Plan → height and vegetation grids
  export.py     .glb writer with Godot collision naming, anchors, curves and vegetation; its re-import; the .tscn
  selftest.py   Deliberate corruptions, each of which must be caught
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

The MVP is planned as sixteen vertical slices in [.scratch/quarry-mvp/issues/](.scratch/quarry-mvp/issues/):

1. ✅ Tracer: Brief → Blockout → Checks → Approve/Reject via CLI
2. ✅ Tracer: Refine Plan → Terrain → `.glb`
3. ✅ All Blockout Checks: overlapping Zones, slope-aware walking, Brief Check, Readings, Pads
4. ✅ Checkpoint #1 page: a top-down Blockout view in the browser, with edits and human acts
5. ✅ Checkpoint #2: Checks on Terrain, Waivers per Checkpoint, and a walkable preview
6. ✅ Live Agent: a Claude-backed adapter with a validation layer
7. ✅ Draft quality review (human)
8. ✅ Going back: Reopen, carry-forward and Edit Requests
9. ✅ Complete Export and the corruption self-test
10. Verify in Godot 4: passes in Godot 4.7, headless and walked first-person; closes once 18 is fixed
11. ✅ Subscription Agent: draft on the Claude subscription via Claude Code, the default (blocks 7)
12. ✅ Shortcut Check: a Brief can mark a walk no Shortcut, and any faster walkable route misses (blocks 7, 13)
13. ✅ Cut Paths: a Path can grade its own strip of ground, to force a route up a steep hill (blocks 7)
14. ✅ Pad blend: flattening a Pad never steepens the ground around it (blocks 7)
15. ✅ Brief Check: refuse a Brief whose other Walk Targets undercut a forced walk
16. ✅ Path slope Check judges the ground's slope too, like the Shortcut Check
17. ✅ Godot names the collision body at random (found in 10)
18. Paths arrive in Godot as lines, not curves (found in 10; needs a decision)
19. ✅ Vegetation metadata sits under `extras` in Godot (found in 10)
