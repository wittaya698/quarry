"""Checks: measured comparisons of a Blockout against the Brief's targets."""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    check: str
    unit: str  # "s" or "m"
    target: float
    tolerance: float
    measured: float
    passed: bool


def run_checks(brief, blockout):
    paths = {(p.start, p.end): p for p in blockout.paths}
    results = []
    for target in brief.walk_targets:
        path = paths[(target.start, target.end)]
        length = _length(path.points)
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
    return results


def _length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))
