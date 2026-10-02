import math

from dataclasses import replace

from quarry.blockout import Blockout, Landmark, Path, Reading, Reason
from quarry.brief import Brief
from quarry.checks import run_checks

AI = Reason("ai", "test")


class Incline:
    """Any surface will do for Checks: this one climbs at a fixed angle along x."""

    def __init__(self, degrees):
        self.rise = math.tan(math.radians(degrees))

    def height(self, x, y):
        return x * self.rise


def by_name(results):
    return {r.check: r for r in results}


def straight(length, target):
    brief = Brief.from_dict(
        {
            "footprint": [400, 400],
            "waypoints": ["spawn", "lighthouse"],
            "walk_targets": [{"from": "spawn", "to": "lighthouse", **target}],
        }
    )
    blockout = Blockout(
        landmarks=(Landmark("spawn", (0, 0), AI), Landmark("lighthouse", (length, 0), AI)),
        paths=(Path("spawn", "lighthouse", ((0, 0), (length, 0)), AI),),
    )
    return brief, blockout


def test_straight_path_on_flat_ground_walks_in_length_over_walk_speed():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})

    result = by_name(run_checks(brief, blockout))["walk spawn→lighthouse"]

    assert brief.walk_speed == 1.4
    assert result.check == "walk spawn→lighthouse"
    assert result.target == 100
    assert result.measured == 100
    assert result.passed


def test_walk_outside_tolerance_misses():
    brief, blockout = straight(140, {"time": 120, "tolerance": 0.1})

    result = by_name(run_checks(brief, blockout))["walk spawn→lighthouse"]

    assert result.measured == 100
    assert not result.passed


def test_walk_target_given_as_distance_is_measured_in_metres():
    brief, blockout = straight(140, {"distance": 150, "tolerance": 0.1})

    result = by_name(run_checks(brief, blockout))["walk spawn→lighthouse"]

    assert result.check == "walk spawn→lighthouse"
    assert result.unit == "m"
    assert result.target == 150
    assert result.measured == 140
    assert result.passed


def test_a_path_up_a_known_slope_walks_its_length_along_the_ground():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})

    walk = by_name(run_checks(brief, blockout, Incline(20)))["walk spawn→lighthouse"]

    assert math.isclose(walk.measured, 140 / math.cos(math.radians(20)) / 1.4)


def test_a_path_steeper_than_the_max_walkable_slope_misses():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})

    gentle = by_name(run_checks(brief, blockout, Incline(20)))["slope spawn→lighthouse"]
    steep = by_name(run_checks(brief, blockout, Incline(35)))["slope spawn→lighthouse"]

    assert gentle.target == brief.max_walkable_slope == 30
    assert math.isclose(gentle.measured, 20) and gentle.passed
    assert math.isclose(steep.measured, 35) and not steep.passed


def test_a_measurable_reading_becomes_a_check_and_an_unmeasurable_one_does_not():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})
    gentle = Reading("gentle hills", "no slope steeper than 15°", "max_slope", 15, AI)
    cozy = Reading("cozy", "small, sheltered spaces", None, None, AI)
    blockout = replace(blockout, readings=(gentle, cozy))

    on_gentle = by_name(run_checks(brief, blockout, Incline(10)))
    on_steep = by_name(run_checks(brief, blockout, Incline(20)))

    assert on_gentle["reading gentle hills"].target == 15
    assert math.isclose(on_gentle["reading gentle hills"].measured, 10)
    assert on_gentle["reading gentle hills"].passed
    assert not on_steep["reading gentle hills"].passed
    assert not any("cozy" in name for name in on_gentle)


def test_every_landmark_has_a_pad_that_must_be_flat():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})

    on_flat = by_name(run_checks(brief, blockout))
    on_slope = by_name(run_checks(brief, blockout, Incline(10)))

    for landmark in ("spawn", "lighthouse"):
        assert on_flat[f"pad {landmark}"].passed
        assert on_flat[f"pad {landmark}"].target == 3  # degrees
        assert math.isclose(on_slope[f"pad {landmark}"].measured, 10)
        assert not on_slope[f"pad {landmark}"].passed


def test_a_decorative_path_is_not_measured():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})
    lookout = Landmark("lookout", (0, 100), AI, ai_chosen=True)
    trail = Path("spawn", "lookout", ((0, 0), (0, 100)), AI, decorative=True)
    blockout = replace(blockout, landmarks=blockout.landmarks + (lookout,), paths=blockout.paths + (trail,))

    names = set(by_name(run_checks(brief, blockout, Incline(40))))

    assert "slope spawn→lighthouse" in names
    assert not any("spawn→lookout" in name for name in names)
    assert "pad lookout" in names  # an AI-chosen Landmark still stands on a Pad


def test_a_reading_can_cap_the_highest_ground():
    brief, blockout = straight(140, {"time": 100, "tolerance": 0.1})
    low = Reading("low dunes", "nothing higher than 30 m", "max_height", 30, AI)
    blockout = replace(blockout, readings=(low,))

    on_gentle = by_name(run_checks(brief, blockout, Incline(4)))  # 400 m × tan 4° ≈ 28 m
    on_steep = by_name(run_checks(brief, blockout, Incline(5)))  # ≈ 35 m

    assert on_gentle["reading low dunes"].unit == "m"
    assert on_gentle["reading low dunes"].passed
    assert not on_steep["reading low dunes"].passed
