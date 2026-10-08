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
