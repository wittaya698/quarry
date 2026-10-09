"""The self-test: proof that Quarry's guards can fail.

A Check or Ledger rule that always passed would pass every honest Site too, so
passing proves nothing. The self-test builds a known-good Site with the fake
Agent, exports it, then breaks it in each way below and asserts that the guard
meant for that corruption catches it, by name.

The self-test approves its own Sites as Human("selftest"). It may: they live in
a directory it was handed and nothing else ever reads them (ADR-0004 guards the
user's Sites, not this one's).
"""
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

from quarry.agent import FakeAgent
from quarry.brief import Brief
from quarry.checks import run_checks
from quarry.export import ExportError, export_glb, verify_export, write_tscn
from quarry.identity import Human
from quarry.site import Refused, Site

TESTER = Human("selftest")
_BRIEF = {
    "footprint": [200, 120],
    "waypoints": ["spawn", "cave"],
    "walk_targets": [{"from": "spawn", "to": "cave", "distance": 80, "tolerance": 0.2}],
}


@dataclass(frozen=True)
class Outcome:
    corruption: str
    caught: bool
    detail: str  # what caught it, or what happened instead


class _Missed(Exception):
    """The corruption got through."""


def selftest(workdir):
    """Build the known-good Site in `workdir`, then try every corruption on a copy.
    Raises if the known-good Site itself does not build, export and verify."""
    workdir = Path(workdir)
    stages = _known_good(workdir / "good")
    outcomes = []
    for i, (name, corrupt) in enumerate(CORRUPTIONS.items()):
        try:
            outcomes.append(Outcome(name, True, corrupt(stages, workdir / f"corruption-{i}")))
        except _Missed as missed:
            outcomes.append(Outcome(name, False, str(missed)))
        except Exception as error:  # got past every guard, then broke something else
            outcomes.append(Outcome(name, False, f"not refused, then {type(error).__name__}: {error}"))
    return outcomes


def _known_good(workdir):
    """The Site at each step: Blockout drafted, then both Drafts approved and exported."""
    workdir.mkdir(parents=True)
    site = Site.create(workdir / "site", Brief.from_dict(_BRIEF))
    site.draft(FakeAgent())
    drafted = shutil.copytree(site.path, workdir / "drafted")
    site.approve(1, by=TESTER)
    site.draft_refine_plan(FakeAgent())
    site.approve_refine_plan(1, by=TESTER)
    site.export(workdir / "site.glb")  # re-imported and re-measured before it lands
    write_tscn(workdir / "site.glb")
    return {"drafted": drafted, "done": site.path}


def _copy(stages, stage, workdir):
    workdir.mkdir(parents=True)
    return Site.open(shutil.copytree(stages[stage], workdir / "site"))


def _approved_blockout(site):
    return site.revision(site.approval.revision).blockout


# --- The corruptions ------------------------------------------------------


def _steepened_path(stages, workdir):
    site = _copy(stages, "done", workdir)
    blockout = _approved_blockout(site)
    path = blockout.paths[0]
    (ax, ay), (bx, by) = path.points[0], path.points[-1]
    steep = _raised(site.terrain(), ((ax + bx) / 2, (ay + by) / 2), 5.0)
    return _missed_check(run_checks(site.brief, blockout, steep), f"slope {path.start}→{path.end}")


def _landmark_off_its_pad(stages, workdir):
    site = _copy(stages, "done", workdir)
    blockout = _approved_blockout(site)
    first = blockout.landmarks[0]
    moved = replace(first, position=(first.position[0] + 10, first.position[1]))
    out = workdir / "moved.glb"
    export_glb(site.terrain(), replace(blockout, landmarks=(moved, *blockout.landmarks[1:])), out)
    return _refused(lambda: verify_export(site.terrain(), blockout, out), f"anchor {first.name}")


def _pad_not_flat(stages, workdir):
    site = _copy(stages, "done", workdir)
    blockout = _approved_blockout(site)
    landmark = blockout.landmarks[0]
    tilted = _raised(site.terrain(), landmark.position, 1.0)
    return _missed_check(run_checks(site.brief, blockout, tilted), f"pad {landmark.name}")


def _terrain_without_a_revision(stages, workdir):
    site = _copy(stages, "done", workdir)
    blockout, terrain = _approved_blockout(site), site.terrain()
    out = workdir / "changed.glb"
    export_glb(_raised(terrain, (10.0, 10.0), 0.1), blockout, out)
    return _refused(lambda: verify_export(terrain, blockout, out), "changed without a Revision")


def _approval_by_the_agent(stages, workdir):
    site = _copy(stages, "drafted", workdir)
    return _refused(lambda: site.approve(1, by=FakeAgent()), "only a human can approve")


def _waiver_reused(stages, workdir):
    workdir.mkdir(parents=True)
    far = {**_BRIEF, "walk_targets": [{**_BRIEF["walk_targets"][0], "distance": 160}]}
    site = Site.create(workdir / "site", Brief.from_dict(far))
    site.draft(FakeAgent())
    site.approve(1, by=TESTER, waivers={"walk spawn→cave": "selftest accepts the short way"})
    site.draft_refine_plan(FakeAgent())
    return _refused(lambda: site.approve_refine_plan(1, by=TESTER), "no Waiver for walk spawn→cave")


def _superseded_export(stages, workdir):
    site = _copy(stages, "done", workdir)
    site.reopen(by=TESTER)
    out = workdir / "superseded.glb"
    detail = _refused(lambda: site.export(out), "Superseded")
    if out.exists():
        raise _Missed(f"refused, but {out.name} was written anyway")
    return detail


CORRUPTIONS = {
    "a Path steepened past the Max Walkable Slope": _steepened_path,
    "a Landmark moved off its Pad": _landmark_off_its_pad,
    "Pad flatness broken": _pad_not_flat,
    "Terrain changed without a Revision": _terrain_without_a_revision,
    "an Approval by the Agent": _approval_by_the_agent,
    "a Waiver from Checkpoint #1 reused at Checkpoint #2": _waiver_reused,
    "an Export of Superseded Terrain": _superseded_export,
}


# --- Telling caught from missed -------------------------------------------


def _raised(terrain, point, metres):
    """The Terrain with the height sample nearest `point` raised, and no Revision for it."""
    heights = [list(row) for row in terrain.heights]
    r, c = round(point[1] / terrain.spacing), round(point[0] / terrain.spacing)
    heights[r][c] += metres
    return replace(terrain, heights=tuple(map(tuple, heights)))


def _missed_check(results, check):
    result = next((r for r in results if r.check == check), None)
    if result is None:
        raise _Missed(f"no {check} Check ran")
    space = "" if result.unit == "°" else " "
    if result.passed:
        raise _Missed(f"{check} passed at {result.measured:.1f}{space}{result.unit}")
    return f"{check} missed: {result.measured:.1f}{space}{result.unit} against {result.target:g}{space}{result.unit}"


def _refused(act, words):
    try:
        act()
    except (Refused, ExportError) as refusal:
        if words not in str(refusal):
            raise _Missed(f"refused, but not by this guard: {refusal}") from None
        return str(refusal)
    raise _Missed("allowed")
