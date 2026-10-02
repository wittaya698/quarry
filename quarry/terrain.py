"""The Terrain Builder: approved Blockout + Refine Plan → Terrain, by code alone.

A pure function (ADR-0001). The only randomness is a hash of the Refine Plan's
seed, so the same inputs give byte-identical Terrain on any machine.
"""
import struct
from dataclasses import dataclass

SPACING = 2.0  # metres between height samples
_CELL = 16.0  # metres per roughness noise cell
_MASK = 0xFFFFFFFF


@dataclass(frozen=True)
class Terrain:
    extent: tuple[float, float]  # metres, x by y; matches the Brief's footprint
    spacing: float
    heights: tuple[tuple[float, ...], ...]  # heights[row][column]; row is y, column is x
    vegetation: tuple[tuple[float, ...], ...]  # density 0 to 1 at each sample
    blockout_revision: int
    refine_plan_revision: int

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
    [ground] = refine_plan_revision.plan.surfaces
    heights = tuple(
        tuple(ground.roughness * _noise(ground.seed, c * SPACING, r * SPACING) for c in range(columns))
        for r in range(rows)
    )
    vegetation = tuple((ground.vegetation_density,) * columns for _ in range(rows))
    return Terrain(
        (width, depth), SPACING, heights, vegetation, blockout_revision.number, refine_plan_revision.number
    )


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
