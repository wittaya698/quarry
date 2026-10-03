"""The Surface: Ground plus Zones → the height, and the owning Zone, at any point.

The single definition of height. Checks measure it and the Terrain Builder
builds on it, so a Blockout and its Terrain can never disagree about shape.
Given a Refine Plan, each Zone's edge eases in over its falloff width, shaped
by its slope profile (ADR-0003: the Refine Plan owns both); without one, the
Blockout's coarse Surface has hard edges.
"""
import math

GROUND = "ground"


def surface(blockout, refine_plan=None):
    edges = {}
    if refine_plan is not None:
        edges = {s.surface: (s.falloff_width, s.slope_profile) for s in refine_plan.surfaces}
    return Surface(blockout.zones, edges)


class Surface:
    def __init__(self, zones, edges=None):
        self._zones = zones  # in Stacking Order, bottom first
        self._edges = edges or {}  # Zone name → (falloff width, slope profile)

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
        return height

    def owner(self, x, y):
        """The topmost Zone's name, or "ground"; surface values come from it alone."""
        owner = GROUND
        for zone in self._zones:
            if math.dist(zone.center, (x, y)) < zone.radius:
                owner = zone.name
        return owner

    def _weight(self, zone, x, y):
        """How fully the Zone applies here: 1 inside, 0 outside, a ramp across its edge."""
        d = math.dist(zone.center, (x, y))
        width, profile = self._edges.get(zone.name, (0.0, "linear"))
        if width <= 0:
            return 1.0 if d < zone.radius else 0.0
        t = min(max((zone.radius + width / 2 - d) / width, 0.0), 1.0)
        return _RAMPS[profile](t)


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
