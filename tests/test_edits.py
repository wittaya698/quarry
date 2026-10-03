import pytest

from quarry.agent import FakeAgent
from quarry.blockout import Blockout, Reason, Zone
from quarry.brief import Brief
from quarry.identity import AGENT, Automated, Human
from quarry.edits import EditError
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


@pytest.fixture
def site(tmp_path):
    site = Site.create(tmp_path / "island", Brief.from_dict(ISLAND))
    site.draft(FakeAgent())
    return site


def landmark(site, name):
    return next(l for l in site.current_revision.blockout.landmarks if l.name == name)


def path(site, start, end):
    return next(p for p in site.current_revision.blockout.paths if (p.start, p.end) == (start, end))


def test_moving_a_landmark_makes_a_new_revision_where_the_landmark_and_its_paths_are_yours(site):
    before = site.current_revision.blockout

    site.edit(1, {"move_landmark": "village", "to": [250, 200]}, by=ALICE)

    assert site.current_revision.number == 2
    village = landmark(site, "village")
    assert village.position == (250, 200)
    assert village.reason.author == "human" and "by you" in village.reason.text
    trail = path(site, "spawn", "village")
    assert trail.points[-1] == (250, 200)
    assert trail.reason.author == "human"
    untouched = [l for l in before.landmarks if l.name != "village"] + [path(site, "spawn", "lighthouse")]
    assert all(element.reason.author == "ai" for element in untouched)
    assert path(site, "spawn", "lighthouse") == next(p for p in before.paths if p.end == "lighthouse")
    assert site.revision(1).blockout == before


def test_checks_re_measure_the_edited_revision(site):
    walk = "walk spawn→village"
    assert not {r.check: r for r in site.checks()}[walk].passed
    x, y = landmark(site, "spawn").position

    site.edit(1, {"move_landmark": "village", "to": [x, y + 84]}, by=ALICE)  # 84 m ≈ 60 s at 1.4 m/s

    result = {r.check: r for r in site.checks()}[walk]
    assert result.measured == pytest.approx(60)
    assert result.passed


def test_a_zone_can_be_moved_resized_raised_and_given_a_new_combine_mode(site):
    site.edit(1, {"zone": "rise", "center": [180, 210], "radius": 50}, by=ALICE)
    site.edit(2, {"zone": "rise", "height": 4, "combine": "max"}, by=ALICE)

    [rise] = site.current_revision.blockout.zones
    assert (rise.center, rise.radius, rise.height, rise.combine) == ((180, 210), 50, 4, "max")
    assert rise.reason.author == "human"
    assert {r.check: r for r in site.checks()}["reading gentle hills"].measured < 10  # lower, wider-spread rise
    assert all(l.reason.author == "ai" for l in site.current_revision.blockout.landmarks)


class Fixed:
    """An Agent that always drafts the same Blockout."""

    def __init__(self, blockout):
        self.blockout = blockout

    def draft_blockout(self, brief, rejection_note=None):
        return self.blockout


@pytest.fixture
def overlapping(tmp_path):
    ai = Reason("ai", "test")
    hill = Zone("hill", (100, 100), 50, 10, "flat", "add", ai)
    pond = Zone("pond", (120, 100), 50, -2, "flat", "replace", ai)
    site = Site.create(tmp_path / "pond", Brief.from_dict({"footprint": [200, 200], "waypoints": []}))
    site.draft(Fixed(Blockout((), (), (hill, pond))))
    return site


def test_restacking_zones_changes_which_one_is_on_top(overlapping):
    from quarry.surface import surface

    overlapping.edit(1, {"stack": ["pond", "hill"]}, by=ALICE)

    blockout = overlapping.current_revision.blockout
    assert [z.name for z in blockout.zones] == ["pond", "hill"]
    assert surface(blockout).owner(110, 100) == "hill"
    assert all(z.reason.author == "human" for z in blockout.zones)


def test_a_stacking_order_must_name_every_zone_exactly_once(overlapping):
    for wrong in (["pond"], ["pond", "hill", "hill"], ["pond", "lake"]):
        with pytest.raises(EditError, match="Stacking Order"):
            overlapping.edit(1, {"stack": wrong}, by=ALICE)
    assert overlapping.current_revision.number == 1


def test_editing_a_readings_limit_changes_its_check(site):
    site.edit(1, {"reading": "gentle hills", "limit": 10}, by=ALICE)

    reading = next(r for r in site.current_revision.blockout.readings if r.phrase == "gentle hills")
    assert reading.limit == 10 and reading.reason.author == "human"
    assert reading.meaning == "no slope steeper than 10°"
    check = {r.check: r for r in site.checks()}["reading gentle hills"]
    assert check.target == 10 and not check.passed  # the rise is ~13.5°

    with pytest.raises(EditError, match="not measurable"):
        site.edit(2, {"reading": "cozy exploration", "limit": 5}, by=ALICE)


def test_an_edit_of_a_revision_that_is_no_longer_current_is_refused(site):
    site.edit(1, {"move_landmark": "village", "to": [300, 300]}, by=ALICE)

    with pytest.raises(Refused, match="Revision 2 is current"):
        site.edit(1, {"move_landmark": "village", "to": [100, 100]}, by=ALICE)
    assert landmark(site, "village").position == (300, 300)


def test_an_approved_blockout_cannot_be_edited(site):
    site.approve(1, by=ALICE, waivers={"walk spawn→village": "fine"})

    with pytest.raises(Refused, match="approved"):
        site.edit(1, {"move_landmark": "village", "to": [300, 300]}, by=ALICE)


def test_an_edit_naming_nothing_in_the_blockout_is_refused(site):
    for change in ({"move_landmark": "castle", "to": [1, 1]}, {"zone": "lake", "height": 3}, {"teleport": 1}):
        with pytest.raises(EditError):
            site.edit(1, change, by=ALICE)
    assert site.current_revision.number == 1


@pytest.mark.parametrize("caller", [AGENT, Automated("ci")])
def test_only_a_human_can_edit(site, caller):
    with pytest.raises(Refused, match="only a human can edit"):
        site.edit(1, {"move_landmark": "village", "to": [300, 300]}, by=caller)
    assert site.current_revision.number == 1


def test_an_edit_records_who_made_it_and_survives_reopening_the_site(site):
    site.edit(1, {"move_landmark": "village", "to": [300, 300]}, by=ALICE)

    reopened = Site.open(site.path)

    assert reopened.current_revision == site.current_revision
    assert reopened.current_revision.edited_by == ALICE
    assert reopened.revision(1).edited_by is None  # drafted by the Agent
