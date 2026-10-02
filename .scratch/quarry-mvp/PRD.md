# PRD: Quarry MVP — AI-drafted terrain with human Checkpoints

Status: ready-for-agent

## Problem Statement

A game developer who wants a playable outdoor space has two bad options today. Hand-sculpting terrain is slow and gets the one thing they actually care about — how long it takes to walk from spawn to the lighthouse, whether the hill is gentle enough to feel cozy — only by trial and error. Asking an AI to generate terrain is fast but opaque: the result arrives with no account of why anything is where it is, small corrections mean regenerating everything and hoping, and there is no point at which a human has genuinely signed off on what was built. The developer cannot trust, inspect, or cheaply steer what the AI produced, and nothing stops an unreviewed change from flowing straight into their game.

## Solution

Quarry turns a short **Brief** — a footprint, named **Waypoints**, **Walk Targets** between them, a **Walk Speed**, a **Max Walkable Slope** and a plain-language mood — into exportable game **Terrain** through two human **Checkpoints** that cannot be skipped.

First, Quarry runs a **Brief Check** and refuses to draft if the Brief is provably impossible. The AI then drafts a **Blockout**: overlapping **Zones** on the **Ground**, **Landmarks** with **Pads**, **Paths**, and **Readings** that make its interpretation of the mood explicit — every choice carrying a plain-language **Reason**. At Checkpoint #1 the developer sees a top-down Blockout in seconds, with every **Check** measured (walk times along Paths with slope, slope limits, Pads, measurable Readings). They drag, resize and edit for free; each edit is a new **Revision**, re-measured instantly. They **Approve** one exact Revision — with a **Waiver** for any missed Check — or **Reject** it with a note.

Second, the AI writes a **Refine Plan**: per-Zone choices like slope profile, roughness, seed and vegetation, each with a Reason. Code — not the AI — deterministically builds Terrain from Blockout + Refine Plan. At Checkpoint #2 the developer walks the Terrain in a browser preview, sees every Check re-run on the real geometry, and makes **Edit Requests** ("make this hill less steep"). Requests the Refine Plan can satisfy produce a new Revision without regenerating anything else; requests that need a Blockout change are named as such and offered as a **Reopen**, never applied silently. Once the Refine Plan is approved, the developer **Exports** a `.glb` that Godot imports with collision, Landmark anchors, Path curves and vegetation density.

The AI can never Approve, Waive, Reject or Reopen. That is enforced by the core, so the promise "nothing ships without a human checkpoint" is structural, not a convention.

## User Stories

### Site and Brief

1. As a game developer, I want to create a new **Site** from a **Brief**, so that all work on one area lives in one place with its full history.
2. As a game developer, I want to give the Brief a footprint size in metres, so that the Terrain matches the space my game needs.
3. As a game developer, I want to name **Waypoints** like "spawn", "lighthouse" and "village", so that the AI places things I care about rather than inventing its own.
4. As a game developer, I want to set a **Walk Target** between two Waypoints as a time or distance with a tolerance, so that pacing is something Quarry measures, not something the AI asserts.
5. As a game developer, I want to set a **Walk Speed** for my player, so that "3 minutes" means the same thing to Quarry as to my game.
6. As a game developer, I want sensible defaults for Walk Speed and **Max Walkable Slope**, so that I can start with only a footprint, a couple of Waypoints and a mood.
7. As a game developer, I want to describe the mood in plain language ("gentle hills, forested, cozy exploration game"), so that I don't have to translate taste into parameters myself.
8. As a game developer, I want a **Brief Check** to tell me before any drafting that a Walk Target cannot possibly fit in the footprint, so that I don't wait for a Draft that was doomed.
9. As a game developer, I want the Brief Check to flag a Walk Target that names a Waypoint that doesn't exist, so that typos don't silently become missing Landmarks.
10. As a game developer, I want a failing Brief Check to block drafting until I fix the Brief, so that the AI never "creatively" works around an impossible request.
11. As a game developer, I want a Brief Check that only flags provable impossibilities, so that merely hard targets are still attempted.
12. As a game developer, I want to make a variant by creating a new Site from a copy of an existing Brief, so that I can explore "rainier, more vertical" without disturbing the original's history.

### Blockout drafting (AI)

