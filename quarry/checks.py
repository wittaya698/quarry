"""Checks: measured comparisons of a Blockout against the Brief's targets.

Checks measure a surface — anything with `height(x, y)` — so the same function
runs on a Blockout's coarse Surface at Checkpoint #1 and on Terrain at #2.
"""
import heapq
import math
from dataclasses import dataclass

from quarry.surface import surface as blockout_surface

_STEP = 1.0  # metres between samples along a Path
_GRID = 2.0  # metres between samples across the footprint
PAD_MAX_SLOPE = 3.0  # degrees; a Pad steeper than this is not flat enough to build on
_ROUTE_GRID = 1.0  # metres between the points a Shortcut may step through
# A Shortcut steps to any of 8 neighbours, so it can run up to ~8% longer than
# the true fastest route: the Check errs towards passing a near-miss.
_MOVES = [(dc, dr, math.hypot(dc, dr) * _ROUTE_GRID) for dc in (-1, 0, 1) for dr in (-1, 0, 1) if dc or dr]


@dataclass(frozen=True)
class CheckResult:
    check: str
    unit: str  # "s", "m" or "°"
    target: float
    tolerance: float
    measured: float | None  # None only for a Shortcut Check that found no walkable route
    passed: bool
    at_most: bool = False  # the target is a ceiling, not an amount to hit
    at_least: bool = False  # the target, less its tolerance, is a floor
    route: tuple[tuple[float, float], ...] | None = None  # a missed Shortcut's way round


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
    for target in brief.walk_targets:
        if target.no_shortcut:
            results.append(_shortcut(brief, blockout, target, ground))
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


def _shortcut(brief, blockout, target, ground):
    """The fastest walkable route anywhere on the ground, against the Walk Target's floor."""
    places = {l.name: l.position for l in blockout.landmarks}
    length, route = _fastest_route(brief, places[target.start], places[target.end], ground)
    if target.time is not None:
        unit, goal, measured = "s", target.time, None if length is None else length / brief.walk_speed
    else:
        unit, goal, measured = "m", target.distance, length
    passed = measured is None or measured >= goal * (1 - target.tolerance) - 1e-9
    return CheckResult(
        f"shortcut {target.start}→{target.end}", unit, goal, target.tolerance, measured, passed,
        at_least=True, route=None if passed else route,
    )


def _fastest_route(brief, start, end, ground):
    """(length along the ground, points) of the shortest route a player can walk
    from start to end: never climbing onto ground steeper than the Max Walkable
    Slope, but dropping down any slope. (None, None) if there is none.

    Steepness is the ground's, in its steepest direction, as a game's character
    controller judges it, so switchbacks across a steep face do not climb it."""
    width, depth = brief.footprint
    columns, rows = math.floor(width / _ROUTE_GRID) + 1, math.floor(depth / _ROUTE_GRID) + 1
    heights = [ground.height(c * _ROUTE_GRID, r * _ROUTE_GRID) for r in range(rows) for c in range(columns)]
    climb = math.tan(math.radians(brief.max_walkable_slope))
    steep = [_gradient(heights, columns, rows, i) > climb + 1e-9 for i in range(len(heights))]

    def node(point):
        c = min(max(round(point[0] / _ROUTE_GRID), 0), columns - 1)
        r = min(max(round(point[1] / _ROUTE_GRID), 0), rows - 1)
        return r * columns + c

    source, goal = node(start), node(end)
    best, previous = {source: 0.0}, {}
    queue = [(0.0, source)]
    while queue:
        length, here = heapq.heappop(queue)
        if here == goal:
            break
        if length > best[here]:
            continue
        r, c = divmod(here, columns)
        for dc, dr, run in _MOVES:
            nc, nr = c + dc, r + dr
            if not (0 <= nc < columns and 0 <= nr < rows):
                continue
            there = nr * columns + nc
            rise = heights[there] - heights[here]
            if rise > 0 and (rise > run * climb + 1e-9 or steep[here] or steep[there]):
                continue  # too steep to climb; any drop is fine
            step = length + math.hypot(run, rise)
            if step < best.get(there, math.inf):
                best[there], previous[there] = step, here
                heapq.heappush(queue, (step, there))
    if goal not in best:
        return None, None
    nodes = [goal]
    while nodes[-1] != source:
        nodes.append(previous[nodes[-1]])
    points = [(n % columns * _ROUTE_GRID, n // columns * _ROUTE_GRID) for n in reversed(nodes)]
    return best[goal], _corners(points)


def _gradient(heights, columns, rows, i):
    """The ground's steepest rise per metre at a grid point."""
    r, c = divmod(i, columns)
    left, right = max(c - 1, 0), min(c + 1, columns - 1)
    below, above = max(r - 1, 0), min(r + 1, rows - 1)
    dx = (heights[r * columns + right] - heights[r * columns + left]) / ((right - left) * _ROUTE_GRID)
    dy = (heights[above * columns + c] - heights[below * columns + c]) / ((above - below) * _ROUTE_GRID)
    return math.hypot(dx, dy)


def _corners(points):
    """The route with every point that only continues a straight run dropped."""
    kept = points[:1]
    for here, after in zip(points[1:], points[2:]):
        before = kept[-1]
        if (here[0] - before[0]) * (after[1] - here[1]) != (here[1] - before[1]) * (after[0] - here[0]):
            kept.append(here)
    return tuple(kept + points[-1:]) if len(points) > 1 else tuple(points)


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
