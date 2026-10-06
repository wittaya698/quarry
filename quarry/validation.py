"""The validation layer: every Agent output passes here before it reaches the
Site's history. A Draft that breaks a rule is refused whole, never repaired.
"""
from dataclasses import fields

from quarry.blockout import Blockout, Landmark, Path, Reading, Zone
from quarry.brief import Brief
from quarry.edits import REFINE_VALUES
from quarry.refine import RefinePlan, Refinement


class InvalidDraft(Exception):
    """Agent output that cannot become a Revision."""


# The Brief's targets, as they could appear in a Draft that tried to restate them.
_BRIEF_FIELDS = {f.name for f in fields(Brief)} | {"time", "distance", "tolerance"}
# What the Refine Plan owns (ADR-0003); a Blockout never sets any of it.
_REFINE_FIELDS = {f.name for f in fields(Refinement)} - {"surface", "reason"}
# What the Blockout owns; a Refine Plan never sets any of it.
_BLOCKOUT_FIELDS = {f.name for f in fields(Blockout)} | {
    f.name for kind in (Landmark, Path, Zone, Reading) for f in fields(kind)
} - {"name", "reason"}

# Checkpoint acts (ADR-0004): no Draft may carry one, in any spelling of the field.
_HUMAN_ACTS = {"approval", "approve", "waiver", "waivers", "rejection", "reject", "reopen"}

_NUMBER = (int, float)
_BLOCKOUT_SHAPE = {
    "landmarks": {"name": str, "position": "point", "reason": "reason", "pad_radius": _NUMBER, "ai_chosen": bool},
    "paths": {"start": str, "end": str, "points": "points", "reason": "reason", "decorative": bool},
    "zones": {
        "name": str, "center": "point", "radius": _NUMBER, "height": _NUMBER,
        "profile": ("dome", "flat"), "combine": ("add", "max", "replace"), "reason": "reason",
    },
    "readings": {
        "phrase": str, "meaning": str, "measure": (None, "max_slope", "max_height"),
        "limit": (_NUMBER, None), "reason": "reason",
    },
}

_REFINE_PLAN_SHAPE = {
    "surfaces": {
        "surface": str, "slope_profile": str, "falloff_width": _NUMBER, "roughness": _NUMBER,
        "seed": int, "vegetation_density": _NUMBER, "reason": "reason",
    },
}


def validate_blockout(brief, output):
    _refuse_foreign(output, _REFINE_FIELDS, "the Refine Plan")
    _require_shape(output, _BLOCKOUT_SHAPE)
    for kind in ("landmarks", "zones"):
        for item in output[kind]:
            size = item.get("pad_radius", item.get("radius"))
            if not size > 0:
                raise InvalidDraft(f"malformed output: {item['name']} has a size of {size} m")
    for reading in output["readings"]:
        if (reading["measure"] is None) != (reading["limit"] is None):
            raise InvalidDraft(f"malformed output: the Reading of “{reading['phrase']}” needs both a measure and a limit, or neither")
    _require_reasons(output)
    names = [l["name"] for l in output["landmarks"]]
    for waypoint in brief.waypoints:
        if names.count(waypoint) != 1:
            raise InvalidDraft(f"Waypoint {waypoint} has {names.count(waypoint)} Landmarks; it needs exactly one")
    for path in output["paths"]:
        for end in (path["start"], path["end"]):
            if end not in names:
                raise InvalidDraft(f"malformed output: a Path ends at {end}, which is no Landmark")
    routes = [(p["start"], p["end"]) for p in output["paths"] if not p["decorative"]]
    for t in brief.walk_targets:
        count = routes.count((t.start, t.end))
        if count != 1:
            raise InvalidDraft(f"Walk Target {t.start}→{t.end} has {count} Paths; it needs exactly one")
    return Blockout.from_dict(output)


