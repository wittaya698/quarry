# Quarry

A terrain-authoring tool for game developers in which an AI agent drafts terrain and a human approves every draft at a checkpoint before it counts.

## Language

**Site**:
One **Brief** together with its whole linear history of **Revisions**, **Checks**, **Approvals** and **Exports**.
_Avoid_: Project, world, scene, map

### Input

**Brief**:
The user's description of what to build — a footprint, named **Waypoints**, **Walk Targets** between them, a **Walk Speed**, a **Max Walkable Slope** and a plain-language mood.
_Avoid_: Area definition, prompt, spec, request

**Waypoint**:
A point the user names in the **Brief** (e.g. spawn, lighthouse) whose position the AI decides.
_Avoid_: Point, marker, POI

**Walk Target**:
A desired walking time or distance between two **Waypoints**, with a tolerance; the **Brief** may mark it no **Shortcut**.
_Avoid_: Distance constraint, travel time

**Shortcut**:
A walkable route from a **Walk Target**'s first **Waypoint** to its second that is faster than the **Walk Target** allows, found anywhere on the ground rather than along the **Path**; walkable means never climbing onto ground steeper than the **Max Walkable Slope** in its steepest direction, so switchbacks across a steep face do not climb it, though it may drop down any slope, as a player can.
_Avoid_: Bypass, cheat, skip

**Walk Speed**:
The player's walking pace that converts a walk time into a distance along a path.
_Avoid_: Movement speed, velocity

**Max Walkable Slope**:
The steepest incline a player is meant to walk, which every measured **Path** must stay under.
_Avoid_: Slope limit, max grade, climb angle

**Brief Check**:
A **Check** on the **Brief** alone, run before any **Draft**, that catches provable impossibilities such as a **Walk Target** that cannot fit in the footprint.
_Avoid_: Validation, preflight, lint

### Stages

**Blockout**:
A coarse, primitive-based layout of a **Site** — **Zones**, **Landmarks**, **Paths** and **Readings** — that a human can take in at a glance.
_Avoid_: Sketch, layout, plan, draft (as a noun for this)

**Ground**:
The base surface of the footprint that every **Zone** sits on.
_Avoid_: Base layer, default zone, floor

**Zone**:
A shaped elevation feature in a **Blockout** (e.g. a hill, a lake, a plateau) placed on the **Ground**; **Zones** may overlap.
_Avoid_: Region, area, elevation zone, patch

**Stacking Order**:
The explicit order of a **Blockout**'s **Zones**, which decides which **Zone** is on top where they overlap.
_Avoid_: Z-order, layer, priority

**Combine Mode**:
How a **Zone**'s height joins what lies beneath it — add, max or replace.
_Avoid_: Blend mode, operator, merge

**Landmark**:
A positioned feature in a **Blockout** — either a placed **Waypoint** or one the AI added on its own, marked as AI-chosen.
_Avoid_: POI, feature, marker

