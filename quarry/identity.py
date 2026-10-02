"""Who performs an act. Only a Human may Approve, Waive or Reject (ADR-0004).

There is deliberately no setting that lets anything else through: a caller that
is not a Human is refused by the Site, however it got there.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Human:
    name: str


@dataclass(frozen=True)
class Automated:
    """A script, pipe or CI job acting without a person at the keyboard."""

    name: str


@dataclass(frozen=True)
class _Agent:
    name: str = "agent"


AGENT = _Agent()
