import json
import math
import threading
import urllib.error
import urllib.request

import pytest

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.identity import Automated, Human
from quarry.page import serve
from quarry.site import Site

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
def island(tmp_path):
    site = Site.create(tmp_path / "island", Brief.from_dict(ISLAND))
    site.draft(FakeAgent())
    return site


def running(site, caller=ALICE, **options):
    server = serve(site.path, caller, **options)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
    return server


@pytest.fixture
def page(island):
    server = running(island, ALICE)
    yield server
    server.shutdown()


def call(server, route, body=None, token=None):
    """(status, JSON) for one request, as the page would make it."""
    token = server.token if token is None else token
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"{server.address}{route}?token={token}", data=data)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_the_page_state_carries_the_blockout_its_reasons_and_its_checks(page):
    status, state = call(page, "/api/state")

    assert status == 200
    assert state["revision"] == 1 and state["state"] == "awaiting review"
    assert state["footprint"] == [400, 400]
    blockout = state["blockout"]
    elements = blockout["landmarks"] + blockout["paths"] + blockout["zones"] + blockout["readings"]
    assert elements and all(e["reason"]["text"] for e in elements)
    checks = {c["check"]: c for c in state["checks"]}
    assert checks["walk spawn→village"]["passed"] is False
    assert {"target", "measured", "unit", "tolerance"} <= set(checks["walk spawn→village"])


def test_a_request_without_the_pages_token_is_forbidden(page):
    for route, body in (("/api/state", None), ("/api/approve", {"revision": 1, "waivers": {}})):
        status, reply = call(page, route, body, token="guess")
        assert status == 403
    assert Site.open(page.site_path).approval is None


def test_an_edit_from_the_page_makes_a_revision_and_returns_re_measured_checks(page):
    status, state = call(page, "/api/edit", {"revision": 1, "change": {"move_landmark": "village", "to": [333, 284]}})

    assert status == 200
    assert state["revision"] == 2
    village = next(l for l in state["blockout"]["landmarks"] if l["name"] == "village")
    assert village["reason"]["author"] == "human"
    assert {c["check"]: c for c in state["checks"]}["walk spawn→village"]["passed"]
    assert Site.open(page.site_path).current_revision.edited_by == ALICE


def test_a_bad_edit_from_the_page_is_refused_with_the_cores_reason(page):
    status, reply = call(page, "/api/edit", {"revision": 1, "change": {"zone": "rise", "combine": "blend"}})
    assert status == 400 and "Combine Mode" in reply["error"]

    status, reply = call(page, "/api/edit", {"revision": 7, "change": {"move_landmark": "village", "to": [1, 1]}})
    assert status == 409 and "Revision 7" in reply["error"]


def test_approving_from_the_page_needs_a_waiver_per_miss_and_records_who(page):
    status, reply = call(page, "/api/approve", {"revision": 1, "waivers": {}})
    assert status == 409 and "no Waiver for walk spawn→village" in reply["error"]

    status, state = call(page, "/api/approve", {"revision": 1, "waivers": {"walk spawn→village": "farther is fine"}})

    assert status == 200 and state["state"] == "approved by alice"
    approval = Site.open(page.site_path).approval
    assert approval.by == ALICE and approval.waivers == {"walk spawn→village": "farther is fine"}


def test_rejecting_from_the_page_needs_a_note(page):
    status, reply = call(page, "/api/reject", {"revision": 1, "note": "  "})
    assert status == 409 and "note" in reply["error"]

    status, state = call(page, "/api/reject", {"revision": 1, "note": "village too far"})

    assert status == 200 and state["state"] == "rejected"
    [rejection] = Site.open(page.site_path).rejections
    assert (rejection.by, rejection.note) == (ALICE, "village too far")


def test_a_page_served_without_a_person_at_the_keyboard_cannot_act(island):
    server = running(island, Automated("non-interactive quarry"))
    try:
        waivers = {"walk spawn→village": "fine"}
        for route, body in (
            ("/api/approve", {"revision": 1, "waivers": waivers}),
            ("/api/reject", {"revision": 1, "note": "no"}),
            ("/api/edit", {"revision": 1, "change": {"move_landmark": "village", "to": [1, 1]}}),
        ):
            status, reply = call(server, route, body)
            assert status == 409 and "only a human" in reply["error"]
    finally:
        server.shutdown()
    reopened = Site.open(island.path)
    assert reopened.approval is None and not reopened.rejections and reopened.current_revision.number == 1


