import json
from dataclasses import replace

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.identity import AGENT, Automated, Human
from quarry.site import NeedsReopen, Refused, Site
from quarry.validation import InvalidDraft

ALICE = Human("alice")

MEADOW = {"footprint": [200, 200], "waypoints": ["spawn", "cave"]}


@pytest.fixture
def done(tmp_path):
    """A Site whose Blockout and Refine Plan are both approved."""
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps(MEADOW))
    site = Site.create(tmp_path / "meadow", Brief.load(brief))
    site.draft(FakeAgent())
    site.approve(1, by=ALICE)
    site.draft_refine_plan(FakeAgent())
    site.approve_refine_plan(1, by=ALICE)
    return site


def test_reopening_supersedes_the_refine_plan_which_stays_viewable_but_never_exports(done, tmp_path):
    out = tmp_path / "meadow.glb"

    done.reopen(by=ALICE)

    assert done.checkpoint == 1 and done.approval is None
    assert done.current_refine_plan is None
    superseded = done.refine_plan(1)
    assert superseded.superseded
    assert done.superseded_terrain(1).refine_plan_revision == 1  # still viewable
    with pytest.raises(Refused, match="Refine Plan Revision 1 is Superseded"):
        done.export(out)
    assert not out.exists()


@pytest.mark.parametrize("caller", [AGENT, Automated("ci"), "alice", None])
def test_reopen_is_refused_from_a_non_human_caller(done, caller):
    with pytest.raises(Refused, match="only a human can reopen"):
        done.reopen(by=caller)

    assert done.checkpoint == "done"


def test_only_an_approved_blockout_can_be_reopened(done):
    done.reopen(by=ALICE)

    with pytest.raises(Refused, match="approved Blockout"):
        done.reopen(by=ALICE)


def test_a_reopening_is_recorded_and_survives_reopening_the_site(done):
    done.reopen(by=ALICE)

    again = Site.open(done.path)

    [reopening] = again.reopenings
    assert (reopening.revision, reopening.by) == (1, ALICE)
    assert again.checkpoint == 1 and again.refine_plan(1).superseded


def test_after_a_reopen_the_next_refine_plan_numbers_on_and_can_be_exported(done, tmp_path):
    done.reopen(by=ALICE)
    done.edit(1, {"zone": "rise", "height": 4}, by=ALICE)
    done.approve(2, by=ALICE)

    done.draft_refine_plan(FakeAgent())
    done.approve_refine_plan(2, by=ALICE)
    done.export(tmp_path / "meadow.glb")

    assert done.current_refine_plan.blockout_revision == 2
    assert done.terrain().blockout_revision == 2
    assert done.refine_plan(1).superseded and not done.refine_plan(2).superseded


def test_a_superseded_refine_plan_cannot_be_approved_edited_or_revived(done):
    done.reopen(by=ALICE)
    done.approve(1, by=ALICE)  # the same Blockout again: Checkpoint #2, but nothing current there

    with pytest.raises(Refused, match="Superseded"):
        done.approve_refine_plan(1, by=ALICE)
    with pytest.raises(Refused, match="Superseded"):
        done.edit_refine_plan(1, {"surface": "ground", "roughness": 1}, by=ALICE)
    with pytest.raises(Refused, match="Superseded"):
        done.revive_refine_plan(1)

    assert done.current_refine_plan is None


def test_changing_the_brief_after_approval_reopens_the_blockout(done):
    longer = Brief.from_dict({**MEADOW, "max_walkable_slope": 20})

    done.edit_brief(longer, by=ALICE)

    assert done.brief.max_walkable_slope == 20
    assert done.checkpoint == 1 and done.refine_plan(1).superseded
    [reopening] = done.reopenings
    assert reopening.by == ALICE
    again = Site.open(done.path)
    assert again.brief == longer and again.checkpoint == 1


def test_changing_the_brief_before_approval_reopens_nothing(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps(MEADOW))
    site = Site.create(tmp_path / "meadow", Brief.load(brief))
    site.draft(FakeAgent())

    site.edit_brief(Brief.from_dict({**MEADOW, "mood": "gentle"}), by=ALICE)

    assert site.brief.mood == "gentle" and site.reopenings == []
    assert site.current_revision.number == 1  # the Draft stays, measured against the new Brief


