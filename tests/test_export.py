import math
import re
from dataclasses import replace
import json

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.export import ExportError, export_glb, godot_name, read_glb, verify_export
from quarry.identity import Human
from quarry.site import Refused, Site

ALICE = Human("alice")


@pytest.fixture
def meadow(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps({
        "footprint": [200, 120], "waypoints": ["spawn", "cave"],
        "walk_targets": [{"from": "spawn", "to": "cave", "distance": 80, "tolerance": 0.2}],
    }))
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
    nodes = read_glb(out).meshes

    assert {"terrain", "terrain_collision-colonly"} <= set(nodes)
    terrain = refined.terrain()
    heights = [h for row in terrain.heights for h in row]
    collision = nodes["terrain_collision-colonly"]
    xs, ys, zs = zip(*collision.positions)
    # glTF is Y-up: the footprint's x runs along X, its y along Z, height along Y.
    assert (min(xs), max(xs)) == (0, 200)
    assert (min(zs), max(zs)) == (0, 120)
    assert min(ys) == pytest.approx(min(heights), abs=1e-4)
    assert max(ys) == pytest.approx(max(heights), abs=1e-4)
    assert collision.triangles and all(normal_y > 0 for normal_y in collision.facing_up())


def test_godot_names_the_collision_body_terrain_collision_beside_the_terrain_mesh(refined, tmp_path):
    out = tmp_path / "meadow.glb"

    refined.export(out)

    # Godot strips the hint, keeps the rest as the node's name, and acts on the hint
    top = [godot_name(name) for name in read_glb(out).children[""]]
    assert top == [("terrain", None), ("terrain_collision", "colonly"), ("landmarks", None), ("paths", None)]


def test_an_export_where_godot_would_give_two_nodes_one_name_fails_verification(refined, tmp_path, monkeypatch):
    out = tmp_path / "meadow.glb"
    blockout = refined.revision(refined.approval.revision).blockout
    # the name issue 10 found: stripped of -colonly it is the display mesh's name,
    # so Godot renamed the collision body @StaticBody3D@19798, new on every import
    monkeypatch.setattr("quarry.export.COLLISION", "terrain-colonly")
    export_glb(refined.terrain(), blockout, out)

    with pytest.raises(ExportError, match="Godot would name both terrain-colonly and terrain"):
        verify_export(refined.terrain(), blockout, out)


def _renamed(blockout, old, new):
    name = lambda n: new if n == old else n
    return replace(
        blockout,
        landmarks=tuple(replace(l, name=name(l.name)) for l in blockout.landmarks),
        paths=tuple(replace(p, start=name(p.start), end=name(p.end)) for p in blockout.paths),
    )


# Godot 4.7 turned a curve ending in -col into collision, and dropped an anchor ending in _noimp
@pytest.mark.parametrize("landmark", ["cave-col", "cave_noimp", "cave-wheel", "cave$colonly"])
def test_an_export_where_godot_would_act_on_a_landmarks_name_fails_verification(refined, tmp_path, landmark):
    out = tmp_path / "meadow.glb"
    blockout = _renamed(refined.revision(refined.approval.revision).blockout, "cave", landmark)
    export_glb(refined.terrain(), blockout, out)

    with pytest.raises(ExportError, match=re.escape(f"Godot would read {landmark} as")):
        verify_export(refined.terrain(), blockout, out)


def test_an_export_that_does_not_match_its_terrain_fails_verification(refined, tmp_path):
    out = tmp_path / "meadow.glb"
    refined.export(out)
    verify_export(refined.terrain(), refined.revision(1).blockout, out)

    wider = Site.create(tmp_path / "wider", Brief.from_dict({"footprint": [240, 120], "waypoints": ["a"]}))
    wider.draft(FakeAgent())
    wider.approve(1, by=ALICE)
    wider.draft_refine_plan(FakeAgent())

    with pytest.raises(ExportError, match="extent"):
        verify_export(wider.terrain(), refined.revision(1).blockout, out)


