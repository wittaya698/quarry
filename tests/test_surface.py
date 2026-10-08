import pytest

from quarry.blockout import Blockout, Landmark, Path, Reason, Zone
from quarry.refine import RefinePlan, Refinement
from quarry.surface import surface

AI = Reason("ai", "test")


def zones(*zones):
    return surface(Blockout(landmarks=(), paths=(), zones=zones))


def plateau(name, x, height, combine):
    """A flat disc of radius 50 centred on (x, 0)."""
    return Zone(name, (x, 0), 50, height, "flat", combine, AI)


def test_an_add_zone_stacks_its_height_on_the_zone_below():
    ground = zones(plateau("hill", 0, 10, "add"), plateau("tower", 20, 5, "add"))

    assert ground.height(10, 0) == 15


def test_a_max_zone_keeps_whichever_is_higher():
    lower = zones(plateau("hill", 0, 10, "add"), plateau("tower", 20, 5, "max"))
    higher = zones(plateau("hill", 0, 10, "add"), plateau("tower", 20, 14, "max"))

    assert lower.height(10, 0) == 10
    assert higher.height(10, 0) == 14


def test_a_replace_zone_sets_its_own_height_even_when_lower():
    ground = zones(plateau("hill", 0, 10, "add"), plateau("pond", 20, -2, "replace"))

    assert ground.height(10, 0) == -2
    assert ground.height(-40, 0) == 10  # the hill beyond the pond is untouched


def test_stacking_order_decides_which_zone_combines_onto_which():
    hill, pond = plateau("hill", 0, 10, "add"), plateau("pond", 20, -2, "replace")

    assert zones(hill, pond).height(10, 0) == -2
    assert zones(pond, hill).height(10, 0) == 8


def test_the_owner_of_a_point_is_its_topmost_zone_never_a_blend():
    ground = zones(plateau("hill", 0, 10, "add"), plateau("pond", 20, -2, "replace"))

    assert ground.owner(10, 0) == "pond"  # inside both: the upper one alone
    assert ground.owner(-40, 0) == "hill"
    assert ground.owner(200, 0) == "ground"


def test_a_dome_rises_smoothly_from_its_rim_to_full_height_at_its_centre():
    ground = zones(Zone("knoll", (0, 0), 40, 12, "dome", "add", AI))

    assert ground.height(0, 0) == 12
    assert abs(ground.height(20, 0) - 6) < 1e-9
    assert abs(ground.height(39.99, 0)) < 1e-3
    assert ground.height(41, 0) == 0


def refined(zone, profile, falloff):
    def refinement(name, width):
        return Refinement(name, profile, width, 0.0, 1, 0.0, AI)

    plan = RefinePlan((refinement("ground", 0.0), refinement(zone.name, falloff)))
    return surface(Blockout(landmarks=(), paths=(), zones=(zone,)), plan)


def test_a_refined_zone_edge_ramps_over_its_falloff_width_instead_of_stepping():
    mesa = Zone("mesa", (0, 0), 50, 10, "flat", "add", AI)

    hard = zones(mesa)
    ramp = refined(mesa, "linear", 20)

    assert (hard.height(49, 0), hard.height(51, 0)) == (10, 0)
    assert ramp.height(39, 0) == 10 and ramp.height(61, 0) == 0
    assert ramp.height(50, 0) == pytest.approx(5)
    assert ramp.height(45, 0) == pytest.approx(7.5)  # linear: an even 26.6° ramp


def test_the_slope_profile_shapes_the_ramp():
    mesa = Zone("mesa", (0, 0), 50, 10, "flat", "add", AI)

    linear, smooth, steep = (refined(mesa, p, 20) for p in ("linear", "smooth", "steep"))

    assert linear.height(50, 0) == smooth.height(50, 0) == pytest.approx(5)  # each keeps the Zone's size
    assert smooth.height(58, 0) < linear.height(58, 0)  # eases in at the foot
    assert steep.height(58, 0) < smooth.height(58, 0)  # steep packs the climb into the middle
    assert steep.height(42, 0) > smooth.height(42, 0)


def climb(cut):
    """Camp at the foot of a 40 m dome, the summit on its crown, joined by a
    straight Path 90 m long, 8 m wide if cut; both Pads are 6 m in radius."""
    hill = Zone("hill", (100, 100), 80, 40, "dome", "add", AI)
    landmarks = (Landmark("camp", (100, 10), AI), Landmark("summit", (100, 100), AI))
    path = Path("camp", "summit", ((100, 10), (100, 100)), AI, cut=cut, width=8 if cut else None)
    return surface(Blockout(landmarks, (path,), (hill,))), surface(Blockout(landmarks, (), (hill,)))


def test_a_cut_path_rises_evenly_between_its_pads_whatever_the_zones_beneath_do():
    ground, _ = climb(cut=True)

    # Level across each Pad, at the height the Zones give its Landmark (0 m and 40 m),
    # then 40 m over the 78 m between the Pads' edges.
    assert ground.height(100, 12) == pytest.approx(0)
    assert ground.height(100, 98) == pytest.approx(40)
    for y in (30, 55, 80):
        assert ground.height(100, y) == pytest.approx(40 * (y - 16) / 78)
        assert ground.height(103.5, y) == pytest.approx(40 * (y - 16) / 78)  # across the strip, too


def test_a_cut_paths_banks_are_sheer_on_the_blockout():
    ground, zones_only = climb(cut=True)

    inside, outside = ground.height(103.9, 55), ground.height(104.1, 55)

    assert outside == pytest.approx(zones_only.height(104.1, 55))  # beyond the strip, the dome
    assert inside - outside > 3  # a step, not a slope


def test_a_path_that_is_not_cut_never_changes_the_ground():
    ground, zones_only = climb(cut=False)

    for x, y in ((100, 12), (100, 55), (103.5, 80), (110, 55)):
        assert ground.height(x, y) == zones_only.height(x, y)
    assert ground.owner(100, 55) == "hill"


def test_a_refine_plan_eases_a_cut_paths_banks_outward_and_leaves_its_grade_exact():
    hill = Zone("hill", (100, 100), 80, 40, "dome", "add", AI)
    landmarks = (Landmark("camp", (100, 10), AI), Landmark("summit", (100, 100), AI))
    path = Path("camp", "summit", ((100, 10), (100, 100)), AI, cut=True, width=8)
    blockout = Blockout(landmarks, (path,), (hill,))
    def refined(name, falloff):
        return Refinement(name, "smooth", falloff, 0.0, 1, 0.5, AI)
    plan = RefinePlan((refined("ground", 0), refined("hill", 0), refined("camp→summit", 8)))
    ground, zones_only = surface(blockout, plan), surface(Blockout(landmarks, (), (hill,)))

    assert ground.height(103.9, 55) == pytest.approx(40 * (55 - 16) / 78)  # the whole strip keeps its grade
    assert abs(ground.height(104.1, 55) - ground.height(103.9, 55)) < 0.1  # no step at its edge
    assert ground.height(112.1, 55) == pytest.approx(zones_only.height(112.1, 55))  # the dome again past the falloff
