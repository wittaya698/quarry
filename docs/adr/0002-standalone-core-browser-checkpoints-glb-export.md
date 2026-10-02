# Standalone core with browser Checkpoints; export is glTF with Godot collision naming

Quarry is a standalone core (Brief → Blockout → Refine Plan → Terrain, plus every Revision, Check and Approval) with a local browser page for each Checkpoint: a top-down Blockout view at Checkpoint #1 and a walkable preview at Checkpoint #2. Export is a `.glb` whose collision meshes follow Godot's import naming (`-col` / `-colonly`), optionally wrapped in a thin `.tscn` that instances it. We rejected a Godot editor plugin, despite its free viewport, walk preview and native collision, because it would put the draft/build separation (ADR-0001) and the Revision history inside one engine's scripting layer and lock Quarry to Godot; glTF keeps other engines reachable.

## Consequences

- Quarry must ship its own minimal first-person walker for the Checkpoint #2 preview.
- Godot 4 is the first target engine. Collision correctness is proven by round-tripping the `.glb`, not by trusting the exporter.
