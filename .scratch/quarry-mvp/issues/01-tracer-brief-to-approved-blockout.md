# 01 — Tracer: Brief → Blockout → Checks → Approve/Reject via CLI

Status: done

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

The first end-to-end path through Quarry, with no code existing yet. Using the CLI, a developer creates a **Site** from a **Brief** (footprint, named **Waypoints**, **Walk Targets**, **Walk Speed**, mood). The **Agent**, backed by a fake LLM, drafts a **Blockout** on flat **Ground** in which every Waypoint becomes one **Landmark** and every Walk Target gets one **Path**, each choice with a **Reason**. The walk-time **Check** measures each Walk Target along its Path. The **Ledger** stores the result as Revision 1, and `status` prints the Site's state and Check results tersely.

The developer then acts at Checkpoint #1 from the CLI: **Approve** one exact **Revision** (with one **Waiver** per missed Check) or **Reject** it with a required note. Each act records who and when, and the Ledger refuses these acts from the Agent or any non-human caller (ADR-0004). History is append-only, so rejected Revisions stay viewable and can be revived, and a variant Site can be made from a copy of a Brief.

This slice establishes the Python package, the Ledger, the Agent port with its fake, the Checks module and the CLI. Use the glossary terms in `CONTEXT.md` for every name.

## Acceptance criteria

- [x] The CLI creates a Site from a Brief file, with defaults for Walk Speed and Max Walkable Slope
- [x] Drafting with the fake Agent produces a Blockout Revision with one Landmark per Waypoint, one Path per Walk Target, and a Reason on every choice
- [x] The walk-time Check reports target, measured value and pass/miss; a straight Path on flat Ground measures exactly length ÷ Walk Speed
- [x] `status` prints the current Checkpoint, Revision and Check results
- [x] Approve names one Revision; it is refused for a non-current Revision, and refused while any missed Check lacks a Waiver
- [x] Reject requires a note; the rejected Revision is kept and viewable, and can be revived as a new Revision
- [x] Approve, Waive and Reject record who and when; the Ledger refuses them from the Agent or any non-human caller, with no bypass setting
- [x] A new Site can be created from a copy of an existing Site's Brief, with independent history
- [x] Tests cover the Ledger rules, the walk Check and the fake-Agent path through public interfaces only

## Blocked by

None - can start immediately
