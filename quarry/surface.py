"""The Surface: Ground plus Zones, then Cut Paths → the height, and the owning
surface, at any point.

The single definition of height. Checks measure it and the Terrain Builder
builds on it, so a Blockout and its Terrain can never disagree about shape.
Given a Refine Plan, each Zone's edge eases in over its falloff width, shaped
by its slope profile (ADR-0003: the Refine Plan owns both); without one, the
Blockout's coarse Surface has hard edges.

A Cut Path (ADR-0005) lies above every Zone: across its strip the height follows
the Path's own grade, rising evenly between its ends' Pads, which it holds level.
"""
import math

GROUND = "ground"


def surface(blockout, refine_plan=None):
    edges = {}
    if refine_plan is not None:
        edges = {s.surface: (s.falloff_width, s.slope_profile) for s in refine_plan.surfaces}
    zones_only = Surface(blockout.zones, edges)
    landmarks = {l.name: l for l in blockout.landmarks}
    strips = tuple(_Strip(p, landmarks, zones_only) for p in blockout.paths if p.cut)
    return Surface(blockout.zones, edges, strips)


class Surface:
    def __init__(self, zones, edges=None, strips=()):
        self._zones = zones  # in Stacking Order, bottom first
        self._edges = edges or {}  # surface name → (falloff width, slope profile)
        self._strips = strips  # Cut Paths, above every Zone

    def height(self, x, y):
        height = 0.0
        for zone in self._zones:
            weight = self._weight(zone, x, y)
            if weight == 0:
                continue
            own = _profile(zone, x, y)
            if zone.combine == "max":
                height = _lerp(height, max(height, own), weight)
            elif zone.combine == "replace":
                height = _lerp(height, own, weight)
            else:
                height += own * weight
        for strip in self._strips:
            outside, level = strip.locate(x, y)
            weight = self._edge(strip.name, outside, 0.0, outward=True)
            if weight:
                height = _lerp(height, level, weight)
        return height

    def owner(self, x, y):
        """The topmost Zone's name, or "ground"; surface values come from it alone."""
        owner = GROUND
        for zone in self._zones:
            if math.dist(zone.center, (x, y)) < zone.radius:
                owner = zone.name
        for strip in self._strips:
            if strip.locate(x, y)[0] < 0:
                owner = strip.name
        return owner

    def _weight(self, zone, x, y):
        return self._edge(zone.name, math.dist(zone.center, (x, y)), zone.radius)

    def _edge(self, name, d, reach, outward=False):
        """How fully a surface applies d metres from its centre (a Zone's) or its
        centreline (a Cut Path's): 1 inside its reach, 0 outside, a ramp across its
        edge. A Zone's ramp straddles its rim; a Cut Path's lies wholly outside its
        strip, so the trail keeps its exact grade and only the banks ease."""
        width, profile = self._edges.get(name, (0.0, "linear"))
        if width <= 0:
            return 1.0 if d < reach else 0.0
        t = min(max((reach + (width if outward else width / 2) - d) / width, 0.0), 1.0)
        return _RAMPS[profile](t)


class _Strip:
    """A Cut Path's ground: its strip, graded evenly along the centreline, and
    both ends' Pads held level at the height the Zones give their Landmarks."""

    def __init__(self, path, landmarks, zones_only):
        self.name = f"{path.start}→{path.end}"
        self.points = path.points
        self._half_width = path.width / 2
        self._starts = [0.0]  # distance along the centreline at each point
        for a, b in zip(path.points, path.points[1:]):
            self._starts.append(self._starts[-1] + math.dist(a, b))
        start, end = landmarks[path.start], landmarks[path.end]
        self._low, self._high = zones_only.height(*start.position), zones_only.height(*end.position)
        self._pads = ((start.position, start.pad_radius, self._low), (end.position, end.pad_radius, self._high))
        length = self._starts[-1]
        # Level across each Pad, so the Pad stays flat; even between their edges.
        self._flat_start = min(start.pad_radius, length / 2)
        self._rise_length = max(length - self._flat_start - min(end.pad_radius, length / 2), 0.0)

    def locate(self, x, y):
        """(metres outside the strip and its Pads, negative inside; the height there).
        Inside a Pad the Pad wins, wherever the winding strip crosses it."""
        distance, along = self._nearest(x, y)
        found = (distance - self._half_width, self.grade(along))
        for centre, radius, level in self._pads:
            outside = math.dist(centre, (x, y)) - radius - 1e-9  # the rim is the Pad's
            if outside < 0 or outside < found[0]:
                found = (min(outside, found[0]), level)
        return found

    def _nearest(self, x, y):
        """(distance from the centreline, distance along it) at the closest point."""
        best = (math.inf, 0.0)
        for (ax, ay), (bx, by), start in zip(self.points, self.points[1:], self._starts):
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            t = 0.0 if length2 == 0 else min(max(((x - ax) * dx + (y - ay) * dy) / length2, 0.0), 1.0)
            d = math.hypot(x - ax - t * dx, y - ay - t * dy)
            if d < best[0]:
                best = (d, start + t * math.sqrt(length2))
        return best

    def grade(self, along):
        if self._rise_length == 0:
            return self._high if along > self._flat_start else self._low
        t = min(max((along - self._flat_start) / self._rise_length, 0.0), 1.0)
        return _lerp(self._low, self._high, t)


_RAMPS = {
    "linear": lambda t: t,
    "smooth": lambda t: t * t * (3 - 2 * t),
    "steep": lambda t: _RAMPS["smooth"](min(max((t - 0.25) / 0.5, 0.0), 1.0)),
}


def _profile(zone, x, y):
    """The Zone's own height at a point; a dome falls to nothing at its rim."""
    if zone.profile == "dome":
        t = min(math.dist(zone.center, (x, y)) / zone.radius, 1.0)
        return zone.height * (1 + math.cos(math.pi * t)) / 2
    return zone.height


def _lerp(a, b, t):
    return a + (b - a) * t
