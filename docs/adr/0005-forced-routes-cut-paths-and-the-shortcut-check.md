# Forced routes: Cut Paths and the Shortcut Check

A Walk Target used to promise only how long its Path is, and the player could walk anywhere. In review, the long-climb sample met its 10-minute camp→summit target with a spiral Path, but the smooth dome under it could be walked straight up in 74 s. Nothing in a Blockout could prevent that. A hill steep enough to block the climb also blocks the Path, because Zones are only discs.

We decided:
- a Brief may mark a Walk Target **no Shortcut**;
- a **Shortcut Check** then looks for any faster walkable route anywhere on the ground;
- the AI prevents one with a **Cut Path**, a Path that grades its own strip of ground at an even rise between its Landmarks, so a hill around it can be steeper than anyone can climb.

## Considered Options

- **Every Walk Target checked for Shortcuts.** Rejected: most walks are meant to be optional routes over open ground. For example, cozy-forest's curving cabin→glade Path is longer than the straight line, by design. Only the Brief's author knows which walks must be forced.
- **Shortcuts symmetric** (no step steeper than the limit, up or down, like the Path slope Check). Rejected: in the exported game a player can drop down any slope. A Check that ignored drops would pass routes the game lets players cut. A Shortcut is one-way: it never climbs steeper than the Max Walkable Slope, but it may drop. So a downhill walk can rarely be forced, and that is the honest answer.
- **New Zone kinds (ramps, ledges) or barrier rings with gaps** to build the route. Rejected: they duplicate the Path as a second statement of where the route goes, and rings can only make tiers, not a smooth climb.
- **Every Path cuts its grade.** Rejected: an ordinary Path over a hill would trench through it instead of following it, changing every existing Blockout.

## Consequences

- A Path can now change the ground, but only when it is a Cut Path. The Blockout owns which Paths are cut and how wide each strip is (at least 4 m). This extends ADR-0003's "where and how big".
- At Checkpoint #1 a Cut Path's banks are sheer. The Refine Plan refines each Cut Path as a surface of its own, above every Zone, and may ease its banks. If easing makes a bank climbable, the Shortcut Check on the Terrain catches it, as every Check runs at both Checkpoints.
- A Shortcut miss carries the Shortcut's route. Both Checkpoint pages draw it, and it goes into the next Draft's input.
- Reopen carry-forward treats a Cut Path like a Zone: it is touched if it was edited or overlaps the edited shape.
