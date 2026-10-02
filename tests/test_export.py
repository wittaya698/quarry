import json

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.export import ExportError, read_glb, verify_export
from quarry.identity import Human
from quarry.site import Refused, Site

ALICE = Human("alice")


@pytest.fixture
def meadow(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps({"footprint": [200, 120], "waypoints": ["spawn", "cave"]}))
    return Site.create(tmp_path / "meadow", Brief.load(brief))


def test_export_is_refused_until_the_refine_plan_is_approved(meadow, tmp_path):
    out = tmp_path / "meadow.glb"

    with pytest.raises(Refused, match="approved Refine Plan"):
        meadow.export(out)
    meadow.draft(FakeAgent())
    meadow.approve(1, by=ALICE)
    meadow.draft_refine_plan(FakeAgent())
    with pytest.raises(Refused, match="approved Refine Plan"):
        meadow.export(out)

    assert not out.exists()


@pytest.fixture
def refined(meadow):
    """A Site whose Blockout and Refine Plan are both approved."""
    meadow.draft(FakeAgent())
    meadow.approve(1, by=ALICE)
    meadow.draft_refine_plan(FakeAgent())
    meadow.approve_refine_plan(1, by=ALICE)
    return meadow


def test_exported_glb_reimports_with_godot_collision_matching_the_terrain(refined, tmp_path):
    out = tmp_path / "meadow.glb"

    refined.export(out)
    nodes = read_glb(out)

    assert {"terrain", "terrain-colonly"} <= set(nodes)
    terrain = refined.terrain()
    heights = [h for row in terrain.heights for h in row]
    collision = nodes["terrain-colonly"]
    xs, ys, zs = zip(*collision.positions)
    # glTF is Y-up: the footprint's x runs along X, its y along Z, height along Y.
    assert (min(xs), max(xs)) == (0, 200)
    assert (min(zs), max(zs)) == (0, 120)
    assert min(ys) == pytest.approx(min(heights), abs=1e-4)
    assert max(ys) == pytest.approx(max(heights), abs=1e-4)
    assert collision.triangles and all(normal_y > 0 for normal_y in collision.facing_up())


def test_an_export_that_does_not_match_its_terrain_fails_verification(refined, tmp_path):
    out = tmp_path / "meadow.glb"
    refined.export(out)
    verify_export(refined.terrain(), out)

    wider = Site.create(tmp_path / "wider", Brief.from_dict({"footprint": [240, 120], "waypoints": ["a"]}))
    wider.draft(FakeAgent())
    wider.approve(1, by=ALICE)
    wider.draft_refine_plan(FakeAgent())

    with pytest.raises(ExportError, match="extent"):
        verify_export(wider.terrain(), out)
