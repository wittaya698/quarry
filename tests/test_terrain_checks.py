import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.identity import Human
from quarry.site import Refused, Site

ALICE = Human("alice")

ISLAND = {
    "footprint": [400, 400],
    "mood": "gentle hills, cozy exploration",
    "waypoints": ["spawn", "lighthouse", "village"],
    "walk_targets": [
        {"from": "spawn", "to": "lighthouse", "time": 180, "tolerance": 0.1},
        {"from": "spawn", "to": "village", "time": 60, "tolerance": 0.1},
    ],
}
FIRST_WAIVER = {"walk spawn→village": "the village can be farther"}


@pytest.fixture
def refining(tmp_path):
    """A Site at Checkpoint #2: approved Blockout, one Refine Plan Draft."""
    site = Site.create(tmp_path / "island", Brief.from_dict(ISLAND))
    site.draft(FakeAgent())
    site.approve(1, by=ALICE, waivers=FIRST_WAIVER)
    site.draft_refine_plan(FakeAgent())
    return site


def by_name(results):
    return {r.check: r for r in results}


def test_every_blockout_check_runs_again_on_the_terrain(refining):
    on_blockout, on_terrain = by_name(refining.checks()), by_name(refining.terrain_checks())

    assert set(on_terrain) == set(on_blockout)
    walk = "walk spawn→lighthouse"
    assert on_terrain[walk].target == on_blockout[walk].target
    assert on_terrain[walk].measured != on_blockout[walk].measured  # measured on the real ground


def test_the_terrain_builder_flattens_every_pad(refining):
    on_terrain = by_name(refining.terrain_checks())

    for name in ISLAND["waypoints"]:
        pad = on_terrain[f"pad {name}"]
        assert pad.passed, f"{name} Pad measures {pad.measured:.1f}°"
        assert pad.measured < 0.5  # flattened, not merely lucky


def ground(site):
    return next(s for s in site.current_refine_plan.plan.surfaces if s.surface == "ground")


def test_editing_a_refine_plan_value_makes_a_revision_and_rebuilds_the_terrain(refining):
    first = refining.terrain()

    refining.edit_refine_plan(1, {"surface": "ground", "roughness": 3.0}, by=ALICE)

    assert refining.current_refine_plan.number == 2
    assert refining.current_refine_plan.edited_by == ALICE
    assert ground(refining).roughness == 3.0 and ground(refining).reason.author == "human"
    rise = next(s for s in refining.current_refine_plan.plan.surfaces if s.surface == "rise")
    assert rise.reason.author == "ai"
    assert refining.terrain().heights != first.heights

    refining.edit_refine_plan(2, {"surface": "ground", "roughness": 0.5}, by=ALICE)
    assert refining.terrain().heights == first.heights  # the same values build the same Terrain


@pytest.mark.parametrize(
    "change",
    [
        {"surface": "lake", "roughness": 1},
        {"surface": "ground", "roughness": -1},
        {"surface": "ground", "vegetation_density": 1.5},
        {"surface": "ground", "slope_profile": "wobbly"},
        {"surface": "ground", "height": 40},  # the Blockout owns heights
    ],
)
def test_a_refine_plan_edit_outside_its_values_is_refused(refining, change):
    from quarry.edits import EditError

    with pytest.raises(EditError):
        refining.edit_refine_plan(1, change, by=ALICE)
    assert refining.current_refine_plan.number == 1


def test_refine_plan_edits_follow_the_same_rules_as_blockout_edits(refining):
    from quarry.identity import AGENT

    with pytest.raises(Refused, match="only a human can edit"):
        refining.edit_refine_plan(1, {"surface": "ground", "roughness": 1}, by=AGENT)
    refining.edit_refine_plan(1, {"surface": "ground", "roughness": 1}, by=ALICE)
    with pytest.raises(Refused, match="Revision 2 is current"):
        refining.edit_refine_plan(1, {"surface": "ground", "roughness": 2}, by=ALICE)
    missed = {r.check: "accepted" for r in refining.terrain_checks() if not r.passed}
    refining.approve_refine_plan(2, by=ALICE, waivers=missed)
    with pytest.raises(Refused, match="approved"):
        refining.edit_refine_plan(2, {"surface": "ground", "roughness": 2}, by=ALICE)
    assert Site.open(refining.path).current_refine_plan.edited_by == ALICE


def test_a_waiver_from_checkpoint_1_does_not_cover_the_same_miss_on_the_terrain(refining):
    assert refining.approval.waivers == FIRST_WAIVER
    assert not by_name(refining.terrain_checks())["walk spawn→village"].passed

    with pytest.raises(Refused, match="no Waiver for walk spawn→village"):
        refining.approve_refine_plan(1, by=ALICE)

    refining.approve_refine_plan(1, by=ALICE, waivers={"walk spawn→village": "still fine on the real ground"})
    assert refining.refine_plan_approval.waivers == {"walk spawn→village": "still fine on the real ground"}


def test_a_path_that_passed_on_the_blockout_misses_once_refining_makes_it_steeper(refining):
    path = "slope spawn→lighthouse"
    assert by_name(refining.checks())[path].passed
    assert by_name(refining.terrain_checks())[path].passed

    refining.edit_refine_plan(1, {"surface": "ground", "roughness": 8.0}, by=ALICE)

    on_terrain = by_name(refining.terrain_checks())
    assert not on_terrain[path].passed
    assert on_terrain["walk spawn→lighthouse"].measured > by_name(refining.checks())["walk spawn→lighthouse"].measured
    assert all(on_terrain[f"pad {name}"].passed for name in ISLAND["waypoints"])  # still flattened


FORCED = {**ISLAND, "walk_targets": [{"from": "spawn", "to": "lighthouse", "time": 600, "no_shortcut": True}]}
FORCED_WAIVERS = {
    "walk spawn→lighthouse": "the straight Path is short",
    "shortcut spawn→lighthouse": "the straight line is the way",
}


@pytest.fixture
def forced(tmp_path):
    """A Site whose one walk is forced: the fake's straight Path is itself a Shortcut."""
    site = Site.create(tmp_path / "forced", Brief.from_dict(FORCED))
    site.draft(FakeAgent())
    return site


def test_a_shortcut_miss_blocks_approval_without_a_waiver(forced):
    shortcut = by_name(forced.checks())["shortcut spawn→lighthouse"]
    assert not shortcut.passed and shortcut.route

    with pytest.raises(Refused, match="shortcut spawn→lighthouse"):
        forced.approve(1, by=ALICE, waivers={"walk spawn→lighthouse": "the straight Path is short"})
    forced.approve(1, by=ALICE, waivers=FORCED_WAIVERS)


def test_the_shortcut_check_runs_again_on_the_terrain(forced):
    forced.approve(1, by=ALICE, waivers=FORCED_WAIVERS)
    forced.draft_refine_plan(FakeAgent())

    on_blockout = by_name(forced.checks())["shortcut spawn→lighthouse"]
    on_terrain = by_name(forced.terrain_checks())["shortcut spawn→lighthouse"]

    assert not on_terrain.passed and on_terrain.route
    assert on_terrain.measured != on_blockout.measured  # measured on the real ground
