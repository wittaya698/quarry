"""The Terrain Builder: approved Blockout + Refine Plan → Terrain, by code alone.

A pure function (ADR-0001). The only randomness is a hash of the Refine Plan's
seed, so the same inputs give byte-identical Terrain on any machine.
"""
import struct
from dataclasses import dataclass

from quarry.surface import surface

SPACING = 2.0  # metres between height samples
_CELL = 16.0  # metres per roughness noise cell
_MASK = 0xFFFFFFFF
_PAD_MARGIN = 1.5 * SPACING  # flat beyond the Pad's edge, so interpolation inside it stays flat
_PAD_BLEND = 6.0  # metres over which a flattened Pad eases back into the natural ground


@dataclass(frozen=True)
class Terrain:
    extent: tuple[float, float]  # metres, x by y; matches the Brief's footprint
    spacing: float
    heights: tuple[tuple[float, ...], ...]  # heights[row][column]; row is y, column is x
    vegetation: tuple[tuple[float, ...], ...]  # density 0 to 1 at each sample
    blockout_revision: int
    refine_plan_revision: int

    def height(self, x, y):
        """Height between samples, interpolated, so Checks can measure Terrain
        exactly as they measure a Blockout."""
        rows, columns = len(self.heights), len(self.heights[0])
        u = min(max(x / self.spacing, 0), columns - 1)
        v = min(max(y / self.spacing, 0), rows - 1)
        c, r = min(int(u), columns - 2), min(int(v), rows - 2)
        top = _lerp(self.heights[r][c], self.heights[r][c + 1], u - c)
        bottom = _lerp(self.heights[r + 1][c], self.heights[r + 1][c + 1], u - c)
        return _lerp(top, bottom, v - r)

    def to_bytes(self):
        rows, columns = len(self.heights), len(self.heights[0])
        header = struct.pack(
            "<ddd3I", *self.extent, self.spacing, rows, self.blockout_revision, self.refine_plan_revision
        )
        samples = [v for grid in (self.heights, self.vegetation) for row in grid for v in row]
        return header + struct.pack(f"<I{len(samples)}d", columns, *samples)


def build_terrain(brief, blockout_revision, refine_plan_revision):
    width, depth = brief.footprint
    columns, rows = round(width / SPACING) + 1, round(depth / SPACING) + 1
    shape = surface(blockout_revision.blockout, refine_plan_revision.plan)
    refinements = {s.surface: s for s in refine_plan_revision.plan.surfaces}
    pads = [(l.position, l.pad_radius + _PAD_MARGIN, shape.height(*l.position)) for l in blockout_revision.blockout.landmarks]
    heights, vegetation = [], []
    for r in range(rows):
        height_row, vegetation_row = [], []
        for c in range(columns):
            x, y = c * SPACING, r * SPACING
            # Surface values come from the topmost Zone alone, never a blend.
            own = refinements[shape.owner(x, y)]
            height = shape.height(x, y) + own.roughness * _noise(own.seed, x, y)
            height_row.append(_flatten_pads(pads, x, y, height))
            vegetation_row.append(own.vegetation_density)
        heights.append(tuple(height_row))
        vegetation.append(tuple(vegetation_row))
    heights, vegetation = tuple(heights), tuple(vegetation)
    return Terrain(
        (width, depth), SPACING, heights, vegetation, blockout_revision.number, refine_plan_revision.number
    )


def _flatten_pads(pads, x, y, height):
    """Hold each Pad level at its centre's Surface height, easing out beyond it."""
    for (px, py), flat_radius, level in pads:
        d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
        if d <= flat_radius:
            height = level
        elif d < flat_radius + _PAD_BLEND:
            height = _lerp(level, height, _smooth((d - flat_radius) / _PAD_BLEND))
    return height


def _noise(seed, x, y):
    """Smooth value noise in [-1, 1]."""
    i, j = int(x // _CELL), int(y // _CELL)
    fx, fy = _smooth(x / _CELL - i), _smooth(y / _CELL - j)
    top = _lerp(_lattice(seed, i, j), _lattice(seed, i + 1, j), fx)
    bottom = _lerp(_lattice(seed, i, j + 1), _lattice(seed, i + 1, j + 1), fx)
    return _lerp(top, bottom, fy)


def _lattice(seed, i, j):
    h = (seed * 0x9E3779B1 + i * 0x85EBCA77 + j * 0xC2B2AE3D) & _MASK
    for shift, multiplier in ((16, 0x7FEB352D), (15, 0x846CA68B)):
        h = ((h ^ (h >> shift)) * multiplier) & _MASK
    h ^= h >> 16
    return h / _MASK * 2 - 1


def _smooth(t):
    return t * t * (3 - 2 * t)


def _lerp(a, b, t):
    return a + (b - a) * t
