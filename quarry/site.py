"""A Site: one Brief and its linear history of Revisions and human acts.

History lives in the Site's directory as an append-only log, one JSON entry per
line. Nothing in it is ever rewritten or deleted.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from quarry.blockout import Blockout
from quarry.brief import Brief
from quarry.checks import run_checks
from quarry.identity import Human


class Refused(Exception):
    """A Checkpoint act the Site's rules do not allow."""


@dataclass(frozen=True)
class Revision:
    number: int
    blockout: Blockout
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


class Site:
    def __init__(self, path, brief):
        self.path = Path(path)
        self.brief = brief
        self._revisions = []
        self.approval = None
        self.rejections = []

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

    # --- Drafts -----------------------------------------------------------

    def draft(self, agent):
        self._append_revision(agent.draft_blockout(self.brief))

    def revive(self, number):
        self._append_revision(self.revision(number).blockout, revived_from=number)

    def revision(self, number):
        if not 1 <= number <= len(self._revisions):
            raise Refused(f"no Revision {number}; this Site has {len(self._revisions)}")
        return self._revisions[number - 1]

    @property
    def current_revision(self):
        """The latest Revision, or None before the first Draft."""
        return self._revisions[-1] if self._revisions else None

    @property
    def checkpoint(self):
        return 1 if self.approval is None else 2

    def checks(self):
        return run_checks(self.brief, self.current_revision.blockout)

    # --- Human acts -------------------------------------------------------

    def approve(self, number, by, waivers=None):
        _require_human(by, "approve")
        self.revision(number)
        waivers = dict(waivers or {})
        current = self.current_revision.number
        if number != current:
            raise Refused(f"cannot approve Revision {number}: Revision {current} is current")
        if any(r.revision == number for r in self.rejections):
            raise Refused(f"cannot approve Revision {number}: it was rejected; revive it first")
        unwaived = [r.check for r in self.checks() if not r.passed and r.check not in waivers]
        if unwaived:
            raise Refused(f"cannot approve Revision {number}: no Waiver for {', '.join(unwaived)}")
        self._record(
            {"kind": "approval", "revision": number, "by": by.name, "at": _now(), "waivers": waivers}
        )

    def reject(self, number, by, note):
        _require_human(by, "reject")
        self.revision(number)
        if not note.strip():
            raise Refused("a Rejection needs a note saying what was wrong")
        self._record(
            {"kind": "rejection", "revision": number, "by": by.name, "at": _now(), "note": note.strip()}
        )

    # --- History ----------------------------------------------------------

    def _append_revision(self, blockout, revived_from=None):
        if self.approval is not None:
            raise Refused(f"the Blockout is approved at Revision {self.approval.revision}")
        self._record(
            {
                "kind": "revision",
                "number": len(self._revisions) + 1,
                "blockout": blockout.to_dict(),
                "revived_from": revived_from,
            }
        )

    def _record(self, entry):
        with open(self.path / "history.jsonl", "a") as log:
            log.write(json.dumps(entry) + "\n")
        self._apply(entry)

    def _apply(self, entry):
        kind = entry["kind"]
        if kind == "revision":
            blockout = Blockout.from_dict(entry["blockout"])
            self._revisions.append(Revision(entry["number"], blockout, entry["revived_from"]))
        elif kind == "approval":
            at = datetime.fromisoformat(entry["at"])
            self.approval = Approval(entry["revision"], Human(entry["by"]), at, entry["waivers"])
        elif kind == "rejection":
            at = datetime.fromisoformat(entry["at"])
            self.rejections.append(Rejection(entry["revision"], Human(entry["by"]), at, entry["note"]))


def _require_human(caller, act):
    if not isinstance(caller, Human):
        raise Refused(f"only a human can {act}; refused from {caller!r}")


def _now():
    return datetime.now(timezone.utc).isoformat()
