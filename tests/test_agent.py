"""The Claude adapter, driven by a fake LLM: no test makes a live call."""
import json
from types import SimpleNamespace

import pytest

from quarry.claude_agent import ClaudeAgent
from quarry.brief import Brief
from quarry.identity import Human
from quarry.site import Site
from quarry.validation import InvalidDraft

ALICE = Human("alice")

ISLAND = {
    "footprint": [400, 400],
    "mood": "gentle hills",
    "waypoints": ["spawn", "lighthouse"],
    "walk_targets": [{"from": "spawn", "to": "lighthouse", "time": 120, "tolerance": 0.1}],
}


def ai(text):
    return {"author": "ai", "text": text}


def blockout_output():
    """What a well-behaved model answers for ISLAND."""
    return {
        "landmarks": [
            {"name": "spawn", "position": [100, 200], "reason": ai("near the west shore"), "pad_radius": 6, "ai_chosen": False},
            {"name": "lighthouse", "position": [268, 200], "reason": ai("on the east point"), "pad_radius": 8, "ai_chosen": False},
        ],
        "paths": [
            {"start": "spawn", "end": "lighthouse", "points": [[100, 200], [268, 200]], "reason": ai("straight along the ridge"), "decorative": False, "cut": False, "width": None},
        ],
        "zones": [
            {"name": "hill", "center": [200, 300], "radius": 50, "height": 6, "profile": "dome", "combine": "add", "reason": ai("a gentle hill off the Path")},
        ],
        "readings": [
            {"phrase": "gentle hills", "meaning": "no slope steeper than 15°", "measure": "max_slope", "limit": 15, "reason": ai("“gentle” reads as a slope limit")},
        ],
    }


class FakeLLM:
    """Stands in for `anthropic.Anthropic()`: answers each request with the next
    scripted output and keeps every request so tests can read the input."""

    def __init__(self, *outputs, stop_reason="end_turn"):
        self.outputs = list(outputs)
        self.stop_reason = stop_reason
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.requests.append(request)
        output = self.outputs.pop(0)
        text = output if isinstance(output, str) else json.dumps(output)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=text)])

    def prompt(self, index=-1):
        return json.dumps(self.requests[index]["messages"], ensure_ascii=False)


@pytest.fixture
def island(tmp_path):
    return Site.create(tmp_path / "island", Brief.from_dict(ISLAND))


def test_the_claude_agent_drafts_a_blockout_that_becomes_a_revision(island):
    llm = FakeLLM(blockout_output())

    island.draft(ClaudeAgent(client=llm))

    blockout = island.current_revision.blockout
    assert [l.name for l in blockout.landmarks] == ["spawn", "lighthouse"]
    assert blockout.paths[0].reason.text == "straight along the ridge"
    assert [z.name for z in blockout.zones] == ["hill"]
    assert llm.requests[0]["model"] == "claude-opus-5-5"
    assert "lighthouse" in llm.prompt()


def test_the_latest_rejection_note_is_in_the_next_blockout_drafts_input(island):
    llm = FakeLLM(blockout_output(), blockout_output(), blockout_output())
    agent = ClaudeAgent(client=llm)
    island.draft(agent)
    island.reject(1, by=ALICE, note="the hill hides the lighthouse")
    island.draft(agent)
    island.reject(2, by=ALICE, note="spawn is too close to the shore")

    island.draft(agent)

    assert "hill hides the lighthouse" not in llm.prompt(0)
    assert "spawn is too close to the shore" in llm.prompt()
    assert "hill hides the lighthouse" not in llm.prompt()


def broken(change):
    """A Blockout output with one thing wrong."""
    output = blockout_output()
    change(output)
    return output


def refused(site, output, match):
    with pytest.raises(InvalidDraft, match=match):
        site.draft(ClaudeAgent(client=FakeLLM(output)))
    assert site.current_revision is None  # nothing reached the history


@pytest.mark.parametrize("output", [
    "Sure! Here is a Blockout: …",
    broken(lambda o: o.pop("paths")),
    broken(lambda o: o["landmarks"][0].update(position="west")),
    broken(lambda o: o["zones"][0].update(radius=-5)),
    broken(lambda o: o["readings"][0].update(limit=None)),
    broken(lambda o: o["readings"][0].update(measure=None)),
    broken(lambda o: o["paths"].append({**o["paths"][0], "end": "harbour", "decorative": True})),
])
def test_malformed_output_is_rejected(island, output):
    refused(island, output, "malformed")


@pytest.mark.parametrize("output", [
    broken(lambda o: o["landmarks"][1]["reason"].update(text="")),
    broken(lambda o: o["paths"][0]["reason"].update(text="   ")),
    broken(lambda o: o["readings"][0]["reason"].update(author="human", text="you asked for this")),
])
def test_a_choice_without_an_ai_reason_is_rejected(island, output):
    refused(island, output, "Reason")


@pytest.mark.parametrize("output", [
    broken(lambda o: o["landmarks"].pop()),
    broken(lambda o: o["landmarks"].append({**o["landmarks"][0], "position": [300, 300]})),
])
def test_a_waypoint_without_exactly_one_landmark_is_rejected(island, output):
    refused(island, output, "Waypoint lighthouse|Waypoint spawn")


