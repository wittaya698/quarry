import json

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.cli import main
from quarry.identity import Human
from quarry.site import Site

ALICE = Human("alice")

MEADOW = {"footprint": [200, 200], "waypoints": ["spawn", "cave"]}


@pytest.fixture
def at_keyboard(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("getpass.getuser", lambda: "alice")


@pytest.fixture
def done(tmp_path):
    site = Site.create(tmp_path / "meadow", Brief.from_dict(MEADOW))
    site.draft(FakeAgent())
    site.approve(1, by=ALICE)
    site.draft_refine_plan(FakeAgent())
    site.approve_refine_plan(1, by=ALICE)
    return site


def test_reopen_from_the_cli_supersedes_the_refine_plan(done, at_keyboard, capsys):
    assert main(["reopen", str(done.path)]) == 0

    out = capsys.readouterr().out
    assert "Reopened Blockout Revision 1" in out and "Refine Plan Revision 1 is Superseded" in out
    site = Site.open(done.path)
    assert site.checkpoint == 1 and site.reopenings[0].by == ALICE


def test_reopen_without_a_person_at_the_keyboard_is_refused(done, capsys):
    assert main(["reopen", str(done.path)]) == 1

    assert "only a human can reopen" in capsys.readouterr().err
    assert Site.open(done.path).checkpoint == "done"


def test_a_superseded_refine_plan_is_shown_marked_so(done, at_keyboard, capsys):
    main(["reopen", str(done.path)])

    assert main(["show", str(done.path), "1", "--refine-plan"]) == 0

    out = capsys.readouterr().out
    assert "Superseded" in out and "ground:" in out


def test_status_names_what_is_superseded(done, at_keyboard, capsys):
    main(["reopen", str(done.path)])
    capsys.readouterr()

    main(["status", str(done.path)])

    assert "Refine Plan Revision 1 Superseded" in capsys.readouterr().out


def test_changing_the_brief_from_the_cli_after_approval_reopens(done, at_keyboard, tmp_path, capsys):
    brief = tmp_path / "steeper.json"
    brief.write_text(json.dumps({**MEADOW, "max_walkable_slope": 35}))

    assert main(["brief", str(done.path), "--brief", str(brief)]) == 0

    assert "Reopened" in capsys.readouterr().out
    site = Site.open(done.path)
    assert site.brief.max_walkable_slope == 35 and site.checkpoint == 1


def test_an_edit_request_from_the_cli_drafts_a_revision(tmp_path, capsys):
    site = Site.create(tmp_path / "meadow", Brief.from_dict(MEADOW))
    site.draft(FakeAgent())

    assert main(["request", str(site.path), "make the rise less steep", "--agent", "fake"]) == 0

    assert "drafted Revision 2 for your Edit Request" in capsys.readouterr().out
    assert Site.open(site.path).current_revision.request == "make the rise less steep"


def test_an_edit_request_needing_a_reopen_says_so_and_offers_the_command(tmp_path, capsys):
    site = Site.create(tmp_path / "meadow", Brief.from_dict(MEADOW))
    site.draft(FakeAgent())
    site.approve(1, by=ALICE)
    site.draft_refine_plan(FakeAgent())

    assert main(["request", str(site.path), "make the rise lower", "--agent", "fake"]) == 0

    out = capsys.readouterr().out
    assert "needs Reopen: rise height" in out and f"quarry reopen {site.path}" in out
    assert Site.open(site.path).current_refine_plan.number == 1


def test_export_with_tscn_writes_a_scene_that_instances_the_glb(done, tmp_path, capsys):
    out = tmp_path / "godot" / "meadow.glb"
    out.parent.mkdir()

    assert main(["export", str(done.path), str(out), "--tscn"]) == 0

    scene = (tmp_path / "godot" / "meadow.tscn").read_text()
    # a path relative to the scene, so the pair works wherever it lands in a Godot project
    assert '[ext_resource type="PackedScene" path="meadow.glb" id="1_glb"]' in scene
    assert '[node name="meadow" type="Node3D"]' in scene
    assert '[node name="terrain" parent="." instance=ExtResource("1_glb")]' in scene
    assert "meadow.tscn" in capsys.readouterr().out


def test_export_writes_no_tscn_unless_asked(done, tmp_path):
    main(["export", str(done.path), str(tmp_path / "meadow.glb")])

    assert not (tmp_path / "meadow.tscn").exists()
