# 08 — Going back: Reopen, carry-forward and Edit Requests

Status: ready-for-agent

## Parent

`.scratch/quarry-mvp/PRD.md`

## What to build

Make reversal and plain-language changes work end to end.
- **Reopen:** the developer can Reopen an approved Blockout from the CLI or either page. The current Refine Plan and Terrain become **Superseded**: still viewable, never exportable. Changing the Brief after Approval Reopens the Blockout.
- **Carry-forward:** after the new Blockout is approved, the next Refine Plan is pre-filled with untouched Zones' values copied verbatim, each with a Reason naming its source Revision. A Zone is touched if it was edited or overlaps the edited Zone's old or new shape. The pre-filled plan still needs its own Approval. Terrain can never be patched directly.
- **Edit Requests:** at either Checkpoint the developer types an Edit Request. The Agent answers with a new Revision of the current stage, or, when the change needs a property the Blockout owns (asked at Checkpoint #2), with "needs Reopen", naming the property and offering a Reopen. The change is never applied silently.

## Acceptance criteria

- [ ] Reopen marks the Refine Plan and Terrain Superseded; Export from them is refused, and they remain viewable
- [ ] A Brief edit after Approval triggers a Reopen
- [ ] The touched-Zone set is correct for a move, a resize, an overlap gained and an overlap lost (tested)
- [ ] Untouched Zones' values are carried verbatim with source Reasons; the carried plan still requires Approval
- [ ] There is no operation that changes Terrain except through a Blockout or Refine Plan Revision
- [ ] An Edit Request that the current stage can satisfy yields a new Revision; one that needs a Blockout-owned property at Checkpoint #2 yields "needs Reopen: <property>" and an offer to Reopen (tested with the fake Agent)
- [ ] Edit Requests are available on both pages and from the CLI

## Blocked by

- `04-checkpoint-1-page.md`
- `05-checkpoint-2.md`
- `06-live-agent.md`