@pytest.mark.parametrize("output", [
    broken(lambda o: o["paths"].pop()),
    broken(lambda o: o["paths"][0].update(decorative=True)),
    broken(lambda o: o["paths"].append({**o["paths"][0], "points": [[100, 200], [200, 250], [268, 200]]})),
])
def test_a_walk_target_without_exactly_one_path_is_rejected(island, output):
    refused(island, output, "Walk Target spawn→lighthouse")


def test_an_ai_chosen_landmark_and_a_decorative_path_are_allowed(island):
    output = blockout_output()
    output["landmarks"].append({"name": "well", "position": [200, 120], "reason": ai("a place to rest"), "pad_radius": 4, "ai_chosen": True})
    output["paths"].append({"start": "spawn", "end": "well", "points": [[100, 200], [200, 120]], "reason": ai("a side trail"), "decorative": True, "cut": False, "width": None})

    island.draft(ClaudeAgent(client=FakeLLM(output)))

    assert island.current_revision.number == 1


def test_a_cut_path_and_its_width_round_trip_into_the_revision(island):
    output = blockout_output()
    output["paths"][0].update(cut=True, width=6, reason=ai("a 6 m cut graded evenly along the ridge"))

    island.draft(ClaudeAgent(client=FakeLLM(output)))

    [path] = island.current_revision.blockout.paths
    assert path.cut and path.width == 6
    assert type(island.current_revision.blockout).from_dict(island.current_revision.blockout.to_dict()) == island.current_revision.blockout


@pytest.mark.parametrize("change, match", [
    (lambda p: p.update(cut=True, width=3), "at least 4 m"),
    (lambda p: p.update(cut=True, width=None), "at least 4 m"),
    (lambda p: p.update(width=6), "only a Cut Path has a width"),
])
def test_a_cut_path_needs_a_width_of_at_least_4_m_and_only_a_cut_path_has_one(island, change, match):
    refused(island, broken(lambda o: change(o["paths"][0])), match)


@pytest.mark.parametrize("output", [
    broken(lambda o: o.update(walk_targets=[{"from": "spawn", "to": "lighthouse", "time": 200, "tolerance": 0.1}])),
    broken(lambda o: o.update(max_walkable_slope=40)),
    broken(lambda o: o["paths"][0].update(time=200)),
    broken(lambda o: o["paths"][0].update(tolerance=0.5)),
])
def test_output_that_rewrites_the_briefs_targets_is_rejected(island, output):
    refused(island, output, "rewrites the Brief")


@pytest.mark.parametrize("output", [
    broken(lambda o: o["zones"][0].update(roughness=0.4)),
    broken(lambda o: o["zones"][0].update(falloff_width=30)),
    broken(lambda o: o["landmarks"][0].update(vegetation_density=0)),
])
def test_a_blockout_that_sets_a_refine_plan_property_is_rejected(island, output):
    refused(island, output, "belongs to the Refine Plan")


def refine_output():
    """What a well-behaved model answers for the approved ISLAND Blockout."""
    def refinement(surface, roughness, why):
        return {
            "surface": surface, "slope_profile": "smooth", "falloff_width": 12, "roughness": roughness,
            "seed": 7, "vegetation_density": 0.4, "reason": ai(why),
        }
    return {"surfaces": [
        refinement("ground", 0.2, "kept roughness low along the Path so the walk stays at 2:00"),
        refinement("hill", 0.8, "rougher on the hill, which no Path crosses"),
    ]}


@pytest.fixture
def approved(island):
    island.draft(ClaudeAgent(client=FakeLLM(blockout_output())))
    island.approve(1, by=ALICE)
    return island


def test_the_claude_agent_drafts_a_refine_plan_from_the_approved_blockout(approved):
    llm = FakeLLM(refine_output())

    approved.draft_refine_plan(ClaudeAgent(client=llm))

    plan = approved.current_refine_plan.plan
    assert [s.surface for s in plan.surfaces] == ["ground", "hill"]
    assert "walk stays at 2:00" in plan.surfaces[0].reason.text
    assert "straight along the ridge" in llm.prompt()  # the approved Blockout, Paths included
    assert "spawn" in llm.prompt() and "lighthouse" in llm.prompt()


def broken_plan(change):
    output = refine_output()
    change(output["surfaces"])
    return output


def refused_plan(site, output, match):
    with pytest.raises(InvalidDraft, match=match):
        site.draft_refine_plan(ClaudeAgent(client=FakeLLM(output)))
    assert site.current_refine_plan is None