**Pad**:
The near-flat buildable area around a **Landmark**, sized in the **Blockout** and held to a slope limit by a **Check**.
_Avoid_: Footprint (that is the **Site**'s extent), base, plinth

**Path**:
An AI-drawn intended route between two **Landmarks** in a **Blockout**; the player may still walk anywhere.
_Avoid_: Road, trail, route, navmesh

**Cut Path**:
A **Path** the AI marks to grade its own strip of ground, at least 4 m wide, rising evenly from its start **Landmark** to its end whatever the **Zones** beneath it do; used to force a route, such as a climb that winds up a hill too steep to climb anywhere else.
_Avoid_: Trail, road, ramp

**Reading**:
The AI's explicit interpretation of a phrase in the **Brief**'s mood as something concrete (e.g. "gentle" → slopes ≤ 15°), carried in a **Blockout** with its **Reason**.
_Avoid_: Assumption, interpretation, inference

**Draft**:
Any AI-produced **Blockout** or **Refine Plan** that has not yet passed its **Checkpoint**.
_Avoid_: Proposal, candidate, suggestion

**Refine Plan**:
The AI's per-zone choices for turning an approved **Blockout** into **Terrain** — values such as slope profile, roughness, seed and vegetation density — each with its reason.
_Avoid_: Settings, parameters, config

**Terrain**:
The real geometry built from an approved **Blockout** and its approved **Refine Plan**, a pure function of the two rather than a fresh interpretation.
_Avoid_: Map, level, mesh, heightmap (those are representations, not the concept)

**Export**:
The game-engine output of a **Site** — **Terrain** geometry and collision, an anchor per **Landmark**, a curve per **Path** and vegetation as density — produced only when the **Refine Plan** is approved and not **Superseded**.
_Avoid_: Build, publish, ship

### Review

**Checkpoint**:
The human review point every **Draft** must pass, where it is approved, rejected or edited.
_Avoid_: Gate, review step, approval step

**Approval**:
The explicit human act at a **Checkpoint** that turns one exact **Revision** of a **Draft** into the contract the next stage is built from.
_Avoid_: Accept, sign-off, confirm

**Revision**:
One immutable version of a **Draft**; every AI pass and every human edit produces a new one.
_Avoid_: Version, iteration, snapshot

**Reason**:
The plain-language justification attached to a single choice in a **Draft**, stating who made it (the AI or the human) and why.
_Avoid_: Explanation, rationale, comment

**Check**:
A measured comparison of a **Blockout** or **Terrain** against a target — a **Walk Target**, the **Max Walkable Slope**, a measurable **Reading** or a **Pad** — that passes or misses.
_Avoid_: Test, validation, constraint

**Edit Request**:
A plain-language change the human asks for at a **Checkpoint** (e.g. "make this hill less steep"), which the AI answers with a new **Revision** or by naming the **Reopen** it would need.
_Avoid_: Feedback, tweak, prompt

**Rejection**:
The human act at a **Checkpoint** that discards a **Revision** with a required note saying what was wrong, prompting a fresh **Draft**.
_Avoid_: Decline, deny, reroll

**Reopen**:
Returning an approved **Blockout** to its **Checkpoint** to change it, which supersedes everything built on it.
_Avoid_: Unlock, revert, edit-after-approve

**Superseded**:
The state of a **Refine Plan** or **Terrain** whose **Blockout** was **Reopened** — still viewable, never exportable.
_Avoid_: Stale, outdated, invalid, deleted

**Waiver**:
An explicit acknowledgement, recorded with an **Approval**, that a named **Check** is missed and accepted anyway.
_Avoid_: Override, exception, force-approve

## Relationships

- A **Brief** names one or more **Waypoints** and zero or more **Walk Targets**; each **Walk Target** joins exactly two **Waypoints**
- Every **Waypoint** becomes exactly one **Landmark** in a **Blockout**; a **Blockout** may also hold AI-chosen **Landmarks** that no **Waypoint** asked for
- A **Site** has exactly one **Brief** and one unbranched history; a variant is a new **Site** made from a copy of the **Brief**
- **Approval**, **Waiver**, **Rejection** and **Reopen** are performed only by a human, and each records who and when; the AI can never perform them
- A **Brief** is never a **Draft** and has no **Checkpoint**; a failing **Brief Check** blocks the first **Blockout**, and changing the **Brief** after **Approval** **Reopens** the **Blockout**
- When the AI cannot meet a **Walk Target** it still delivers the **Blockout**, with the missed **Check** and a **Reason** owning the miss; it never rewrites the **Brief**'s targets
- A **Blockout** carries one **Reading** per mood phrase it acted on; every measurable **Reading** is also a **Check** at both **Checkpoints**, and an unmeasurable one is shown but not checked
- Every **Walk Target** has exactly one **Path**; a **Blockout** may also hold decorative **Paths** no **Walk Target** measures
- A **Path** never changes the ground unless it is a **Cut Path**; the **Brief** asks for no **Shortcut**, a **Cut Path** is how the AI prevents one, and the **Shortcut** **Check** proves it
- A **Walk Target** is met or missed by measurement along its **Path**, slope included, never by the AI's say-so
- A **Walk Target** marked no **Shortcut** is also missed when any **Shortcut** exists; an unmarked one is never checked for **Shortcuts**, since the player may walk anywhere
- Every **Check** runs at both **Checkpoints** — on the **Blockout**, then again on the **Terrain**; a **Waiver** given at the first never covers a miss at the second
- Every **Draft** passes exactly one **Checkpoint** of its own; an earlier **Approval** never covers a new **Draft**
- A **Blockout** has one **Ground** and zero or more **Zones**; a spot on the footprint may lie under several **Zones** at once
- Where **Zones** overlap, height follows each **Zone**'s **Combine Mode** in **Stacking Order**; every surface value comes from the topmost **Zone** alone, never an average
- A **Cut Path**'s strip lies above every **Zone**: it is refined in the **Refine Plan** as a surface of its own, exactly once, and its values win along it
- A **Refine Plan** belongs to exactly one approved **Blockout**
- A **Terrain** is built from exactly one approved **Blockout** plus one **Refine Plan**, and is traceable back to both
- At the second **Checkpoint** the human reviews the **Refine Plan** together with the **Terrain** it produces; the **Approval** lands on the **Refine Plan**
- Nothing is built on a **Blockout** that has no **Approval**
- A **Draft** has one or more **Revisions**; an **Approval** names exactly one of them
- Every choice in a **Revision** carries exactly one **Reason**; a human edit replaces the AI's **Reason** for what it touched rather than leaving it standing
- A rejected **Revision** is kept, never deleted; its note feeds the next **Draft**
- **Reopening** a **Blockout** makes its **Refine Plan** and **Terrain** **Superseded**; the next **Refine Plan** carries untouched **Zones**' values forward verbatim (a **Zone** or **Cut Path** is touched if it was edited or overlaps the edited one's old or new shape), each with a **Reason** naming the **Revision** it came from, and still needs its own **Approval**
- The **Blockout** owns where and how big (**Zone** shapes and heights, **Combine Modes**, **Stacking Order**, **Landmarks**, **Paths** and which are **Cut Paths**, **Readings**); the **Refine Plan** owns how it looks up close; no property belongs to both
- An **Edit Request** at the second **Checkpoint** that needs a **Blockout**-owned change is never applied there — the AI names the property and offers a **Reopen**
- Every **Landmark** has exactly one **Pad**; an **Export** marks where a **Landmark** goes but never contains its geometry
- **Terrain** is never patched directly; any change reaches it only through a new **Blockout** or **Refine Plan** **Revision**
- An **Approval** carries one **Waiver** per missed **Check**; a missed **Check** without a **Waiver** blocks **Approval**