def test_each_landmark_is_an_empty_anchor_standing_on_its_pad(refined, tmp_path):
    out = tmp_path / "meadow.glb"

    refined.export(out)
    anchors = read_glb(out).anchors

    terrain = refined.terrain()
    landmarks = refined.revision(refined.approval.revision).blockout.landmarks
    assert set(anchors) == {l.name for l in landmarks}
    for landmark in landmarks:
        x, height, y = anchors[landmark.name]
        assert (x, y) == pytest.approx(landmark.position, abs=1e-4)
        assert height == pytest.approx(terrain.height(*landmark.position), abs=1e-4)


def test_each_path_is_a_curve_laid_along_the_ground(refined, tmp_path):
    out = tmp_path / "meadow.glb"

    refined.export(out)
    curves = read_glb(out).curves

    terrain = refined.terrain()
    paths = refined.revision(refined.approval.revision).blockout.paths
    assert set(curves) == {f"{p.start}→{p.end}" for p in paths}
    for path in paths:
        curve = curves[f"{path.start}→{path.end}"]
        assert (curve[0][0], curve[0][2]) == pytest.approx(path.points[0], abs=1e-4)
        assert (curve[-1][0], curve[-1][2]) == pytest.approx(path.points[-1], abs=1e-4)
        for x, height, y in curve:
            assert height == pytest.approx(terrain.height(x, y), abs=1e-3)
        # close enough together that the curve rides over the rise, not through it
        assert all(math.dist(a, b) <= terrain.spacing + 1e-6 for a, b in zip(curve, curve[1:]))


def test_vegetation_is_density_data_on_the_terrain_node(refined, tmp_path):
    out = tmp_path / "meadow.glb"

    refined.export(out)
    vegetation = read_glb(out).metadata["terrain"]["vegetation_density"]

    terrain = refined.terrain()
    assert vegetation["spacing"] == terrain.spacing
    assert vegetation["rows"] == len(terrain.heights) and vegetation["columns"] == len(terrain.heights[0])
    # row by row from the footprint's (0, 0) corner, x fastest: Godot reads it as node metadata
    assert vegetation["density"] == [d for row in terrain.vegetation for d in row]


def test_an_export_whose_terrain_was_changed_without_a_revision_fails_verification(refined, tmp_path):
    out = tmp_path / "meadow.glb"
    terrain = refined.terrain()
    blockout = refined.revision(refined.approval.revision).blockout
    # one sample raised 2 m, inside the Terrain's own height range so no extent gives it away
    heights = [list(row) for row in terrain.heights]
    heights[10][10] += 2
    export_glb(replace(terrain, heights=tuple(map(tuple, heights))), blockout, out)

    with pytest.raises(ExportError, match="height"):
        verify_export(terrain, blockout, out)


def _moved_off_its_pad(blockout):
    first = blockout.landmarks[0]
    moved = replace(first, position=(first.position[0] + 10, first.position[1]))
    return replace(blockout, landmarks=(moved, *blockout.landmarks[1:]))


def _rerouted(blockout):
    first = blockout.paths[0]
    (ax, ay), (bx, by) = first.points[0], first.points[-1]
    detour = replace(first, points=(first.points[0], ((ax + bx) / 2, (ay + by) / 2 + 15), first.points[-1]))
    return replace(blockout, paths=(detour, *blockout.paths[1:]))


@pytest.mark.parametrize("corrupt, complaint", [
    (_moved_off_its_pad, "anchor spawn"),
    (lambda b: replace(b, landmarks=b.landmarks[1:]), "no anchor for spawn"),
    (_rerouted, "curve spawn→cave"),
    (lambda b: replace(b, paths=()), "no curve for spawn→cave"),
])
def test_an_export_whose_anchors_or_curves_are_wrong_fails_verification(refined, tmp_path, corrupt, complaint):
    out = tmp_path / "meadow.glb"
    terrain = refined.terrain()
    blockout = refined.revision(refined.approval.revision).blockout
    export_glb(terrain, corrupt(blockout), out)

    with pytest.raises(ExportError, match=complaint):
        verify_export(terrain, blockout, out)
