"""A Site: one Brief and its linear history of Revisions and human acts.

History lives in the Site's directory as an append-only log, one JSON entry per
line. Nothing in it is ever rewritten or deleted.

Two Drafts pass a Checkpoint each — the Blockout, then the Refine Plan — under
the same rules, so both are kept by one `_Stage`.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from quarry.blockout import Blockout
from quarry.brief import Brief
from quarry.checks import run_checks
from quarry.export import export_glb, verify_export
from quarry.identity import Human
from quarry.refine import RefinePlan
from quarry.terrain import build_terrain


class Refused(Exception):
    """A Checkpoint act the Site's rules do not allow."""


@dataclass(frozen=True)
class Revision:
    number: int
    blockout: Blockout
    revived_from: int | None = None


@dataclass(frozen=True)
class RefinePlanRevision:
    number: int
    plan: RefinePlan
    revived_from: int | None = None


@dataclass(frozen=True)
class Approval:
    revision: int
    by: Human
    at: datetime
    waivers: dict[str, str]  # missed Check → why it is accepted anyway


@dataclass(frozen=True)
class Rejection:
    revision: int
    by: Human
    at: datetime
    note: str  # what was wrong; feeds the next Draft


class _Stage:
    """One Draft's Revisions and the human acts on them."""

    def __init__(self, key, name, revision_type, field, draft_type):
        self.key, self.name = key, name  # key tags history entries; name is for people
        self.revision_type, self.field, self.draft_type = revision_type, field, draft_type
        self.revisions = []
        self.approval = None
        self.rejections = []

    def revision(self, number):
        if not 1 <= number <= len(self.revisions):
            raise Refused(f"no Revision {number} of the {self.name}; it has {len(self.revisions)}")
        return self.revisions[number - 1]

    @property
    def current(self):
        return self.revisions[-1] if self.revisions else None

    def is_rejected(self, number):
        return any(r.revision == number for r in self.rejections)

    def refuse_revision(self):
        if self.approval is not None:
            raise Refused(f"the {self.name} is approved at Revision {self.approval.revision}")

    def refuse_approval(self, number, checks, waivers):
        current = self.current.number
        if number != current:
            raise Refused(f"cannot approve Revision {number}: Revision {current} is current")
        if self.is_rejected(number):
            raise Refused(f"cannot approve Revision {number}: it was rejected; revive it first")
        unwaived = [r.check for r in checks if not r.passed and r.check not in waivers]
        if unwaived:
            raise Refused(f"cannot approve Revision {number}: no Waiver for {', '.join(unwaived)}")

    def refuse_rejection(self, number, note):
        self.revision(number)
        if not note.strip():
            raise Refused("a Rejection needs a note saying what was wrong")

    def apply(self, entry):
        kind = entry["kind"]
        if kind == "revision":
            draft = self.draft_type.from_dict(entry[self.field])
            self.revisions.append(self.revision_type(entry["number"], draft, entry["revived_from"]))
        elif kind == "approval":
            at = datetime.fromisoformat(entry["at"])
            self.approval = Approval(entry["revision"], Human(entry["by"]), at, entry["waivers"])
        elif kind == "rejection":
            at = datetime.fromisoformat(entry["at"])
            self.rejections.append(Rejection(entry["revision"], Human(entry["by"]), at, entry["note"]))


