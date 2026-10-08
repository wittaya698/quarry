import json
from pathlib import Path

from quarry.brief import Brief, brief_check


def brief(footprint, *targets, waypoints=("spawn", "cave")):
    return Brief.from_dict({"footprint": footprint, "waypoints": list(waypoints), "walk_targets": list(targets)})


def test_a_walk_target_naming_an_undefined_waypoint_is_a_problem():
    problems = brief_check(brief([200, 200], {"from": "spawn", "to": "lighthouse", "time": 60}))

    assert len(problems) == 1
    assert "lighthouse" in problems[0]


# The longest route a 100 × 100 m footprint can hold without crossing itself,
# 4 m corridors climbing at the 30° Max Walkable Slope: 2500 m / cos 30° ≈ 2887 m,
# which is about 2062 s at the 1.4 m/s Walk Speed.


def test_a_walk_target_too_long_to_fit_in_the_footprint_is_a_problem():
    problems = brief_check(brief([100, 100], {"from": "spawn", "to": "cave", "time": 3600}))

    assert len(problems) == 1
    assert "walk spawn→cave" in problems[0] and "footprint" in problems[0]


def test_a_hard_but_possible_brief_passes():
    winding = brief([100, 100], {"from": "spawn", "to": "cave", "time": 1800})
    far = brief([100, 100], {"from": "spawn", "to": "cave", "distance": 2800})

    assert brief_check(winding) == []
    assert brief_check(far) == []


def test_a_walk_target_can_be_marked_no_shortcut_and_is_not_by_default():
    marked = brief([200, 200], {"from": "spawn", "to": "cave", "time": 60, "no_shortcut": True})
    unmarked = brief([200, 200], {"from": "spawn", "to": "cave", "time": 60})

    assert marked.walk_targets[0].no_shortcut
    assert not unmarked.walk_targets[0].no_shortcut
    assert Brief.from_dict(marked.to_dict()) == marked
    assert "no_shortcut" not in unmarked.to_dict()["walk_targets"][0]  # older Briefs read back unchanged


LONG_CLIMB = json.loads((Path(__file__).parent.parent / "examples/briefs/long-climb.json").read_text())


def long_climb(spring_to_summit):
    targets = [
        {**t, "time": spring_to_summit} if (t["from"], t["to"]) == ("spring", "summit") else t
        for t in LONG_CLIMB["walk_targets"]
    ]
    return Brief.from_dict({**LONG_CLIMB, "walk_targets": targets})


def test_a_forced_walk_that_a_chain_of_other_walk_targets_undercuts_is_a_problem():
    # camp→spring at most 0:22, then spring→summit at most 5:30: 5:52, under camp→summit's 9:30 floor.
    problems = brief_check(long_climb(300))

    assert problems == [
        "walk camp→summit is marked no Shortcut, but camp→spring→summit may take only 5:52, under its 9:30 floor"
    ]


def test_the_corrected_long_climb_brief_passes():
    assert brief_check(Brief.from_dict(LONG_CLIMB)) == []


def chain(no_shortcut, *legs):
    walks = [{"from": "camp", "to": "summit", "time": 600, "tolerance": 0.05, "no_shortcut": no_shortcut}]
    walks += [{"from": a, "to": b, "time": 10, "tolerance": 0.1} for a, b in legs]
    return brief([200, 200], *walks, waypoints=("camp", "spring", "summit"))


def test_a_chain_that_only_runs_the_wrong_way_never_refuses_a_forced_walk():
    assert brief_check(chain(True, ("summit", "spring"), ("spring", "camp"))) == []
    assert brief_check(chain(True, ("camp", "spring"), ("summit", "spring"))) == []
    assert len(brief_check(chain(True, ("camp", "spring"), ("spring", "summit")))) == 1


def test_an_unmarked_walk_target_is_never_refused_for_a_chain():
    assert brief_check(chain(False, ("camp", "spring"), ("spring", "summit"))) == []
