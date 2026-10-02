"""Checks: measured comparisons of a Blockout against the Brief's targets.

Checks measure a surface — anything with `height(x, y)` — so the same function
runs on a Blockout's coarse Surface at Checkpoint #1 and on Terrain at #2.
"""
import math
from dataclasses import dataclass

from quarry.surface import surface as blockout_surface

_STEP = 1.0  # metres between samples along a Path
_GRID = 2.0  # metres between samples across the footprint
PAD_MAX_SLOPE = 3.0  # degrees; a Pad steeper than this is not flat enough to build on


@dataclass(frozen=True)
class CheckResult:
    check: str
    unit: str  # "s", "m" or "°"
    target: float
    tolerance: float
    measured: float
    passed: bool
    at_most: bool = False  # the target is a ceiling, not an amount to hit


def run_checks(brief, blockout, surface=None):
    ground = surface or blockout_surface(blockout)
    routes = [p for p in blockout.paths if not p.decorative]
    paths = {(p.start, p.end): p for p in routes}
    results = []
    for target in brief.walk_targets:
        path = paths[(target.start, target.end)]
        length = _length(path.points, ground)
        if target.time is not None:
            unit, goal, measured = "s", target.time, length / brief.walk_speed
        else:
            unit, goal, measured = "m", target.distance, length
        results.append(
            CheckResult(
                check=f"walk {target.start}→{target.end}",
                unit=unit,
                target=goal,
                tolerance=target.tolerance,
                measured=measured,
                passed=abs(measured - goal) <= goal * target.tolerance,
            )
        )
    for path in routes:
        results.append(
            _at_most(f"slope {path.start}→{path.end}", "°", brief.max_walkable_slope, _steepest(path.points, ground))
        )
    for landmark in blockout.landmarks:
        results.append(_at_most(f"pad {landmark.name}", "°", PAD_MAX_SLOPE, _steepest_on_pad(landmark, ground)))
    measures = {"max_slope": ("°", _steepest_anywhere), "max_height": ("m", _highest)}
    for reading in blockout.readings:
        if reading.measure is None:
            continue  # shown with the Blockout, without pass or miss
        unit, measure = measures[reading.measure]
        results.append(_at_most(f"reading {reading.phrase}", unit, reading.limit, measure(brief.footprint, ground)))
    return results


def _at_most(check, unit, limit, measured):
    return CheckResult(check, unit, limit, 0.0, measured, measured <= limit + 1e-9, at_most=True)


def _length(points, ground):
    """Distance along the ground, so a climb is longer than its map length."""
    return sum(math.hypot(run, rise) for run, rise in _steps(points, ground))


def _steepest(points, ground):
    return max((math.degrees(math.atan2(abs(rise), run)) for run, rise in _steps(points, ground)), default=0.0)


def _steps(points, ground):
    """(map distance, height change) for each short step along a polyline."""
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil(math.dist(a, b) / _STEP))
        previous = a
        for i in range(1, count + 1):
            here = (a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count)
            yield math.dist(previous, here), ground.height(*here) - ground.height(*previous)
            previous = here


def _grid(footprint, ground):
    width, depth = footprint
    columns, rows = round(width / _GRID) + 1, round(depth / _GRID) + 1
    return [[ground.height(c * _GRID, r * _GRID) for c in range(columns)] for r in range(rows)]


def _steepest_anywhere(footprint, ground):
    heights = _grid(footprint, ground)
    steepest = 0.0
    for r in range(len(heights) - 1):
        for c in range(len(heights[0]) - 1):
            dx, dy = heights[r][c + 1] - heights[r][c], heights[r + 1][c] - heights[r][c]
            steepest = max(steepest, math.degrees(math.atan(math.hypot(dx, dy) / _GRID)))
    return steepest


def _highest(footprint, ground):
    return max(h for row in _grid(footprint, ground) for h in row)


def _steepest_on_pad(landmark, ground):
    """The steepest step between neighbouring 1 m samples inside the Pad."""
    (x, y), reach = landmark.position, math.floor(landmark.pad_radius)
    inside = {
        (i, j)
        for i in range(-reach, reach + 1)
        for j in range(-reach, reach + 1)
        if math.hypot(i, j) <= landmark.pad_radius
    }
    steepest = 0.0
    for i, j in inside:
        for di, dj in ((1, 0), (0, 1)):
            if (i + di, j + dj) in inside:
                rise = ground.height(x + i + di, y + j + dj) - ground.height(x + i, y + j)
                steepest = max(steepest, math.degrees(math.atan(abs(rise))))
    return steepest
