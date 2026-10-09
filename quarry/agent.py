"""The Agent port, and a fake that drafts without an LLM.

An Agent has four operations, each returning its Draft as plain data (the shape
of `to_dict`), never as a trusted object:

    draft_blockout(brief, rejection_note=None, shortcuts=())
    draft_refine_plan(brief, blockout, rejection_note=None, shortcuts=())
    edit_blockout(brief, blockout, request)  -> a Blockout
    edit_refine_plan(brief, blockout, plan, request)
        -> {"plan": a Refine Plan, "needs_reopen": None}
        or {"plan": None, "needs_reopen": {"property": ..., "reason": ...}}

The last two answer an Edit Request: a plain-language change the human asks for.

`shortcuts` are the latest Revision's missed Shortcut Checks, each carrying the
route that leaked, so the next Draft can see where to close it.

The Site passes every output through `quarry.validation` before keeping it. An
Agent is handed a Brief and a Blockout, never the Site, so it has no way to
perform a human act. The live adapters are `quarry.claude_code_agent` (on the
Claude subscription, the default) and `quarry.claude_agent` (the Anthropic API).
"""
import math

from dataclasses import replace

from quarry.blockout import Blockout, Landmark, Path, Reading, Reason, Zone
from quarry.checks import run_checks
from quarry.refine import RefinePlan, Refinement


# Mood words the fake knows how to measure; any other phrase is read but not measured.
_MEASURABLE = {"gentle": ("max_slope", 15.0, "no slope steeper than 15°")}


class FakeAgent:
    """Places Waypoints on a ring around the footprint's centre, raises a gentle
    rise in the middle and joins each Walk Target with a straight Path.
    Deterministic, so tests know the answer."""

    def __init__(self, seed=1):
        self.seed = seed

    def __repr__(self):
        return f"FakeAgent(seed={self.seed})"

    def draft_blockout(self, brief, rejection_note=None, shortcuts=()):
        width, depth = brief.footprint
        radius = min(width, depth) / 3
        landmarks = {}
        for i, name in enumerate(brief.waypoints):
            angle = 2 * math.pi * i / len(brief.waypoints)
            position = (width / 2 + radius * math.cos(angle), depth / 2 + radius * math.sin(angle))
            landmarks[name] = Landmark(name, position, Reason("ai", f"placed {name} on the ring"))
        paths = tuple(
            Path(
                t.start,
                t.end,
                (landmarks[t.start].position, landmarks[t.end].position),
                Reason("ai", f"straight route from {t.start} to {t.end}"),
            )
            for t in brief.walk_targets
        )
        # Inside the ring, so it never tilts a Pad; ~13° at its steepest.
        rise_radius = min(width, depth) / 6
        rise = Zone(
            "rise", (width / 2, depth / 2), rise_radius, rise_radius * 0.15, "dome", "add",
            Reason("ai", "a low rise in the middle gives the ground some shape"),
        )
        blockout = Blockout(tuple(landmarks.values()), paths, (rise,), _readings(brief.mood))
        return _own_misses(brief, blockout).to_dict()

    def draft_refine_plan(self, brief, blockout, rejection_note=None, shortcuts=()):
        ground = Refinement(
            surface="ground",
            slope_profile="smooth",
            falloff_width=20.0,
            roughness=0.5,
            seed=self.seed,
            vegetation_density=0.3,
            reason=Reason("ai", "low roughness keeps the ground easy to walk"),
        )
        zones = tuple(
            Refinement(
                surface=zone.name,
                slope_profile="smooth",
                falloff_width=10.0,
                roughness=0.2,
                seed=self.seed,
                vegetation_density=0.6,
                reason=Reason("ai", f"denser growth marks {zone.name} out from the ground"),
            )
            for zone in blockout.zones
        )
        cut_paths = tuple(
            Refinement(
                surface=f"{path.start}→{path.end}",
                slope_profile="smooth",
                falloff_width=2.0,
                roughness=0.0,
                seed=self.seed,
                vegetation_density=0.0,
                reason=Reason("ai", "a bare, smooth trail whose banks ease only a little"),
            )
            for path in blockout.paths
            if path.cut
        )
        return RefinePlan((ground, *zones, *cut_paths)).to_dict()

    def edit_blockout(self, brief, blockout, request):
        """Halves the height of every Zone the request names."""
        named = [z.name for z in blockout.zones if z.name in request]
        why = Reason("ai", f"halved in height for your request “{request}”")
        zones = tuple(replace(z, height=z.height / 2, reason=why) if z.name in named else z for z in blockout.zones)
        return replace(blockout, zones=zones).to_dict()

    def edit_refine_plan(self, brief, blockout, plan, request):
        """Doubles the falloff of every surface the request names, unless it asks
        for something only the Blockout owns."""
        for word, owned in _BLOCKOUT_WORDS.items():
            if word in request:
                [zone] = [z.name for z in blockout.zones if z.name in request] or ["the ground"]
                why = f"“{word}” changes the {owned}, which the approved Blockout owns"
                return {"plan": None, "needs_reopen": {"property": f"{zone} {owned}", "reason": why}}
        why = Reason("ai", f"falloff doubled to ease the slopes, for your request “{request}”")
        surfaces = tuple(
            replace(s, falloff_width=s.falloff_width * 2, reason=why) if s.surface in request else s
            for s in plan.surfaces
        )
        return {"plan": replace(plan, surfaces=surfaces).to_dict(), "needs_reopen": None}


# Words in an Edit Request the fake reads as asking for a Blockout-owned property.
_BLOCKOUT_WORDS = {"lower": "height", "higher": "height", "move": "position", "bigger": "radius", "smaller": "radius"}


def _readings(mood):
    readings = []
    for phrase in (p.strip() for p in mood.split(",")):
        if not phrase:
            continue
        word = next((w for w in _MEASURABLE if w in phrase.lower()), None)
        if word:
            measure, limit, meaning = _MEASURABLE[word]
            readings.append(Reading(phrase, meaning, measure, limit, Reason("ai", f"“{word}” reads as a slope limit")))
        else:
            readings.append(Reading(phrase, "a feel to judge by eye", None, None, Reason("ai", "no measure fits this phrase")))
    return tuple(readings)


def _own_misses(brief, blockout):
    """A missed target is delivered anyway, with the Path's Reason owning the miss.
    The Brief is never bent to fit."""
    missed = {r.check: r for r in run_checks(brief, blockout) if not r.passed}
    paths = []
    for path in blockout.paths:
        miss = missed.get(f"walk {path.start}→{path.end}")
        if miss:
            text = (
                f"{path.reason.text}; it measures {miss.measured:.0f} {miss.unit} "
                f"and misses the {miss.target:g} {miss.unit} target"
            )
            path = replace(path, reason=Reason("ai", text))
        paths.append(path)
    return replace(blockout, paths=tuple(paths))