@pytest.mark.parametrize("output, match", [
    ("[]", "malformed"),
    (broken_plan(lambda s: s[0].update(vegetation_density=2)), "malformed"),
    (broken_plan(lambda s: s[1].update(slope_profile="jagged")), "malformed"),
    (broken_plan(lambda s: s[0].update(seed=1.5)), "malformed"),
    (broken_plan(lambda s: s[1]["reason"].update(text="")), "Reason"),
    (broken_plan(lambda s: s.pop()), "hill is refined 0 times"),
    (broken_plan(lambda s: s.append(dict(s[1]))), "hill is refined 2 times"),
    (broken_plan(lambda s: s.append({**s[1], "surface": "lake"})), "no surface named lake"),
    (broken_plan(lambda s: s[1].update(height=3)), "belongs to the Blockout"),
    (broken_plan(lambda s: s[1].update(radius=80)), "belongs to the Blockout"),
])
def test_an_invalid_refine_plan_is_rejected(approved, output, match):
    refused_plan(approved, output, match)


def test_the_latest_rejection_note_is_in_the_next_refine_plan_drafts_input(approved):
    llm = FakeLLM(refine_output(), refine_output())
    approved.draft_refine_plan(ClaudeAgent(client=llm))
    approved.reject_refine_plan(1, by=ALICE, note="the ground looks like gravel")

    approved.draft_refine_plan(ClaudeAgent(client=llm))

    assert "the ground looks like gravel" in llm.prompt()


def test_the_model_is_offered_no_tool_for_any_human_act(approved):
    llm = FakeLLM(blockout_output(), refine_output())
    agent = ClaudeAgent(client=llm)
    agent.draft_blockout(approved.brief)
    agent.draft_refine_plan(approved.brief, approved.current_revision.blockout)

    for request in llm.requests:
        assert not request.get("tools")
        assert request.get("tool_choice") in (None, {"type": "none"})


@pytest.mark.parametrize("act", ["approval", "waivers", "rejection", "reopen"])
def test_output_that_attempts_a_human_act_is_rejected_and_nothing_is_approved(island, act):
    output = broken(lambda o: o.update({act: {"revision": 1, "by": "agent"}}))

    refused(island, output, "only a human")

    assert island.approval is None and island.rejections == []


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_a_draft_the_model_did_not_finish_is_rejected(island, stop_reason):
    llm = FakeLLM('{"landmarks": [', stop_reason=stop_reason)

    with pytest.raises(InvalidDraft, match=f"stopped early \\({stop_reason}\\)"):
        island.draft(ClaudeAgent(client=llm))
    assert island.current_revision is None


# The model's straight 168 m Path takes 2:00, far under a forced 10-minute walk:
# both the Path and the straight line beside it are Shortcuts.
FORCED = {**ISLAND, "walk_targets": [{"from": "spawn", "to": "lighthouse", "time": 600, "tolerance": 0.1, "no_shortcut": True}]}
FORCED_WAIVERS = {"walk spawn→lighthouse": "short on purpose", "shortcut spawn→lighthouse": "open ground"}


@pytest.fixture
def forced(tmp_path):
    return Site.create(tmp_path / "forced", Brief.from_dict(FORCED))


def test_the_latest_blockouts_shortcut_misses_are_in_the_next_drafts_input(forced):
    llm = FakeLLM(blockout_output(), blockout_output())
    forced.draft(ClaudeAgent(client=llm))

    forced.draft(ClaudeAgent(client=llm))

    assert "Shortcut" not in llm.prompt(0)
    latest = llm.prompt()
    assert "spawn→lighthouse" in latest and "Shortcut" in latest
    assert "2:0" in latest and "10:00" in latest  # how fast, against what
    assert "(100, 200)" in latest and "(268, 200)" in latest  # the route, from spawn to the lighthouse


def test_the_latest_terrains_shortcut_misses_are_in_the_next_refine_plans_input(forced):
    llm = FakeLLM(blockout_output(), refine_output(), refine_output())
    forced.draft(ClaudeAgent(client=llm))
    forced.approve(1, by=ALICE, waivers=FORCED_WAIVERS)
    forced.draft_refine_plan(ClaudeAgent(client=llm))

    forced.draft_refine_plan(ClaudeAgent(client=llm))

    assert "Shortcut" not in llm.prompt(1)
    assert "Shortcut" in llm.prompt() and "spawn→lighthouse" in llm.prompt()


@pytest.fixture
def approved_with_a_cut(island):
    output = blockout_output()
    output["paths"][0].update(cut=True, width=6)
    island.draft(ClaudeAgent(client=FakeLLM(output)))
    island.approve(1, by=ALICE, waivers={c.check: "test" for c in island.checks() if not c.passed})
    return island


def test_a_refine_plan_must_refine_each_cut_path_exactly_once(approved_with_a_cut):
    def cut_refinement(surfaces):
        surfaces.append({**surfaces[0], "surface": "spawn→lighthouse", "reason": ai("a smooth, bare trail")})

    refused_plan(approved_with_a_cut, refine_output(), "spawn→lighthouse is refined 0 times")
    refused_plan(approved_with_a_cut, broken_plan(lambda s: (cut_refinement(s), cut_refinement(s))), "spawn→lighthouse is refined 2 times")

    approved_with_a_cut.draft_refine_plan(ClaudeAgent(client=FakeLLM(broken_plan(cut_refinement))))

    surfaces = [s.surface for s in approved_with_a_cut.current_refine_plan.plan.surfaces]
    assert surfaces == ["ground", "hill", "spawn→lighthouse"]