13. As a game developer, I want the AI to draft a Blockout of Zones, Landmarks, Pads and Paths from my Brief, so that I get a first layout in seconds.
14. As a game developer, I want every Waypoint to appear as exactly one Landmark, so that nothing I named goes missing.
15. As a game developer, I want any Landmark the AI added on its own to be marked as AI-chosen, so that I can tell my intent apart from its suggestions.
16. As a game developer, I want every Walk Target to have exactly one Path, so that I know exactly which route the walk time was measured on.
17. As a game developer, I want the AI to be allowed decorative Paths that no Walk Target measures, so that the layout can suggest exploration beyond the required routes.
18. As a game developer, I want Zones that can overlap (a hill on a plateau), so that the Blockout can express natural compound landforms.
19. As a game developer, I want each Zone to show its **Combine Mode** (add, max, replace) and its place in the **Stacking Order**, so that what happens where Zones overlap is visible, not an engine mystery.
20. As a game developer, I want the AI's interpretation of my mood listed as **Readings** ("'gentle' → slopes ≤ 15°"), so that I can see and correct its taste before it shapes everything.
21. As a game developer, I want every choice in the Blockout to carry a **Reason** ("placed the lighthouse here because it is a 3:02 walk from spawn"), so that I understand why, not just what.
22. As a game developer, I want the AI to still deliver a Blockout when it cannot meet a Walk Target, with a Reason that owns the miss, so that I decide what to compromise rather than the AI.
23. As a game developer, I want the AI never to rewrite my targets to make them pass, so that the Brief always means what I wrote.
24. As a game developer, I want a Rejection note I wrote to feed the next Blockout Draft, so that "too flat, wanted more verticality" actually changes the result.

### Checkpoint #1 — reviewing the Blockout

25. As a game developer, I want a top-down Blockout view that loads in a few seconds, so that reviewing is fast enough to do every time.
26. As a game developer, I want every Check shown with its measured value and its target ("measured 2:51 against a 3:00 target, ±10%"), so that I see exactly how close each one is.
27. As a game developer, I want Path slope checked against the Max Walkable Slope, so that a route over a cliff doesn't "pass" on distance alone.
28. As a game developer, I want measurable Readings shown as Checks and unmeasurable ones shown as plain statements, so that I know which interpretations are enforced.
29. As a game developer, I want to drag a Landmark and see Checks re-measure instantly, so that edits are cheap and I can feel the consequences.
30. As a game developer, I want to resize or move a Zone, change its height, Combine Mode or Stacking Order, so that I can fix the layout directly instead of describing the fix.
31. As a game developer, I want to edit a Reading (e.g. change "≤ 15°" to "≤ 20°"), so that the AI's guess doesn't become a constraint I disagree with.
32. As a game developer, I want each edit to produce a new Revision, so that I always know exactly which version I'm approving.
33. As a game developer, I want the AI's Reason replaced by "moved by you" on anything I edited, so that a stale justification never sits next to my change.
34. As a game developer, I want to approve one exact Revision, so that approval can never mean "what I saw before my last drag".
35. As a game developer, I want Approval blocked while any Check misses without a Waiver, so that no miss slips through unnoticed.
36. As a game developer, I want to give a Waiver per missed Check, so that I can accept a known compromise deliberately and on record.
37. As a game developer, I want to Reject a Revision with a required note, so that the AI knows what was wrong.
38. As a game developer, I want rejected Revisions kept and viewable, so that I can look back at or revive an earlier idea.
39. As a game developer, I want to make Edit Requests in plain language at Checkpoint #1 too, so that I can ask the AI for changes I'd rather not do by hand.

### Refine Plan drafting (AI)

40. As a game developer, I want the AI to draft a Refine Plan only after the Blockout is approved, so that nothing is built on an unapproved layout.
41. As a game developer, I want the Refine Plan to give per-Zone slope profile, falloff width, roughness, seed and vegetation density, each with a Reason, so that I can see how the AI intends to make it look up close.
42. As a game developer, I want Refine Plan Reasons to account for Path effects ("kept roughness low along the Path so the walk stays at 3:05"), so that refinement doesn't quietly break pacing.
43. As a game developer, I want the Refine Plan unable to change anything the Blockout owns (Zone shapes, heights, Combine Modes, Stacking Order, Landmarks, Paths, Readings), so that Checkpoint #2 can never undo Checkpoint #1.

### Terrain building (code)