## Example dialogue

> **Dev:** "The user approved a **Blockout** yesterday and today only nudged one **Landmark** — can we skip the **Checkpoint**?"
> **Domain expert:** "No. The nudge made a new **Revision**, and the **Approval** names a **Revision**, not a **Draft** in general. The edit was cheap; the **Approval** still isn't optional."

> **Dev:** "At the second **Checkpoint** they asked to make the hill less steep. Can the AI just drop the **Zone** to 25 m?"
> **Domain expert:** "Height belongs to the **Blockout**. The AI first tries the **Refine Plan** — a wider falloff. If the 'gentle' **Reading** still misses, it says the fix needs a **Reopen**, and the human decides."

> **Dev:** "The spawn→lighthouse **Walk Target** passed on the **Blockout**. Do we re-measure on the **Terrain**?"
> **Domain expert:** "Always. Refinement can steepen the **Path**. A miss on the **Terrain** needs its own **Waiver** — the first **Checkpoint**'s doesn't carry over."

## Flagged ambiguities

- "footprint" was about to mean both the **Site**'s extent and a **Landmark**'s flat area — resolved: footprint is the **Site**'s extent in the **Brief**; a **Landmark**'s is its **Pad**.
- "marks it final" — resolved: there is no separate "final" state; **Approval** of the **Refine Plan** at the second **Checkpoint** is what makes **Terrain** exportable.
- "edit at a checkpoint" could have meant amending the approved thing in place — resolved: an edit makes a new **Revision** at the same **Checkpoint**, re-measured, needing its own **Approval**.
- "points" in the input and "landmarks" in the draft were the same idea under two names — resolved: the user names **Waypoints**; once placed they are **Landmarks**.
- "walk-time" had no speed or route — resolved: measured along the path including slope, at the **Brief**'s **Walk Speed**.
- "draft" was used both for the step that produces a **Blockout** and for any unapproved output — resolved: **Draft** means unapproved AI output of either stage (a **Blockout** or a **Refine Plan**); **Terrain** is never itself a **Draft**, since it is derived.
- "the AI refines into real terrain" — resolved: the AI writes a **Refine Plan**; code, not the AI, builds **Terrain** from it.
