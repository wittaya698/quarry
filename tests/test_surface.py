import pytest

from quarry.blockout import Blockout, Reason, Zone
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
    from quarry.refine import RefinePlan, Refinement

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
