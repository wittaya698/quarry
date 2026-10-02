from quarry.blockout import Blockout, Landmark, Path, Reason
from quarry.brief import Brief
from quarry.checks import run_checks

AI = Reason("ai", "test")


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

    [result] = run_checks(brief, blockout)

    assert brief.walk_speed == 1.4
    assert result.check == "walk spawn→lighthouse"
    assert result.target == 100
    assert result.measured == 100
    assert result.passed


def test_walk_outside_tolerance_misses():
    brief, blockout = straight(140, {"time": 120, "tolerance": 0.1})

    [result] = run_checks(brief, blockout)

    assert result.measured == 100
    assert not result.passed


def test_walk_target_given_as_distance_is_measured_in_metres():
    brief, blockout = straight(140, {"distance": 150, "tolerance": 0.1})

    [result] = run_checks(brief, blockout)

    assert result.check == "walk spawn→lighthouse"
    assert result.unit == "m"
    assert result.target == 150
    assert result.measured == 140
    assert result.passed