@pytest.mark.parametrize("caller", [AGENT, Automated("ci")])
def test_only_a_human_can_change_the_brief(done, caller):
    with pytest.raises(Refused, match="only a human"):
        done.edit_brief(Brief.from_dict(MEADOW), by=caller)

    assert done.checkpoint == "done"


@pytest.fixture
def yours(tmp_path):
    """Approved through Refine Plan Revision 2, a human edit the Agent would never draft."""
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps(MEADOW))
    site = Site.create(tmp_path / "meadow", Brief.load(brief))
    site.draft(FakeAgent())
    site.approve(1, by=ALICE)
    site.draft_refine_plan(FakeAgent())
    site.edit_refine_plan(1, {"surface": "rise", "roughness": 3}, by=ALICE)
    site.edit_refine_plan(2, {"surface": "ground", "seed": 77}, by=ALICE)
    site.approve_refine_plan(3, by=ALICE)
    site.reopen(by=ALICE)
    return site


def test_the_next_refine_plan_carries_untouched_values_verbatim_naming_their_revision(yours):
    yours.edit(1, {"move_landmark": "cave", "to": [20, 20]}, by=ALICE)  # its Pad never touches the rise
    yours.approve(2, by=ALICE)

    yours.draft_refine_plan(FakeAgent())

    carried = {s.surface: s for s in yours.current_refine_plan.plan.surfaces}
    old = {s.surface: s for s in yours.refine_plan(3).plan.surfaces}
    for name in ("ground", "rise"):
        assert carried[name].reason.text == f"carried from Refine Plan Revision 3: {old[name].reason.text}"
        assert replace(carried[name], reason=old[name].reason) == old[name]
    assert yours.refine_plan_approval is None  # carried, but still to be approved


def test_a_touched_zone_is_drafted_afresh(yours):
    yours.edit(1, {"zone": "rise", "height": 4}, by=ALICE)
    yours.approve(2, by=ALICE)

    yours.draft_refine_plan(FakeAgent())

    carried = {s.surface: s for s in yours.current_refine_plan.plan.surfaces}
    assert carried["rise"].roughness == 0.2 and carried["rise"].reason.author == "ai"  # the Agent's own
    assert carried["ground"].seed == 77  # the ground is always carried


@pytest.fixture
def drafted(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps(MEADOW))
    site = Site.create(tmp_path / "meadow", Brief.load(brief))
    site.draft(FakeAgent())
    return site


def test_an_edit_request_at_checkpoint_1_answers_with_a_new_blockout_revision(drafted):
    before = drafted.current_revision.blockout.zones[0]

    answer = drafted.request_edit("make the rise less steep", FakeAgent())

    revision = drafted.current_revision
    assert answer == revision and revision.number == 2
    assert revision.request == "make the rise less steep"
    [rise] = revision.blockout.zones
    assert rise.height < before.height and rise.reason.author == "ai"
    assert Site.open(drafted.path).current_revision.request == "make the rise less steep"


@pytest.fixture
def refining(drafted):
    drafted.approve(1, by=ALICE)
    drafted.draft_refine_plan(FakeAgent())
    return drafted


def test_an_edit_request_the_refine_plan_can_satisfy_answers_with_a_new_refine_plan_revision(refining):
    before = {s.surface: s for s in refining.current_refine_plan.plan.surfaces}["rise"]

    answer = refining.request_edit("make the rise less steep", FakeAgent())

    assert answer == refining.current_refine_plan and answer.number == 2
    assert answer.request == "make the rise less steep"
    rise = {s.surface: s for s in answer.plan.surfaces}["rise"]
    assert rise.falloff_width > before.falloff_width and rise.reason.author == "ai"
    assert refining.current_revision.number == 1  # the approved Blockout is untouched


