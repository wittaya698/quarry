# 08 — Going back: Reopen, carry-forward and Edit Requests

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

Make reversal and plain-language changes work end to end.
- **Reopen:** the developer can Reopen an approved Blockout from the CLI or either page. The current Refine Plan and Terrain become **Superseded**: still viewable, never exportable. Changing the Brief after Approval Reopens the Blockout.
- **Carry-forward:** after the new Blockout is approved, the next Refine Plan is pre-filled with untouched Zones' values copied verbatim, each with a Reason naming its source Revision. A Zone is touched if it was edited or overlaps the edited Zone's old or new shape. The pre-filled plan still needs its own Approval. Terrain can never be patched directly.
- **Edit Requests:** at either Checkpoint the developer types an Edit Request. The Agent answers with a new Revision of the current stage, or, when the change needs a property the Blockout owns (asked at Checkpoint #2), with "needs Reopen", naming the property and offering a Reopen. The change is never applied silently.

## Decided (2026-10-09)

- **Touched** goes a little past the spec, so carry-forward never keeps values for ground that changed. A Zone counts as edited if its shape, height, Combine Mode or place in the Stacking Order changed. A moved or resized Landmark Pad touches the Zones and Cut Paths under its old and new Pad. "ground" is always carried.
- **Carry-forward** fills only the first Refine Plan after a Reopen. The Agent drafts the whole plan, and each untouched surface is then replaced by the Superseded plan's value, unchanged, with the Reason "carried from Refine Plan Revision N: …". A later redraft, for example after a Rejection, is the Agent's own.
- **Superseded** Refine Plan Revisions keep their numbers, and new ones number on from them. `quarry show SITE N --refine-plan` prints one. `quarry open SITE --refine-plan N` walks its Terrain read-only, with every act refused.
- **A Brief change** is a human act, recorded in history; `brief.json` stays the Brief the Site was created with. After Approval it records a Reopen first.
- **After "needs Reopen"** nothing is changed. Reopening keeps your request in the Checkpoint #1 page's Edit Request box, and you send it yourself.
- **An Edit Request's answer** may hand back a choice it did not change with that choice's Reason, even one a human wrote. A human Reason on a changed choice is refused.

## Acceptance criteria

- [x] Reopen marks the Refine Plan and Terrain Superseded; Export from them is refused, and they remain viewable
- [x] A Brief edit after Approval triggers a Reopen
- [x] The touched-Zone set is correct for a move, a resize, an overlap gained and an overlap lost (tested)
- [x] Cut Paths (issue 13) are carried forward like Zones: one is touched if it was edited or overlaps the edited shape (tested)
- [x] Untouched Zones' values are carried verbatim with source Reasons; the carried plan still requires Approval
- [x] There is no operation that changes Terrain except through a Blockout or Refine Plan Revision
- [x] An Edit Request that the current stage can satisfy yields a new Revision; one that needs a Blockout-owned property at Checkpoint #2 yields "needs Reopen: <property>" and an offer to Reopen (tested with the fake Agent)
- [x] Edit Requests are available on both pages and from the CLI

## Blocked by

- `04-checkpoint-1-page.md`
- `05-checkpoint-2.md`
- `06-live-agent.md`
