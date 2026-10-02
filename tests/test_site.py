import json
from datetime import datetime, timezone

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.identity import AGENT, Automated, Human
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


NO_TARGETS = {"footprint": [200, 200], "waypoints": ["spawn", "cave"]}


def brief_file(tmp_path, data=ISLAND):
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def site(tmp_path):
    return Site.create(tmp_path / "island", Brief.load(brief_file(tmp_path)))


def test_drafting_places_every_waypoint_and_draws_a_path_per_walk_target(site):
    site.draft(FakeAgent())

    revision = site.current_revision
    assert revision.number == 1
    blockout = revision.blockout
    assert sorted(l.name for l in blockout.landmarks) == ["lighthouse", "spawn", "village"]
    assert sorted((p.start, p.end) for p in blockout.paths) == [
        ("spawn", "lighthouse"),
        ("spawn", "village"),
    ]
    for choice in [*blockout.landmarks, *blockout.paths]:
        assert choice.reason.author == "ai"
        assert choice.reason.text


@pytest.fixture
def meadow(tmp_path):
    """A Site the FakeAgent drafts with no Checks, so nothing misses."""
    return Site.create(tmp_path / "meadow", Brief.load(brief_file(tmp_path, NO_TARGETS)))


def test_approving_the_current_revision_records_who_and_when(meadow):
    meadow.draft(FakeAgent())
    before = datetime.now(timezone.utc)

    meadow.approve(1, by=ALICE)

    approval = meadow.approval
    assert approval.revision == 1
    assert approval.by == ALICE
    assert before <= approval.at <= datetime.now(timezone.utc)
    assert meadow.checkpoint == 2


def test_approving_a_revision_that_is_no_longer_current_is_refused(meadow):
    meadow.draft(FakeAgent())
    meadow.draft(FakeAgent())

    with pytest.raises(Refused, match="Revision 2 is current"):
        meadow.approve(1, by=ALICE)

    assert meadow.approval is None


def test_approval_is_refused_while_a_missed_check_has_no_waiver(site):
    site.draft(FakeAgent())
    missed = [r.check for r in site.checks() if not r.passed]
    assert missed == ["walk spawn→village"]

    with pytest.raises(Refused, match="walk spawn→village"):
        site.approve(1, by=ALICE)
    with pytest.raises(Refused, match="walk spawn→village"):
        site.approve(1, by=ALICE, waivers={"walk spawn→lighthouse": "not the miss"})

    site.approve(1, by=ALICE, waivers={"walk spawn→village": "village can be farther"})
    assert site.approval.waivers == {"walk spawn→village": "village can be farther"}


def test_rejection_requires_a_note(meadow):
    meadow.draft(FakeAgent())

    with pytest.raises(Refused, match="note"):
        meadow.reject(1, by=ALICE, note="  ")

    assert meadow.rejections == []


def test_a_rejected_revision_is_kept_and_can_be_revived_as_a_new_revision(meadow):
    meadow.draft(FakeAgent())
    meadow.reject(1, by=ALICE, note="too flat")

    [rejection] = meadow.rejections
    assert (rejection.revision, rejection.note, rejection.by) == (1, "too flat", ALICE)
    with pytest.raises(Refused, match="rejected"):
        meadow.approve(1, by=ALICE)

    meadow.revive(1)

    revived = meadow.current_revision
    assert revived.number == 2
    assert revived.revived_from == 1
    assert revived.blockout == meadow.revision(1).blockout
    meadow.approve(2, by=ALICE)


NOT_HUMAN = [AGENT, Automated("ci"), "alice", None]


@pytest.mark.parametrize("caller", NOT_HUMAN)
def test_approval_and_waivers_are_refused_from_a_non_human_caller(site, caller):
    site.draft(FakeAgent())

    with pytest.raises(Refused, match="only a human"):
        site.approve(1, by=caller, waivers={"walk spawn→village": "fine"})

    assert site.approval is None


@pytest.mark.parametrize("caller", NOT_HUMAN)
def test_rejection_is_refused_from_a_non_human_caller(site, caller):
    site.draft(FakeAgent())

    with pytest.raises(Refused, match="only a human"):
        site.reject(1, by=caller, note="too flat")

    assert site.rejections == []


