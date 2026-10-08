# Draft quality review (issue 07)

Sample Briefs: `examples/briefs/`. Sites (untracked): `.scratch/quarry-mvp/review/sites/<name>`.
Model `claude-opus-5-5`, effort `high`, `--agent subscription`.

## Round 1 — Blockouts, prompts as merged in issue 11 (2026-10-07)

### What the Checks found

| Sample | Walks | Slopes | Pads | Readings |
|---|---|---|---|---|
| cozy-forest | 2/2 pass | 2/2 pass | 3/3 | 2 measured pass, 2 unmeasured |
| coastal-cliffs | 2/2 pass | **0/2** (37.5°, 50.6° vs 35°) | 3/3 | 2 unmeasured |
| tight-courtyard | 2/2 pass | **1/2** (fountain→terrace 56.3° vs 30°) | 3/3 | **"flat" misses its own 8° ceiling** (46.7°) |
| long-climb | 3/3 pass | **2/3** (spring→summit 25.6° vs 25°) | 3/3 | 1 measured pass, 2 unmeasured |

### Reasons the Checks contradict

Every slope miss comes with a Reason claiming the Path is gentle. None owns the miss.

- coastal-cliffs landing→cliff_top: "no slope above about 21°", but the Check measures 37.5°.
- coastal-cliffs cliff_top→lookout: "slopes of 13° or less", but the Check measures 50.6°.
- tight-courtyard fountain→terrace: "climbs gently onto the 1.5 m terrace … well under the 30° limit", but a `flat` Zone's edge is a step (56.3°).
- tight-courtyard "flat": "leaving room for the gentle rise of about 5°", but the Check measures 46.7°.

The model can't compute the slopes it reports, so it guesses, and it guesses low. The walk times all pass, so the lengths it reports are reliable.

### Reviewer verdicts

For each sample, record accept or reject, with a reason, for its Readings, placements and Reasons.

**All samples, Reasons (2026-10-08):** reject. *"Describe what the trail looks like, not slope numbers you can't compute."*

#### cozy-forest
- Readings:
- Placements:
- Reasons:

#### coastal-cliffs
- Readings:
- Placements:
- Reasons:

#### tight-courtyard
- Readings:
- Placements:
- Reasons:

#### long-climb
- Readings:
- Placements:
- Reasons:

## Round 2 — Blockouts, after the "no guessed numbers" rule (2026-10-08)

Prompt change: Reasons describe the ground and the trail and never state a slope, gradient or angle. A length or walk time worked out from a Path's points is still allowed. The same rule went into the Refine Plan prompt, whose example Reason had quoted a walk time.

Sites: `.scratch/quarry-mvp/review/sites/round2/<name>`.

| Sample | Walks | Slopes | Pads | Readings |
|---|---|---|---|---|
| cozy-forest | 2/2 | 2/2 | 3/3 | **"gentle" misses its own 10° ceiling** (12.2°) |
| coastal-cliffs | 2/2 | **1/2** (landing→cliff_top 78°) | 3/3 | 2 unmeasured |
| tight-courtyard | **1/2** (0:22 vs 0:20 ±10%) | **1/2** (fountain→terrace 58.6°) | 3/3 | 1 pass, 3 unmeasured |
| long-climb | 3/3 | 3/3 | **2/3** (summit 6°) | 3 unmeasured |

**Fixed:** no Reason states a slope number any more.

**Still untrue, now in words:** the Paths that miss on slope are described as reaching high ground "by the side ramp" (cliffs, 78°) or "up the low ramp onto the terrace" (courtyard, 58.6°). A Blockout has no ramps. A `flat` Zone's rim is a sheer step until the Refine Plan's falloff softens it, and the model doesn't know that.

**New oddity:** the courtyard drew a decorative gate→gate loop to trace the wall.

## Round 3 — Blockouts, after teaching the ground model (2026-10-08)

Prompt change: the Blockout prompt now states how Checkpoint #1's ground is built and measured:
- the dome formula and its steepest slope, with the h / r limits for common slope ceilings;
- flat, max and replace rims are sheer steps until the Refine Plan eases them;
- a step must be owned in the Reason and never called a ramp;
- the tilt of a Pad on a dome's crown;
- what a max_slope or max_height Reading measures, so the AI sets only ceilings its own layout meets.

Sites: `.scratch/quarry-mvp/review/sites/round3/<name>`.

| Sample | Walks | Slopes | Pads | Readings |
|---|---|---|---|---|
| cozy-forest | 2/2 | 2/2 | 3/3 | 2/2 measured pass |
| coastal-cliffs | 2/2 | 2/2 | 3/3 | 2 unmeasured |
| tight-courtyard | 2/2 | 2/2 | 3/3 | 2/2 measured pass |
| long-climb | 3/3 | 3/3 | 3/3 | 1/1 measured pass |

Every Check passes on all four samples, and every Reason matches what the Checks measured.
- **courtyard:** the AI built a real ramp. A low dome under the terrace, with a flat top cut in by `replace` at exactly the dome's height at that radius (1.5 m), so the Path climbs at 11.9° with no step.
- **cliffs:** the cliffs come from the cove's `replace` rim and no Path crosses them. The steep Reading is left unmeasured, which is honest: "steep" is a minimum, not a ceiling.

Still for the reviewer: do the layouts read as the moods?

**Reviewer:** approved all four Round 3 Blockouts as they are (2026-10-08).

## Refine Plans, Round 1 — on the approved Round 3 Blockouts (2026-10-08)

