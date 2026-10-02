import json

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.checks import run_checks
from quarry.surface import surface
from quarry.identity import AGENT, Automated, Human
from quarry.site import Refused, Site

ALICE = Human("alice")

MEADOW = {"footprint": [200, 200], "waypoints": ["spawn", "cave"]}


@pytest.fixture
def meadow(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps(MEADOW))
    return Site.create(tmp_path / "meadow", Brief.load(brief))


def test_a_refine_plan_cannot_be_drafted_on_an_unapproved_blockout(meadow):
    with pytest.raises(Refused, match="approved Blockout"):
        meadow.draft_refine_plan(FakeAgent())

    meadow.draft(FakeAgent())
    with pytest.raises(Refused, match="approved Blockout"):
        meadow.draft_refine_plan(FakeAgent())

    assert meadow.current_refine_plan is None


@pytest.fixture
def approved(meadow):
    """A Site whose Blockout is approved, ready for a Refine Plan."""
    meadow.draft(FakeAgent())
    meadow.approve(1, by=ALICE)
    return meadow


def test_a_refine_plan_on_an_approved_blockout_refines_every_surface_with_a_reason(approved):
    approved.draft_refine_plan(FakeAgent())

    revision = approved.current_refine_plan
    assert revision.number == 1
    zones = [z.name for z in approved.current_revision.blockout.zones]
    assert [s.surface for s in revision.plan.surfaces] == ["ground", *zones]
    for refinement in revision.plan.surfaces:
        assert refinement.slope_profile in {"linear", "smooth", "steep"}
        assert refinement.falloff_width >= 0
        assert refinement.roughness >= 0
        assert isinstance(refinement.seed, int)
        assert 0 <= refinement.vegetation_density <= 1
        assert refinement.reason.author == "ai"
        assert refinement.reason.text


def test_the_same_blockout_and_refine_plan_always_build_byte_identical_terrain(approved, tmp_path):
    approved.draft_refine_plan(FakeAgent())

    first = approved.terrain().to_bytes()
    assert approved.terrain().to_bytes() == first
    assert Site.open(approved.path).terrain().to_bytes() == first

    reseeded = Site.create(tmp_path / "reseeded", approved.brief)
    reseeded.draft(FakeAgent())
    reseeded.approve(1, by=ALICE)
    reseeded.draft_refine_plan(FakeAgent(seed=2))
    assert reseeded.current_revision.blockout == approved.current_revision.blockout
    assert reseeded.terrain().to_bytes() != first


def test_terrain_names_the_blockout_and_refine_plan_revisions_it_was_built_from(meadow):
    meadow.draft(FakeAgent())
    meadow.draft(FakeAgent())
    meadow.approve(2, by=ALICE)
    meadow.draft_refine_plan(FakeAgent())
    meadow.draft_refine_plan(FakeAgent(seed=7))

    terrain = meadow.terrain()

    assert terrain.blockout_revision == 2
    assert terrain.refine_plan_revision == 2
    assert terrain.extent == (200, 200)


def test_approving_the_current_refine_plan_records_who_and_finishes_the_checkpoints(approved):
    approved.draft_refine_plan(FakeAgent())
    approved.draft_refine_plan(FakeAgent(seed=2))

    with pytest.raises(Refused, match="Revision 2 is current"):
        approved.approve_refine_plan(1, by=ALICE)
    approved.approve_refine_plan(2, by=ALICE)

    approval = approved.refine_plan_approval
    assert (approval.revision, approval.by) == (2, ALICE)
    assert approved.checkpoint == "done"
    assert approved.approval.revision == 1  # the Blockout's Approval is untouched


def test_a_rejected_refine_plan_needs_a_note_is_kept_and_can_be_revived(approved):
    approved.draft_refine_plan(FakeAgent())

    with pytest.raises(Refused, match="note"):
        approved.reject_refine_plan(1, by=ALICE, note=" ")
    approved.reject_refine_plan(1, by=ALICE, note="too bumpy")

    [rejection] = approved.refine_plan_rejections
    assert (rejection.revision, rejection.note, rejection.by) == (1, "too bumpy", ALICE)
    with pytest.raises(Refused, match="rejected"):
        approved.approve_refine_plan(1, by=ALICE)

    approved.revive_refine_plan(1)

    revived = approved.current_refine_plan
    assert (revived.number, revived.revived_from) == (2, 1)
    assert revived.plan == approved.refine_plan(1).plan
    approved.approve_refine_plan(2, by=ALICE)
    with pytest.raises(Refused, match="approved"):
        approved.draft_refine_plan(FakeAgent())


@pytest.mark.parametrize("caller", [AGENT, Automated("ci"), "alice", None])
def test_refine_plan_approval_and_rejection_are_refused_from_a_non_human_caller(approved, caller):
    approved.draft_refine_plan(FakeAgent())

    with pytest.raises(Refused, match="only a human"):
        approved.approve_refine_plan(1, by=caller)
    with pytest.raises(Refused, match="only a human"):
        approved.reject_refine_plan(1, by=caller, note="too bumpy")

    assert approved.refine_plan_approval is None
    assert approved.refine_plan_rejections == []


def test_refine_plan_history_survives_reopening_the_site(approved):
    approved.draft_refine_plan(FakeAgent())
    approved.reject_refine_plan(1, by=ALICE, note="too bumpy")
    approved.draft_refine_plan(FakeAgent(seed=3))
    approved.approve_refine_plan(2, by=ALICE)

    reopened = Site.open(approved.path)

    assert reopened.refine_plan(1) == approved.refine_plan(1)
    assert reopened.current_refine_plan == approved.current_refine_plan
    assert reopened.refine_plan_rejections == approved.refine_plan_rejections
    assert reopened.refine_plan_approval == approved.refine_plan_approval
    assert reopened.approval == approved.approval
    assert reopened.rejections == []
    assert reopened.checkpoint == "done"


def test_the_same_checks_run_on_the_built_terrain(tmp_path):
    across = {**MEADOW, "mood": "gentle", "walk_targets": [{"from": "spawn", "to": "cave", "time": 100}]}
    site = Site.create(tmp_path / "across", Brief.from_dict(across))
    site.draft(FakeAgent())
    site.approve(1, by=ALICE)
    site.draft_refine_plan(FakeAgent())
    blockout = site.current_revision.blockout

    on_blockout = {r.check: r for r in site.checks()}
    on_terrain = {r.check: r for r in run_checks(site.brief, blockout, site.terrain())}

    assert set(on_terrain) == set(on_blockout)
    walk = "walk spawn→cave"  # straight across the middle, over the rise
    assert on_terrain[walk].measured == pytest.approx(on_blockout[walk].measured, rel=0.03)


def test_terrain_stands_on_the_blockout_surface_with_each_samples_own_refinement(approved):
    approved.draft_refine_plan(FakeAgent())
    [rise] = approved.current_revision.blockout.zones
    refinements = {s.surface: s for s in approved.current_refine_plan.plan.surfaces}

    terrain = approved.terrain()
    coarse = surface(approved.current_revision.blockout)

    x, y = rise.center
    assert terrain.height(x, y) == pytest.approx(coarse.height(x, y), abs=refinements["rise"].roughness)
    assert coarse.height(x, y) == rise.height > 0
    column, row = round(x / terrain.spacing), round(y / terrain.spacing)
    assert terrain.vegetation[row][column] == refinements["rise"].vegetation_density
    assert terrain.vegetation[0][0] == refinements["ground"].vegetation_density
    assert refinements["rise"].vegetation_density != refinements["ground"].vegetation_density