def test_an_edit_request_needing_a_blockout_property_at_checkpoint_2_names_it_and_changes_nothing(refining):
    history = (refining.path / "history.jsonl").read_text()

    answer = refining.request_edit("make the rise lower", FakeAgent())

    assert isinstance(answer, NeedsReopen)
    assert answer.property == "rise height" and answer.reason
    assert str(answer).startswith("needs Reopen: rise height")
    assert (refining.path / "history.jsonl").read_text() == history  # never applied silently
    assert refining.checkpoint == 2 and refining.current_refine_plan.number == 1


class Answers:
    """An Agent that answers every Edit Request at Checkpoint #2 with `output`."""

    def __init__(self, output):
        self.output = output

    def edit_refine_plan(self, brief, blockout, plan, request):
        return self.output


def plan_setting(refining, **trespass):
    plan = refining.current_refine_plan.plan.to_dict()
    plan["surfaces"][1].update(trespass)
    return plan


@pytest.mark.parametrize("output", [
    lambda site: {"plan": plan_setting(site, height=2), "needs_reopen": None},  # the Blockout's
    lambda site: {"plan": plan_setting(site, approve=True), "needs_reopen": None},  # a human act
    lambda site: {"plan": None, "needs_reopen": None},
    lambda site: {"plan": site.current_refine_plan.plan.to_dict(), "needs_reopen": {"property": "x", "reason": "y"}},
    lambda site: {"plan": None, "needs_reopen": {"property": " ", "reason": "too steep"}},
    lambda site: site.current_refine_plan.plan.to_dict(),  # a bare plan, not an answer
])
def test_an_edit_request_answer_that_breaks_a_rule_is_refused_whole(refining, output):
    history = (refining.path / "history.jsonl").read_text()

    with pytest.raises(InvalidDraft):
        refining.request_edit("make the rise less steep", Answers(output(refining)))

    assert (refining.path / "history.jsonl").read_text() == history


def test_an_edit_request_is_refused_once_its_stage_is_approved(done):
    with pytest.raises(Refused, match="Refine Plan is approved"):
        done.request_edit("make the rise less steep", FakeAgent())


def test_an_edit_request_needs_words(drafted):
    with pytest.raises(Refused, match="needs words"):
        drafted.request_edit("  ", FakeAgent())


def test_terrain_only_ever_changes_through_a_blockout_or_refine_plan_revision(yours, tmp_path):
    """Every way back — Reopen, a Brief change, Edit Requests at both Checkpoints —
    leaves history holding Revisions and human acts only: no entry writes Terrain."""
    yours.request_edit("make the rise less steep", FakeAgent())
    yours.approve(2, by=ALICE)
    yours.draft_refine_plan(FakeAgent())
    yours.request_edit("make the rise less steep", FakeAgent())
    yours.request_edit("make the rise lower", FakeAgent())
    yours.edit_brief(Brief.from_dict({**MEADOW, "mood": "calm"}), by=ALICE)

    entries = [json.loads(line) for line in (yours.path / "history.jsonl").read_text().splitlines()]

    assert {e["kind"] for e in entries} == {"revision", "approval", "reopen", "brief"}
    assert not any("terrain" in key for e in entries for key in e)
    assert not [name for name in dir(yours) if "terrain" in name and not name.startswith("_")
                and name not in ("terrain", "terrain_checks", "superseded_terrain")]


def test_an_edit_request_keeps_your_own_edits_and_their_reasons(drafted):
    drafted.edit(1, {"move_landmark": "cave", "to": [40, 60]}, by=ALICE)

    drafted.request_edit("make the rise less steep", FakeAgent())

    cave = {l.name: l for l in drafted.current_revision.blockout.landmarks}["cave"]
    assert cave.position == (40, 60) and cave.reason.author == "human"


class Rewrites:
    """An Agent that answers a Checkpoint #1 Edit Request by passing off its own change as yours."""

    def edit_blockout(self, brief, blockout, request):
        output = blockout.to_dict()
        output["zones"][0].update(height=1, reason={"author": "human", "text": "moved by you"})
        return output


def test_an_edit_request_answer_may_not_put_a_human_reason_on_a_change(drafted):
    with pytest.raises(InvalidDraft, match="Reason from the AI"):
        drafted.request_edit("make the rise less steep", Rewrites())

    assert drafted.current_revision.number == 1