44. As a game developer, I want Terrain built deterministically from Blockout + Refine Plan, so that the same approved inputs always yield the same geometry.
45. As a game developer, I want every Terrain traceable to exactly one Blockout Revision and one Refine Plan Revision, so that I can always answer "where did this come from?".
46. As a game developer, I want height where Zones overlap to follow Combine Mode in Stacking Order, and surface values to come from the topmost Zone alone, so that every spot has one unambiguous owner.
47. As a game developer, I want each Landmark's Pad flattened to near-flat, so that I can actually place a building there.
48. As a game developer, I want Terrain rebuilt in seconds after a Refine Plan change, so that edits at Checkpoint #2 are cheap.

### Checkpoint #2 — reviewing the Terrain

49. As a game developer, I want to walk the Terrain in a first-person browser preview at my Brief's Walk Speed, so that I judge pacing and feel, not just numbers.
50. As a game developer, I want every Check re-run on the Terrain against the same targets, so that a walk that passed on the Blockout but got steeper after refining shows red.
51. As a game developer, I want Pad flatness checked ("lighthouse Pad: max slope 3°, measured 2.1°"), so that refinement noise can't put a building on a lump.
52. As a game developer, I want a Waiver given at Checkpoint #1 not to cover a miss at Checkpoint #2, so that each Draft really gets its own review.
53. As a game developer, I want to see the Refine Plan alongside the Terrain it produced, so that I know which choice caused what I'm looking at.
54. As a game developer, I want to edit Refine Plan values directly, so that "a bit rougher here" doesn't need the AI at all.
55. As a game developer, I want an Edit Request like "make this hill less steep" answered with a new Refine Plan Revision when possible, so that I don't regenerate everything for a small change.
56. As a game developer, I want an Edit Request that needs a Blockout change answered with "this needs Zone height lowered to 25 m — Reopen Checkpoint #1?", so that I decide whether to go back.
57. As a game developer, I want to Approve the Refine Plan, with Waivers for any misses, so that the Terrain becomes exportable.
58. As a game developer, I want to Reject the Refine Plan with a note, so that the AI tries again with my feedback.

### Reopen and supersession

59. As a game developer, I want to Reopen an approved Blockout, so that I can make a layout change I only noticed while walking the Terrain.
60. As a game developer, I want Reopening to mark the current Refine Plan and Terrain **Superseded**, still viewable but never exportable, so that I can't accidentally export Terrain from a layout I've since changed.
61. As a game developer, I want changing the Brief after Approval to Reopen the Blockout, so that a new mood or target can never sit under an old approval.
62. As a game developer, I want the next Refine Plan to carry untouched Zones' values forward verbatim, with a Reason naming the source Revision, so that a small layout change doesn't throw away refinement I already approved of.
63. As a game developer, I want "touched" to mean the edited Zone plus every Zone overlapping its old or new shape, so that carry-forward never keeps values for ground that actually changed.
64. As a game developer, I want a carried-forward Refine Plan to still need its own Approval, so that nothing is pre-approved by history.
65. As a game developer, I want there to be no way to patch Terrain directly, so that every change stays traceable through a Revision.

### Export

66. As a game developer, I want to Export only from Terrain whose Refine Plan is approved and not Superseded, so that everything I ship was reviewed.
67. As a game developer, I want the Export as a `.glb` whose collision meshes follow Godot's import naming, so that Godot builds collision on import with no manual setup.
68. As a game developer, I want an optional thin `.tscn` that instances the `.glb`, so that I can drop the Site straight into a Godot scene.
69. As a game developer, I want each Landmark exported as a named, empty anchor at its exact position, so that my designer can place the real asset there.
70. As a game developer, I want each Path exported as a curve, so that my game can lay roads or navigation along it later.
71. As a game developer, I want vegetation exported as density data, so that my engine scatters trees its own way and the Export stays light.
72. As a game developer, I want every Export round-tripped and re-measured, so that collision and anchors are proven present rather than trusted.

### Integrity and history