def validate_refine_plan(brief, blockout, output):
    _refuse_foreign(output, _BLOCKOUT_FIELDS, "the Blockout")
    _require_shape(output, _REFINE_PLAN_SHAPE)
    for refinement in output["surfaces"]:
        for field, valid in REFINE_VALUES.items():
            if not valid(refinement[field]) or isinstance(refinement[field], bool):
                raise InvalidDraft(f"malformed output: {field} {_quote(refinement[field])} for {refinement['surface']}")
    _require_reasons(output)
    surfaces = ["ground", *(z.name for z in blockout.zones)]
    refined = [r["surface"] for r in output["surfaces"]]
    for name in refined:
        if name not in surfaces:
            raise InvalidDraft(f"the Refine Plan refines no surface named {name}; the Blockout has {', '.join(surfaces)}")
    for name in surfaces:
        if refined.count(name) != 1:
            raise InvalidDraft(f"{name} is refined {refined.count(name)} times; it needs exactly one Refinement")
    return RefinePlan.from_dict(output)


def _refuse_foreign(output, other_stage, owner):
    """Refuse anything a Draft has no right to write: a human act, the Brief's
    targets, or a property the other stage owns."""
    _refuse_trespass(output, _HUMAN_ACTS, "attempts {}: only a human can approve, waive, reject or reopen")
    _refuse_trespass(output, _BRIEF_FIELDS, "rewrites the Brief: {} is the Brief's, never the Agent's")
    _refuse_trespass(output, other_stage, "sets {}, which belongs to " + owner + " (ADR-0003)")


def _require_reasons(output):
    """Every choice carries the AI's own Reason; only a human edit writes a human one."""
    for kind, items in output.items():
        for item in items:
            reason = item["reason"]
            if reason["author"] != "ai" or not str(reason["text"]).strip():
                label = item.get("name") or item.get("phrase") or item.get("surface") or f"{item.get('start')}→{item.get('end')}"
                raise InvalidDraft(f"{kind} {label} has no Reason from the AI")


def _refuse_trespass(output, foreign, message):
    """Refuse a Draft that writes a property it does not own, at the top level or in any item."""
    if not isinstance(output, dict):
        return  # left for the shape check to call malformed
    keys = set(output)
    for items in output.values():
        if isinstance(items, (list, tuple)):
            keys |= {k for item in items if isinstance(item, dict) for k in item}
    trespass = sorted(keys & foreign)
    if trespass:
        raise InvalidDraft(f"the Draft {message.format(', '.join(trespass))}")


def _require_shape(output, shape):
    if not isinstance(output, dict):
        raise InvalidDraft(f"malformed output: expected a JSON object, got {_quote(output)}")
    if set(output) != set(shape):
        raise InvalidDraft(f"malformed output: expected {', '.join(shape)}; got {', '.join(output)}")
    for kind, columns in shape.items():
        items = output[kind]
        if not isinstance(items, (list, tuple)) or not all(isinstance(i, dict) for i in items):
            raise InvalidDraft(f"malformed output: {kind} must be a list of objects")
        for item in items:
            if set(item) != set(columns):
                raise InvalidDraft(f"malformed output: one of the {kind} has {', '.join(sorted(item))}")
            for field, expected in columns.items():
                if not _fits(item[field], expected):
                    raise InvalidDraft(f"malformed output: {field} {_quote(item[field])} in {kind}")


def _fits(value, expected):
    if expected == "point":
        return isinstance(value, (list, tuple)) and len(value) == 2 and all(_is_number(v) for v in value)
    if expected == "points":
        return isinstance(value, (list, tuple)) and len(value) >= 2 and all(_fits(p, "point") for p in value)
    if expected == "reason":
        return isinstance(value, dict) and set(value) == {"author", "text"}
    if expected is _NUMBER:
        return _is_number(value)
    if isinstance(expected, tuple):  # allowed values, or a number or None
        return any(_fits(value, e) if e is _NUMBER else value == e for e in expected)
    return isinstance(value, expected)


def _is_number(value):
    return isinstance(value, _NUMBER) and not isinstance(value, bool)


def _quote(value):
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "…"