def test_a_malformed_request_is_answered_not_crashed(page):
    status, reply = call(page, "/api/edit", {"change": {}})
    assert status == 400 and "revision" in reply["error"]


def test_the_page_itself_is_served_at_its_url(page):
    with urllib.request.urlopen(page.url) as response:
        html = response.read().decode()

    assert response.headers["Content-Type"].startswith("text/html")
    assert "Checkpoint #1" in html


@pytest.fixture
def terrain_page(island):
    """The page for a Site at Checkpoint #2."""
    island.approve(1, by=ALICE, waivers={"walk spawn→village": "farther is fine"})
    island.draft_refine_plan(FakeAgent())
    server = running(island, ALICE)
    yield server
    server.shutdown()


def test_at_checkpoint_2_the_page_state_carries_the_refine_plan_terrain_and_terrain_checks(terrain_page):
    status, state = call(terrain_page, "/api/state")

    assert status == 200
    assert state["checkpoint"] == 2 and state["revision"] == 1 and state["state"] == "awaiting review"
    assert all(s["reason"]["text"] for s in state["refine_plan"]["surfaces"])
    site = Site.open(terrain_page.site_path)
    terrain = site.terrain()
    assert state["terrain"]["spacing"] == terrain.spacing
    assert state["terrain"]["heights"] == [list(row) for row in terrain.heights]
    assert state["walk_speed"] == 1.4 and state["max_walkable_slope"] == 30
    measured = {c["check"]: c["measured"] for c in state["checks"]}
    assert measured == {r.check: r.measured for r in site.terrain_checks()}
    assert state["waivers"] == {}  # Checkpoint #1's Waivers are not this Checkpoint's


def test_at_checkpoint_2_an_edit_rebuilds_the_terrain(terrain_page):
    _, before = call(terrain_page, "/api/state")

    status, state = call(terrain_page, "/api/edit", {"revision": 1, "change": {"surface": "ground", "roughness": 2.0}})

    assert status == 200 and state["revision"] == 2
    ground = next(s for s in state["refine_plan"]["surfaces"] if s["surface"] == "ground")
    assert ground["roughness"] == 2.0 and ground["reason"]["author"] == "human"
    assert state["terrain"]["heights"] != before["terrain"]["heights"]
    assert Site.open(terrain_page.site_path).current_refine_plan.edited_by == ALICE


def test_at_checkpoint_2_approval_needs_fresh_waivers_and_records_who(terrain_page):
    status, reply = call(terrain_page, "/api/approve", {"revision": 1, "waivers": {}})
    assert status == 409 and "no Waiver for walk spawn→village" in reply["error"]

    status, state = call(terrain_page, "/api/approve", {"revision": 1, "waivers": {"walk spawn→village": "on Terrain too"}})

    assert status == 200 and state["state"] == "approved by alice"
    approval = Site.open(terrain_page.site_path).refine_plan_approval
    assert approval.by == ALICE and approval.waivers == {"walk spawn→village": "on Terrain too"}


def test_at_checkpoint_2_rejecting_needs_a_note(terrain_page):
    status, reply = call(terrain_page, "/api/reject", {"revision": 1, "note": ""})
    assert status == 409 and "note" in reply["error"]

    status, state = call(terrain_page, "/api/reject", {"revision": 1, "note": "too smooth"})

    assert status == 200 and state["state"] == "rejected"
    [rejection] = Site.open(terrain_page.site_path).refine_plan_rejections
    assert (rejection.by, rejection.note) == (ALICE, "too smooth")


def test_at_checkpoint_2_a_page_with_no_person_at_the_keyboard_cannot_act(island):
    island.approve(1, by=ALICE, waivers={"walk spawn→village": "fine"})
    island.draft_refine_plan(FakeAgent())
    server = running(island, Automated("non-interactive quarry"))
    try:
        for route, body in (
            ("/api/approve", {"revision": 1, "waivers": {"walk spawn→village": "fine"}}),
            ("/api/reject", {"revision": 1, "note": "no"}),
            ("/api/edit", {"revision": 1, "change": {"surface": "ground", "roughness": 1.0}}),
        ):
            status, reply = call(server, route, body)
            assert status == 409 and "only a human" in reply["error"]
    finally:
        server.shutdown()
    reopened = Site.open(island.path)
    assert reopened.refine_plan_approval is None and not reopened.refine_plan_rejections
    assert reopened.current_refine_plan.number == 1