| Sample | Checks on the Terrain |
|---|---|
| cozy-forest | all pass |
| coastal-cliffs | all pass; the cove keeps a 1 m `steep` falloff, so the cliffs stay sheer |
| long-climb | all pass |
| tight-courtyard | **"flat" misses its 15° ceiling** (17.6°); fountain→terrace steepens from 11.9° to 16.7°, still passing |

**Why the courtyard misses.** The Refine Plan isn't the cause; the Terrain Builder is.
- The refined Surface peaks at 13.0°. The Terrain peaks at 17.6°, 14 m from the terrace's centre.
- The Builder holds each Pad level out to its radius plus a 3 m margin (here 8 + 3 = 11 m), then eases back to the natural ground over 6 m (`_flatten_pads`, `_PAD_BLEND`).
- The terrace's flat top already ends at 11 m. So the ease squeezes the start of the ramp's descent into 6 m, and the ground gets steeper there.
- This is code behaviour. The prompt can't know it, and the Agent can't fix it.

**Reasons:** they describe the surfaces in words and quote no numbers. They still promise outcomes the model can't verify, though: "climbs it evenly without being steepened" for the courtyard ramp, which did steepen.

**Reviewer, long-climb (2026-10-08):** reject. *"I shouldn't be able to climb straight to the peak. I must at least walk circular around the mountain."*
- On the Terrain, a straight line from camp to the summit is walkable: its steepest point is 21.1° against the 25° limit, and it takes 74 s against the 10:00 target.
- The Blockout has no way to prevent this. A hill steep enough to block the climb would also block the spiral Path, because Zones are discs and a Path doesn't shape the ground.
- Fixing it needs a design change, not just a prompt change.

## Shortcut Check on long-climb (issue 12, 2026-10-08)

`examples/briefs/long-climb.json` now marks camp→summit no Shortcut. The approved Round 3 Blockout, checked against it (on a copy of the Site, with the new Brief), misses:

| Measured on | shortcut camp→summit | every other Check |
|---|---|---|
| Blockout | **1:17** against ≥ 9:30, straight from camp up the hill to the summit | pass |
| Terrain (Refine Plan Revision 1) | **1:17**, the same way | pass |

Both Checkpoint pages draw the route as a red dashed line. A Shortcut climbs only onto ground no steeper than the Max Walkable Slope in its steepest direction, so switchbacks across a steep face don't count (decided while building the Check; recorded in ADR-0005). The walk view now obeys the same rule. Closing the Shortcut needs Cut Paths (issue 13).

## Round 4 — long-climb with Cut Paths (issue 13, 2026-10-08)

Site: `.scratch/quarry-mvp/review/sites/round4/long-climb`, drafted live after the Cut Path prompt.

- The AI raised a hill too steep to climb (80 m on a 70 m radius) and wound a 5 m Cut Path almost four times round it, with turns about 15 m apart.
- **shortcut camp→summit passes:** the fastest walkable route is the trail itself, at 10:01 against the 9:30 floor. Every slope and Pad Check passes.
- **walk spring→summit misses** (10:19 against 5:00), because the sample Brief contradicts itself. A 5:00 spring→summit would make camp→spring→summit about 5:20, a Shortcut on the forced climb. The AI saw this, routed spring→summit back through camp, and owned the miss in its Reason.
- Follow-ups: the sample Brief's spring→summit target is now 10:00 ±10%. Issue 15 has the Brief Check refuse such Briefs before drafting. The round4 Site keeps the old Brief, so this miss needs a Waiver.

**Reviewer:** approved the Round 4 Blockout, waiving walk spring→summit (2026-10-08).

**Refine Plan, Round 4 (live).** The Cut Path is almost bare (roughness 0.05 m) with 1 m bank easing; the hill's flank keeps a `steep` 4 m falloff. On the Terrain:
- **shortcut camp→summit passes** at 10:01 against the 9:30 floor.
- Every other Check passes except the waived spring→summit miss, which needs a fresh Waiver here.
- The trail's steepest point rises from 5.5° to 12.5°. This is Terrain resolution, not the plan: heights are stored every 2 m, so some points on the 5 m trail's centreline borrow height from a sample on the bank. Still well under 25°.

Still for the reviewer: walk it, and confirm the summit can't be climbed straight up.

**Reviewer, Round 4 walk (2026-10-09):** *"I get stuck at this too often."* At a corner of the trail the walker stopped against a wall. Diagnosis: Terrain is sampled every 2 m, and the samples nearest each bank read as too steep. That left the 5 m trail a walkable lane only 1–3 m wide, jagged on the diagonal. A simulated walker following the trail stalled at 387 of 835 m, whichever way it slid. With an 8 m trail, or with 1 m Terrain, it walks end to end. The reviewer chose an **8 m minimum Cut Path** (ADR-0005).

## Round 5 — long-climb, 8 m Cut Paths and the fixed Brief (2026-10-09)

Site: `.scratch/quarry-mvp/review/sites/round5/long-climb`. The Brief now asks 10:00 ±10% for spring→summit.

**Every Check passes.** shortcut camp→summit measures 10:25 against the 9:30 floor.
- The crag is a 150 m dome on an 86 m radius, cut off flat at 80 m.
- The 8 m Cut Path crosses the meadow from camp on a raised causeway, winds twice round the crag with its loops 16 m apart, and ends in a trench across the flat top.
- The Reason works out the inside-of-the-bends route (about 580 s), following the new prompt line.