class Site:
    def __init__(self, path, brief):
        self.path = Path(path)
        self.brief = brief
        self._blockout = _Stage("blockout", "Blockout", Revision, "blockout", Blockout)
        self._refine = _Stage("refine_plan", "Refine Plan", RefinePlanRevision, "plan", RefinePlan)

    @classmethod
    def create(cls, path, brief):
        """A new Site. Refuses a directory that already exists, so no history
        is ever written over."""
        path = Path(path)
        path.mkdir(parents=True)
        (path / "brief.json").write_text(json.dumps(brief.to_dict(), indent=2))
        (path / "history.jsonl").touch()
        return cls(path, brief)

    @classmethod
    def open(cls, path):
        path = Path(path)
        site = cls(path, Brief.load(path / "brief.json"))
        for line in (path / "history.jsonl").read_text().splitlines():
            site._apply(json.loads(line))
        return site

    @property
    def checkpoint(self):
        """1 while the Blockout is a Draft, 2 while the Refine Plan is, then "done"."""
        if self.approval is None:
            return 1
        return 2 if self.refine_plan_approval is None else "done"

    # --- Checkpoint #1: the Blockout --------------------------------------

    def draft(self, agent):
        self._append(self._blockout, agent.draft_blockout(self.brief))

    def revive(self, number):
        self._append(self._blockout, self.revision(number).blockout, revived_from=number)

    def revision(self, number):
        return self._blockout.revision(number)

    @property
    def current_revision(self):
        """The latest Blockout Revision, or None before the first Draft."""
        return self._blockout.current

    @property
    def approval(self):
        return self._blockout.approval

    @property
    def rejections(self):
        return self._blockout.rejections

    def checks(self):
        return run_checks(self.brief, self.current_revision.blockout)

    def approve(self, number, by, waivers=None):
        self._approve(self._blockout, number, by, waivers, self.checks)

    def reject(self, number, by, note):
        self._reject(self._blockout, number, by, note)

    # --- Checkpoint #2: the Refine Plan -----------------------------------

    def draft_refine_plan(self, agent):
        if self.approval is None:
            raise Refused("a Refine Plan needs an approved Blockout")
        blockout = self.revision(self.approval.revision).blockout
        self._append(self._refine, agent.draft_refine_plan(self.brief, blockout))

    @property
    def current_refine_plan(self):
        """The latest Refine Plan Revision, or None before the first."""
        return self._refine.current

    def revive_refine_plan(self, number):
        self._append(self._refine, self.refine_plan(number).plan, revived_from=number)

    def refine_plan(self, number):
        return self._refine.revision(number)

    @property
    def refine_plan_approval(self):
        return self._refine.approval

    @property
    def refine_plan_rejections(self):
        return self._refine.rejections

    def approve_refine_plan(self, number, by, waivers=None):
        # Checks on Terrain arrive with issue 05; until then nothing can miss here.
        self._approve(self._refine, number, by, waivers, lambda: [])

    def reject_refine_plan(self, number, by, note):
        self._reject(self._refine, number, by, note)

    def terrain(self):
        """Terrain built from the approved Blockout and the current Refine Plan."""
        if self.current_refine_plan is None:
            raise Refused("Terrain needs a Refine Plan; draft one first")
        blockout = self.revision(self.approval.revision)
        return build_terrain(self.brief, blockout, self.current_refine_plan)

    def export(self, path):
        """Write the Site's Export: only from Terrain whose Refine Plan is approved.
        The file is re-imported and re-measured before it takes the given name,
        so a failed Export never leaves a `.glb` behind."""
        if self.refine_plan_approval is None:
            raise Refused("Export needs an approved Refine Plan")
        path = Path(path)
        terrain = self.terrain()
        pending = path.with_name(path.name + ".partial")
        try:
            export_glb(terrain, pending)
            verify_export(terrain, pending)
        except BaseException:
            pending.unlink(missing_ok=True)
            raise
        pending.replace(path)

    # --- Human acts, the same at both Checkpoints -------------------------

    def _approve(self, stage, number, by, waivers, checks):
        _require_human(by, "approve")
        waivers = dict(waivers or {})
        stage.revision(number)  # before the Checks, which need a Revision to measure
        stage.refuse_approval(number, checks(), waivers)
        self._record(
            stage,
            {"kind": "approval", "revision": number, "by": by.name, "at": _now(), "waivers": waivers},
        )

    def _reject(self, stage, number, by, note):
        _require_human(by, "reject")
        stage.refuse_rejection(number, note)
        self._record(
            stage,
            {"kind": "rejection", "revision": number, "by": by.name, "at": _now(), "note": note.strip()},
        )

    # --- History ----------------------------------------------------------

    def _append(self, stage, draft, revived_from=None):
        stage.refuse_revision()
        self._record(
            stage,
            {
                "kind": "revision",
                "number": len(stage.revisions) + 1,
                stage.field: draft.to_dict(),
                "revived_from": revived_from,
            },
        )

    def _record(self, stage, entry):
        entry = {"stage": stage.key, **entry}
        with open(self.path / "history.jsonl", "a") as log:
            log.write(json.dumps(entry) + "\n")
        self._apply(entry)

    def _apply(self, entry):
        stage = self._refine if entry.get("stage") == "refine_plan" else self._blockout
        stage.apply(entry)


def _require_human(caller, act):
    if not isinstance(caller, Human):
        raise Refused(f"only a human can {act}; refused from {caller!r}")


def _now():
    return datetime.now(timezone.utc).isoformat()
