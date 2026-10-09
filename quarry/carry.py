"""Carry-forward: after a Reopen, which Refine Plan values still describe ground
that did not change, so the next Refine Plan can keep them.

A surface is touched if the Blockout edited it, or if its shape overlaps the
old or new shape of anything edited: a Zone, a Cut Path's strip, or a Landmark's
Pad. Everything else is untouched, and its values are carried verbatim.
"""
import math
import re
from dataclasses import replace

from quarry.blockout import Reason

_ZONE_SHAPE = ("center", "radius", "height", "profile", "combine")
_CARRIED = re.compile(r"^carried from Refine Plan Revision \d+: ")


def touched(old, new):
    """The names of the new Blockout's refined surfaces (Zones and Cut Paths)
    whose Refine Plan values cannot be carried from the old one."""
    old_zones, new_zones = _zones(old), _zones(new)
    old_order = [name for name in old_zones if name in new_zones]
    new_order = [name for name in new_zones if name in old_zones]
    old_paths, new_paths = _cut_paths(old), _cut_paths(new)
    old_pads, new_pads = _pads(old), _pads(new)

    edited, shapes = set(), []
    for before, after, same, refined in (
        (old_zones, new_zones, _same_zone, True),
        (old_paths, new_paths, _same_path, True),
        (old_pads, new_pads, lambda a, b: a == b, False),  # a Pad is no surface of its own
    ):
        for name in before.keys() | after.keys():
            a, b = before.get(name), after.get(name)
            if a is None or b is None or not same(a, b):
                edited |= {name} if refined else set()
                shapes += [_shape(s) for s in (a, b) if s is not None]
    for name in new_order:
        if old_order.index(name) != new_order.index(name):
            edited.add(name)
            shapes.append(_shape(new_zones[name]))
            shapes.append(_shape(old_zones[name]))

    refined = {**new_zones, **new_paths}
    return {
        name for name, surface in refined.items()
        if name in edited or any(_overlap(_shape(surface), shape) for shape in shapes)
    }


def carry_forward(plan, number, keep):
    """The Refinements of `plan` (Refine Plan Revision `number`) for the surfaces
    in `keep`, values verbatim, each Reason naming the Revision they came from."""
    return {
        s.surface: replace(
            s, reason=Reason(s.reason.author, f"carried from Refine Plan Revision {number}: "
                             f"{_CARRIED.sub('', s.reason.text)}")
        )
        for s in plan.surfaces
        if s.surface in keep
    }


def _zones(blockout):
    return {z.name: z for z in blockout.zones}


def _cut_paths(blockout):
    return {f"{p.start}→{p.end}": p for p in blockout.paths if p.cut}


def _pads(blockout):
    """Each Landmark's Pad, as (position, radius); the Landmark's Reason is not its shape."""
    return {l.name: (l.position, l.pad_radius) for l in blockout.landmarks}


def _same_zone(a, b):
    return all(getattr(a, f) == getattr(b, f) for f in _ZONE_SHAPE)


def _same_path(a, b):
    return (a.points, a.width) == (b.points, b.width)


def _shape(thing):
    """(polyline, radius): a disc is a one-point polyline; a strip, its centreline."""
    if isinstance(thing, tuple):  # a Pad
        position, radius = thing
        return (position,), radius
    if hasattr(thing, "radius"):  # a Zone
        return (thing.center,), thing.radius
    return thing.points, thing.width / 2  # a Cut Path


def _overlap(a, b):
    (points_a, radius_a), (points_b, radius_b) = a, b
    return _distance(points_a, points_b) < radius_a + radius_b


def _distance(a, b):
    """The shortest distance between two polylines (a single point counts as one)."""
    return min(_segment_distance(p, q) for p in _segments(a) for q in _segments(b))


def _segments(points):
    return list(zip(points, points[1:])) or [(points[0], points[0])]


def _segment_distance(p, q):
    if _cross(p, q):
        return 0.0
    return min(_to_segment(p[0], q), _to_segment(p[1], q), _to_segment(q[0], p), _to_segment(q[1], p))


def _to_segment(point, segment):
    (ax, ay), (bx, by) = segment
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / length))
    return math.dist(point, (ax + t * dx, ay + t * dy))


def _cross(p, q):
    def side(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    return (
        side(*p, q[0]) * side(*p, q[1]) < 0 and side(*q, p[0]) * side(*q, p[1]) < 0
    )
