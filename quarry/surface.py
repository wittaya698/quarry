"""The Surface: Ground plus Zones → the height, and the owning Zone, at any point.

The single definition of height. Checks measure it and the Terrain Builder
builds on it, so a Blockout and its Terrain can never disagree about shape.
"""
import math

GROUND = "ground"


def surface(blockout):
    return Surface(blockout.zones)


class Surface:
    def __init__(self, zones):
        self._zones = zones  # in Stacking Order, bottom first

    def height(self, x, y):
        height = 0.0
        for zone in self._covering(x, y):
            own = _profile(zone, x, y)
            if zone.combine == "max":
                height = max(height, own)
            elif zone.combine == "replace":
                height = own
            else:
                height += own
        return height

    def owner(self, x, y):
        """The topmost Zone's name, or "ground"; surface values come from it alone."""
        owner = GROUND
        for zone in self._covering(x, y):
            owner = zone.name
        return owner

    def _covering(self, x, y):
        return (z for z in self._zones if math.dist(z.center, (x, y)) < z.radius)


def _profile(zone, x, y):
    """The Zone's own height at a point inside it."""
    if zone.profile == "dome":
        t = math.dist(zone.center, (x, y)) / zone.radius
        return zone.height * (1 + math.cos(math.pi * t)) / 2
    return zone.height
