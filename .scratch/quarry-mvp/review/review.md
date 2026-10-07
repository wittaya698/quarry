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
