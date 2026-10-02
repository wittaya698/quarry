# Checkpoint acts are human-only, enforced in the core

Approval, Waiver, Rejection and Reopen can be performed only by a human, and the core — not the UI — refuses them from the agent or any automated caller; there is no auto-approve setting, including for tests or CI. We chose core enforcement over a UI convention because Quarry's founding promise is that no Draft passes without a human checkpoint, and a promise that one script or flag can bypass is a convention, not a guarantee. Every such act records who performed it and when.

## Consequences

- Tests that need an approved Blockout construct one through the core's human-act path with a test identity, never by bypassing it.
- MVP assumes one human per Site; recorded identity leaves room for multiple reviewers later.