def test_at_checkpoint_2_the_walkable_preview_page_is_served(terrain_page):
    with urllib.request.urlopen(terrain_page.url) as response:
        html = response.read().decode()

    assert "Checkpoint #2" in html


def test_the_page_state_carries_a_missed_shortcuts_route_and_nothing_for_a_pass(tmp_path):
    # The fake's straight Paths take about 2:45: fine for 3 minutes, far too fast for 10.
    forced = {**ISLAND, "walk_targets": [
        {"from": "spawn", "to": "lighthouse", "time": 180, "tolerance": 0.1, "no_shortcut": True},
        {"from": "spawn", "to": "village", "time": 600, "tolerance": 0.1, "no_shortcut": True},
    ]}
    site = Site.create(tmp_path / "forced", Brief.from_dict(forced))
    site.draft(FakeAgent())
    server = running(site, ALICE)
    try:
        _, state = call(server, "/api/state")
    finally:
        server.shutdown()

    checks = {c["check"]: c for c in state["checks"]}
    held, leaked = checks["shortcut spawn→lighthouse"], checks["shortcut spawn→village"]
    assert held["passed"] and held["route"] is None
    assert not leaked["passed"] and leaked["at_least"]
    spawn = next(l["position"] for l in state["blockout"]["landmarks"] if l["name"] == "spawn")
    assert len(leaked["route"]) >= 2 and math.dist(leaked["route"][0], spawn) < 1.5


def test_an_edit_request_from_the_checkpoint_1_page_drafts_a_revision(island):
    server = running(island, agent=FakeAgent())
    try:
        status, state = call(server, "/api/request", {"request": "make the rise less steep"})
    finally:
        server.shutdown()

    assert status == 200 and state["revision"] == 2 and state["needs_reopen"] is None
    assert Site.open(island.path).current_revision.request == "make the rise less steep"


def test_an_edit_request_needing_a_reopen_on_the_checkpoint_2_page_names_it_and_offers_the_reopen(island):
    island.approve(1, by=ALICE, waivers={"walk spawn→village": "fine"})
    island.draft_refine_plan(FakeAgent())
    server = running(island, agent=FakeAgent())
    try:
        status, state = call(server, "/api/request", {"request": "make the rise lower"})
        assert status == 200 and state["checkpoint"] == 2 and state["revision"] == 1
        assert state["needs_reopen"]["property"] == "rise height" and state["can_reopen"]

        status, state = call(server, "/api/reopen", {})
    finally:
        server.shutdown()

    assert status == 200 and state["checkpoint"] == 1 and not state["can_reopen"]
    site = Site.open(island.path)
    assert site.reopenings[0].by == ALICE and site.refine_plan(1).superseded


def test_a_page_with_no_person_at_the_keyboard_cannot_reopen(island):
    island.approve(1, by=ALICE, waivers={"walk spawn→village": "fine"})
    server = running(island, caller=Automated("non-interactive quarry"))
    try:
        status, reply = call(server, "/api/reopen", {})
    finally:
        server.shutdown()

    assert status == 409 and "only a human" in reply["error"]
    assert Site.open(island.path).approval is not None


def test_a_superseded_refine_plans_terrain_is_viewable_read_only(island):
    island.approve(1, by=ALICE, waivers={"walk spawn→village": "fine"})
    island.draft_refine_plan(FakeAgent())
    island.reopen(by=ALICE)
    server = running(island, superseded=1)
    try:
        _, state = call(server, "/api/state")
        with urllib.request.urlopen(server.url) as response:
            html = response.read().decode()
        status, reply = call(server, "/api/approve", {"revision": 1, "waivers": {}})
    finally:
        server.shutdown()

    site = Site.open(island.path)
    assert state["checkpoint"] == 2 and state["superseded"] and state["revision"] == 1
    assert state["terrain"]["heights"] == [list(row) for row in site.superseded_terrain(1).heights]
    assert "Checkpoint #2" in html
    assert status == 409 and "Superseded" in reply["error"]
