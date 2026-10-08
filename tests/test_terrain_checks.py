import math

import pytest

from quarry.agent import FakeAgent
from quarry.blockout import Blockout, Landmark, Path, Reason, Zone
from quarry.brief import Brief
from quarry.export import read_glb
from quarry.identity import Human
from quarry.refine import RefinePlan, Refinement
from quarry.site import Refused, Site
from quarry.surface import surface

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


def spiral_climb():
    """A 40 m dome too steep to climb (≈38° against 25°), with a Cut Path winding
    1.5 times round it from camp at its foot to the summit on its crown."""
    ai = Reason("ai", "test")
    turns = [(-math.pi / 2 + 3 * math.pi * i / 60, 90 * (1 - i / 60)) for i in range(61)]
    points = tuple((100 + r * math.cos(a), 100 + r * math.sin(a)) for a, r in turns)
    return Blockout(
        landmarks=(Landmark("camp", points[0], ai), Landmark("summit", (100, 100), ai)),
        paths=(Path("camp", "summit", points, ai, cut=True, width=8),),
        zones=(Zone("hill", (100, 100), 80, 40, "dome", "add", ai),),
    )


class Drafts:
    """An Agent that drafts a fixed Blockout, and refines like the fake."""

    def __init__(self, blockout):
        self.blockout = blockout

    def draft_blockout(self, brief, rejection_note=None, shortcuts=()):
        return self.blockout.to_dict()

    def draft_refine_plan(self, brief, blockout, rejection_note=None, shortcuts=()):
        return FakeAgent().draft_refine_plan(brief, blockout)


def test_a_cut_path_forces_the_climb_at_both_checkpoints(tmp_path):
    brief = Brief.from_dict({
        "footprint": [200, 200], "waypoints": ["camp", "summit"], "max_walkable_slope": 25,
        "walk_targets": [{"from": "camp", "to": "summit", "time": 300, "tolerance": 0.1, "no_shortcut": True}],
    })
    site = Site.create(tmp_path / "spiral", brief)
    agent = Drafts(spiral_climb())
    site.draft(agent)
    on_blockout = by_name(site.checks())
    site.approve(1, by=ALICE, waivers={c: "test" for c, r in on_blockout.items() if not r.passed})
    site.draft_refine_plan(agent)
    on_terrain = by_name(site.terrain_checks())

    for checks in (on_blockout, on_terrain):
        assert checks["slope camp→summit"].passed, checks["slope camp→summit"].measured
        assert checks["shortcut camp→summit"].passed, checks["shortcut camp→summit"].measured
        assert checks["pad summit"].passed and checks["pad camp"].passed


def test_a_cut_paths_own_refinement_wins_along_its_strip(tmp_path):
    site = Site.create(tmp_path / "spiral", Brief.from_dict({"footprint": [200, 200], "waypoints": []}))
    agent = Drafts(spiral_climb())
    site.draft(agent)
    site.approve(1, by=ALICE)
    site.draft_refine_plan(agent)
    plan = {s.surface: s for s in site.current_refine_plan.plan.surfaces}
    terrain = site.terrain()

    # The spiral passes (100, 160) half a turn after camp; (100, 150) is the dome beside it.
    on_strip, beside = terrain.vegetation[160 // 2][100 // 2], terrain.vegetation[150 // 2][100 // 2]
    assert on_strip == plan["camp→summit"].vegetation_density
    assert beside == plan["hill"].vegetation_density != on_strip


def test_the_exports_collision_carries_a_cut_paths_strip(tmp_path):
    site = Site.create(tmp_path / "spiral", Brief.from_dict({"footprint": [200, 200], "waypoints": []}))
    agent = Drafts(spiral_climb())
    site.draft(agent)
    site.approve(1, by=ALICE)
    site.draft_refine_plan(agent)
    site.approve_refine_plan(1, by=ALICE)
    site.export(tmp_path / "spiral.glb")

    collision = {(x, z): y for x, y, z in read_glb(tmp_path / "spiral.glb")["terrain-colonly"].positions}
    terrain = site.terrain()
    # On the strip at (100, 160), the trail's graded height, not the dome's.
    assert collision[(100, 160)] == pytest.approx(terrain.height(100, 160), abs=1e-4)
    dome = 40 * (1 + math.cos(math.pi * 60 / 80)) / 2  # the hill alone, 60 m from its centre
    assert abs(collision[(100, 160)] - dome) > 1


class Smooth(Drafts):
    """Drafts a fixed Blockout; refines every surface with a 6 m smooth falloff and no roughness."""

    def draft_refine_plan(self, brief, blockout, rejection_note=None, shortcuts=()):
        names = ["ground", *(z.name for z in blockout.zones)]
        return RefinePlan(tuple(
            Refinement(name, "smooth", 6.0, 0.0, 1, 0.3, Reason("ai", "test")) for name in names
        )).to_dict()


def test_a_pad_on_ground_already_level_changes_no_height(tmp_path):
    # The terrace is level out to 9 m (its 6 m falloff straddles its 12 m rim),
    # exactly the reach of a 6 m Pad and its margin; beyond, it falls away.
    ai = Reason("ai", "test")
    terrace = Blockout(
        landmarks=(Landmark("bench", (100, 100), ai),),
        paths=(),
        zones=(Zone("terrace", (100, 100), 12, 3, "flat", "add", ai),),
    )
    site = Site.create(tmp_path / "terrace", Brief.from_dict({"footprint": [200, 200], "waypoints": ["bench"]}))
    agent = Smooth(terrace)
    site.draft(agent)
    site.approve(1, by=ALICE)
    site.draft_refine_plan(agent)
    shape = surface(terrace, site.current_refine_plan.plan)
    terrain = site.terrain()

    for r, row in enumerate(terrain.heights):
        for c, height in enumerate(row):
            x, y = c * terrain.spacing, r * terrain.spacing
            assert height == pytest.approx(shape.height(x, y), abs=1e-9), (x, y)