def test_history_survives_reopening_the_site(site):
    site.draft(FakeAgent())
    site.reject(1, by=ALICE, note="too flat")
    site.draft(FakeAgent())
    site.approve(2, by=ALICE, waivers={"walk spawn→village": "village can be farther"})

    reopened = Site.open(site.path)

    assert reopened.brief == site.brief
    assert reopened.revision(1) == site.revision(1)
    assert reopened.current_revision == site.current_revision
    assert reopened.rejections == site.rejections
    assert reopened.approval == site.approval
    assert reopened.checkpoint == 2


def test_a_variant_site_from_a_copied_brief_has_independent_history(site, tmp_path):
    site.draft(FakeAgent())
    site.reject(1, by=ALICE, note="too flat")

    variant = Site.create(tmp_path / "island-rainy", site.brief)
    variant.draft(FakeAgent())
    variant.approve(1, by=ALICE, waivers={"walk spawn→village": "fine here"})

    original = Site.open(site.path)
    assert variant.brief == original.brief
    assert original.approval is None
    assert [r.revision for r in original.rejections] == [1]
    assert variant.rejections == []
    assert Site.open(variant.path).approval.revision == 1


def test_creating_a_site_over_an_existing_one_is_refused(site):
    with pytest.raises(FileExistsError):
        Site.create(site.path, site.brief)


def test_no_new_blockout_revision_after_approval(meadow):
    meadow.draft(FakeAgent())
    meadow.approve(1, by=ALICE)

    with pytest.raises(Refused, match="approved"):
        meadow.draft(FakeAgent())
    with pytest.raises(Refused, match="approved"):
        meadow.revive(1)

    assert meadow.current_revision.number == 1


@pytest.mark.parametrize("number", [0, 2, -1])
def test_acts_on_a_revision_that_does_not_exist_are_refused(meadow, number):
    meadow.draft(FakeAgent())

    with pytest.raises(Refused, match="no Revision"):
        meadow.revision(number)
    with pytest.raises(Refused, match="no Revision"):
        meadow.reject(number, by=ALICE, note="too flat")
    with pytest.raises(Refused, match="no Revision"):
        meadow.revive(number)
    with pytest.raises(Refused, match="no Revision"):
        meadow.approve(number, by=ALICE)


def test_approving_before_any_draft_is_refused(meadow):
    with pytest.raises(Refused, match="no Revision"):
        meadow.approve(1, by=ALICE)


def test_a_brief_that_fails_the_brief_check_cannot_be_drafted(tmp_path):
    impossible = {**NO_TARGETS, "walk_targets": [{"from": "spawn", "to": "summit", "time": 60}]}
    site = Site.create(tmp_path / "broken", Brief.from_dict(impossible))

    assert site.brief_problems() == ["walk spawn→summit names summit, which is not a Waypoint"]
    with pytest.raises(Refused, match="Brief Check"):
        site.draft(FakeAgent())
    assert site.current_revision is None


def test_a_blockout_that_misses_a_target_is_still_drafted_and_owns_the_miss(site):
    brief_before = (site.path / "brief.json").read_text()

    site.draft(FakeAgent())

    blockout = site.current_revision.blockout
    [village] = [p for p in blockout.paths if p.end == "village"]
    assert "misses the 60 s target" in village.reason.text
    [lighthouse] = [p for p in blockout.paths if p.end == "lighthouse"]
    assert "misses" not in lighthouse.reason.text
    assert (site.path / "brief.json").read_text() == brief_before
    assert Site.open(site.path).brief == site.brief


def test_the_fake_agent_reads_the_mood_and_shapes_the_ground(site):
    site.draft(FakeAgent())

    blockout = site.current_revision.blockout
    readings = {r.phrase: r for r in blockout.readings}
    assert readings["gentle hills"].measure == "max_slope"
    assert readings["cozy exploration"].measure is None
    assert blockout.zones and all(z.reason.text for z in blockout.zones)
    checks = {r.check: r for r in site.checks()}
    assert checks["reading gentle hills"].passed
    assert all(checks[f"pad {name}"].passed for name in site.brief.waypoints)