73. As a game developer, I want every Approval, Waiver, Rejection and Reopen to record who did it and when, so that I can audit how a Terrain came to be.
74. As a game developer, I want the AI structurally unable to perform those acts, with no auto-approve setting, so that the human checkpoint is a guarantee.
75. As a game developer, I want a Site's full history (every Revision, Check result, Approval and Export) kept immutable and linear, so that I can reconstruct any past state.
76. As a game developer, I want to see where a Site currently stands (which Checkpoint, which Revision, what's Superseded), so that I can pick up work after a break.

### CLI

77. As a game developer, I want CLI commands to create a Site, run the Brief Check, request a Draft, open a Checkpoint page and Export, so that I can drive Quarry from a terminal.
78. As a game developer, I want a CLI command that prints a Site's current status and Checks tersely, so that I (or an agent helping me) can check progress cheaply.

## Implementation Decisions

**Language and shape.** Python core (confirmed; following the Contour precedent), with local browser pages in plain JavaScript using three.js for the Checkpoint views. A standalone core with browser Checkpoints, not a Godot plugin (ADR-0002).

**Governing ADRs.**
- ADR-0001: the approved Blockout is the contract, and Terrain is a pure function of Blockout + Refine Plan. The AI never authors geometry.
- ADR-0002: standalone core, browser Checkpoints, `.glb` export with Godot `-col`/`-colonly` collision naming. Godot 4 is the first target engine.
- ADR-0003: each property is owned by exactly one stage. The Blockout owns *where and how big*, and the Refine Plan owns *how it looks up close*.
- ADR-0004: Approval, Waiver, Rejection and Reopen are human-only, enforced in the core, with no auto-approve setting.

**Modules.**

1. **Ledger**: the Site's append-only history and checkpoint state machine. Interface: append a Draft Revision (from the Agent or from a human edit); record a human act (Approve naming one Revision plus one Waiver per missed Check; Reject plus a required note; Reopen); query current state. It enforces:
   - Approval names one exact Revision.
   - Approval is refused while a missed Check has no Waiver.
   - A Refine Plan cannot be drafted on an unapproved Blockout.
   - A Reopen marks the downstream Refine Plan and Terrain Superseded.
   - A Brief change after Approval triggers a Reopen.
   - Human acts require a human identity and are refused from the Agent or any automated caller.
   - Nothing is deleted; history is linear with no branches.
2. **Brief Check**: Brief → list of provable impossibilities. It covers Walk Targets that cannot fit within the footprint at the Walk Speed and Max Walkable Slope, and references to undefined Waypoints. It never flags targets that are merely hard.
3. **Surface**: Ground + Zones → height and topmost Zone at any point. Height combines in Stacking Order per each Zone's Combine Mode. Surface values come from the topmost Zone only. This is the single definition of height, shared by Checks and by the Terrain Builder.
4. **Checks**: Brief + Blockout + a surface (the Blockout's coarse surface or a built Terrain) → a list of results, each with a target, a measured value and pass/miss. It covers walk time/distance along each measured Path including slope, Path max slope against the Max Walkable Slope, Pad flatness, and measurable Readings. The same function serves both Checkpoints.
5. **Terrain Builder**: Blockout + Refine Plan → Terrain (a height grid, Pad flattening, a per-point vegetation density, and Zone ownership). It is deterministic: identical inputs give byte-identical output, with all randomness taken from Refine Plan seeds. The Terrain records the two Revision identifiers it came from.
6. **Carry-forward**: old Blockout + new Blockout + old Refine Plan → the set of touched Zones and a pre-filled next Refine Plan. A Zone counts as touched if it was edited or overlaps the edited Zone's old or new shape. Carried values carry a Reason naming the source Revision.
7. **Agent**: a port with an LLM-backed adapter (latest Claude model) and a fake. Operations:
   - Draft a Blockout from the Brief, plus an optional Rejection note.
   - Draft a Refine Plan from an approved Blockout plus carried values.
   - Answer an Edit Request with either a new Revision or a "needs Reopen" result naming the Blockout-owned property.

   All Agent output passes a validation layer before it reaches the Ledger: the schema is valid, every choice has a Reason, every Waypoint becomes exactly one Landmark, every Walk Target has exactly one Path, and the Agent never touches a property owned by the other stage. The Agent has no access to human acts.
8. **Exporter**: approved, non-Superseded Terrain → a `.glb` with terrain mesh, collision meshes named for Godot import, an empty named anchor per Landmark, a curve per Path, and vegetation density data, plus an optional `.tscn` that instances it. Every Export is re-imported and re-measured: collision present, anchors at their positions, Paths present.
9. **Checkpoint pages**: a local server and pages.
   - Checkpoint #1: a top-down Blockout editor with Zones, Landmarks, Pads, Paths and Readings, live Check results, drag/resize edits that become new Revisions, Edit Requests, and Approve-with-Waivers or Reject-with-note.
   - Checkpoint #2: a first-person walkable preview at Walk Speed, the Refine Plan shown alongside, Check results on Terrain, Refine Plan value edits, Edit Requests, and Approve or Reject.

   Human acts are sent with the user's identity.
10. **CLI**: thin wiring that creates Sites, runs the Brief Check, requests Drafts, opens Checkpoint pages, prints terse status and Check results, and Exports.

**Key data shapes (in prose).**
- A Revision is immutable and identified within its Site.
- Every choice in a Blockout or Refine Plan carries one Reason with an author: the AI, the human, or carried from a named Revision.
- A Check result records which Check, its target, the measured value, and pass/miss.
- An Approval records the Revision, its Waivers, who performed it and when.

**Edits are cheap by construction.** Human edits at either Checkpoint create Revisions without involving the Agent. Re-measuring and rebuilding Terrain are pure code paths that must finish in seconds for an MVP-sized Site.

## Testing Decisions

**What a good test is here.** Tests exercise each module only through its public interface, in domain terms, and assert observable results such as "Approval is refused," "walk measures 2:51," or "same inputs → identical Terrain." They never assert internal data structures. A test should fail exactly when a domain rule in CONTEXT.md is broken.

**Tested modules:**
- **Ledger**: every state-machine rule, including Approval of a non-current Revision, Approval with an unwaived miss, a Refine Plan drafted on an unapproved Blockout, Reopen superseding downstream state, a Brief change after Approval, Waivers not carrying across Checkpoints, and human acts refused from non-human callers.
- **Checks**: use hand-built Blockouts with known answers, for example a straight Path on flat Ground gives an exact walk time, and a Path over a known slope fails the Max Walkable Slope. Run the same cases against Blockout and Terrain surfaces.
- **Surface**: overlap fixtures for each Combine Mode and Stacking Order, plus topmost-Zone ownership of surface values.
- **Terrain Builder**: determinism (build twice, compare), traceability (the Terrain names its Revisions), and Pad flatness.
- **Carry-forward**: the touched set for a move, a resize, an overlap gained and an overlap lost. Untouched values are carried verbatim, with source Reasons.
- **Exporter**: a round-trip test that exports, re-imports, and asserts that collision, Landmark anchors and Path curves are present. Exporting from Superseded or unapproved Terrain is refused.
- **Brief Check**: provably impossible Briefs are flagged, and hard-but-possible Briefs are not.
- **Agent**: only through the fake LLM and the validation layer. Tests check that malformed output, missing Reasons, missing Landmarks or Paths, and cross-stage property writes are rejected, and that Edit Request routing returns "needs Reopen" for Blockout-owned properties. No live LLM calls run in tests.

**Proving the Checks can fail.** Following Contour's prior art (`selftest` deliberately corrupts a build in many ways to prove its checks catch each one), Quarry should include a mutation-style self-test. It takes a known-good Site, applies deliberate corruptions such as steepening a Path, moving a Landmark off its Pad, or editing Terrain without a Revision, and asserts that the relevant Check or Ledger rule catches each one. Contour's `.glb` round-trip re-measure is also prior art for the Exporter test. Quarry has no code yet, so there is no in-repo prior art.

**Not tested in the MVP:** Checkpoint pages and the CLI, which are thin wiring over the tested modules.

## Out of Scope

- Landmark geometry. Quarry exports anchors, never buildings or props.
- Placing individual vegetation instances in the Export. Only density data is exported.
- Branching within a Site. Variants are separate Sites made by copying a Brief.
- Multiple reviewers, roles or permissions. The MVP assumes one human per Site, with identity recorded.
- Engines other than Godot as a verified target, though glTF keeps them reachable.
- Any auto-approve, batch-approve or CI-approve path, permanently and by design (ADR-0004).
- Texturing, materials, water simulation, weather and lighting.
- Very large or streamed worlds. The MVP targets footprints in the hundreds of metres.
- A Godot editor plugin (rejected in ADR-0002).

## Further Notes

- The domain glossary is `CONTEXT.md` at the repo root, and decisions are in `docs/adr/0001`–`0004`. Use the glossary's terms and avoid its listed synonyms in code, issues and UI copy.
- **Confirmed:** Godot 4 is the first target engine, and the core is written in Python.
- The sibling project Contour (separate codebase) is the conceptual model: propose → confirm → write, a spec as the source of truth, and checks proven able to fail. Quarry borrows the model but not the code or the vocabulary.
