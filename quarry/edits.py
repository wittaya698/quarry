"""Human edits: one small change to a Blockout or Refine Plan, giving the next Revision.

No Agent is involved. Whatever an edit touches gets a human Reason in place of
the AI's, so a stale justification never sits next to the developer's change.
"""
from dataclasses import replace

from quarry.blockout import Reason

COMBINE_MODES = ("add", "max", "replace")
_MEANINGS = {"max_slope": "no slope steeper than {:g}°", "max_height": "nothing higher than {:g} m"}
_ZONE_VERBS = {"center": "moved", "radius": "resized", "height": "re-heighted", "combine": "recombined"}


class EditError(ValueError):
    """An edit that names nothing in the Blockout, or makes no sense for it."""


def apply_edit(blockout, change):
    if "move_landmark" in change:
        return _move_landmark(blockout, change["move_landmark"], tuple(change["to"]))
    if "stack" in change:
        return _restack(blockout, list(change["stack"]))
    if "reading" in change:
        return _edit_reading(blockout, change["reading"], change["limit"])
    if "zone" in change:
        return _edit_zone(blockout, change["zone"], {k: v for k, v in change.items() if k != "zone"})
    raise EditError(f"unknown edit {change!r}")


def _move_landmark(blockout, name, to):
    if name not in {l.name for l in blockout.landmarks}:
        raise EditError(f"no Landmark named {name}")
    yours = Reason("human", "moved by you")
    landmarks = tuple(
        replace(l, position=to, reason=yours) if l.name == name else l for l in blockout.landmarks
    )
    paths = []
    for p in blockout.paths:
        if name in (p.start, p.end):
            points = list(p.points)
            if p.start == name:
                points[0] = to
            if p.end == name:
                points[-1] = to
            p = replace(p, points=tuple(points), reason=Reason("human", f"follows {name}, moved by you"))
        paths.append(p)
    return replace(blockout, landmarks=landmarks, paths=tuple(paths))


def _edit_zone(blockout, name, values):
    if name not in {z.name for z in blockout.zones}:
        raise EditError(f"no Zone named {name}")
    unknown = set(values) - set(_ZONE_VERBS)
    if unknown or not values:
        raise EditError(f"a Zone edit changes {', '.join(_ZONE_VERBS)}; got {', '.join(sorted(unknown)) or 'nothing'}")
    if "combine" in values and values["combine"] not in COMBINE_MODES:
        raise EditError(f"Combine Mode must be one of {', '.join(COMBINE_MODES)}")
    if "radius" in values and not values["radius"] > 0:
        raise EditError("a Zone's radius must be more than 0 m")
    if "center" in values:
        values = {**values, "center": tuple(values["center"])}
    verbs = ", ".join(_ZONE_VERBS[k] for k in _ZONE_VERBS if k in values)
    yours = Reason("human", f"{verbs} by you")
    zones = tuple(replace(z, **values, reason=yours) if z.name == name else z for z in blockout.zones)
    return replace(blockout, zones=zones)


def _restack(blockout, order):
    names = [z.name for z in blockout.zones]
    if sorted(order) != sorted(names):
        raise EditError(f"a Stacking Order must name each Zone exactly once: {', '.join(names)}")
    by_name = {z.name: z for z in blockout.zones}
    yours = Reason("human", "restacked by you")
    zones = tuple(
        by_name[name] if names[i] == name else replace(by_name[name], reason=yours)
        for i, name in enumerate(order)
    )
    return replace(blockout, zones=zones)


def _edit_reading(blockout, phrase, limit):
    [reading] = [r for r in blockout.readings if r.phrase == phrase] or [None]
    if reading is None:
        raise EditError(f"no Reading of “{phrase}”")
    if reading.measure is None:
        raise EditError(f"the Reading of “{phrase}” is not measurable, so it has no limit")
    meaning = _MEANINGS[reading.measure].format(limit)
    edited = replace(reading, meaning=meaning, limit=limit, reason=Reason("human", f"limit set to {limit:g} by you"))
    return replace(blockout, readings=tuple(edited if r is reading else r for r in blockout.readings))


_REFINE_VALUES = {
    "slope_profile": lambda v: v in ("linear", "smooth", "steep"),
    "falloff_width": lambda v: isinstance(v, (int, float)) and v >= 0,
    "roughness": lambda v: isinstance(v, (int, float)) and v >= 0,
    "seed": lambda v: isinstance(v, int),
    "vegetation_density": lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
}


def apply_refine_edit(plan, change):
    """Change one surface's Refinement; nothing the Blockout owns can be reached."""
    name = change.get("surface")
    values = {k: v for k, v in change.items() if k != "surface"}
    if name not in {s.surface for s in plan.surfaces}:
        raise EditError(f"no Refinement for a surface named {name}")
    unknown = set(values) - set(_REFINE_VALUES)
    if unknown or not values:
        raise EditError(
            f"a Refine Plan edit changes {', '.join(_REFINE_VALUES)}; got {', '.join(sorted(unknown)) or 'nothing'}"
        )
    for key, value in values.items():
        if not _REFINE_VALUES[key](value):
            raise EditError(f"{value!r} is not a valid {key.replace('_', ' ')}")
    changed = ", ".join(f"{k.replace('_', ' ')} {v if isinstance(v, str) else format(v, 'g')}" for k, v in values.items())
    yours = Reason("human", f"{changed}, set by you")
    surfaces = tuple(replace(s, **values, reason=yours) if s.surface == name else s for s in plan.surfaces)
    return replace(plan, surfaces=surfaces)
