"""The Blockout: a coarse layout of a Site, every choice carrying a Reason."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Reason:
    author: str  # "ai" or "human"
    text: str


@dataclass(frozen=True)
class Landmark:
    name: str  # a Waypoint's name, or the AI's own name for one it chose
    position: tuple[float, float]
    reason: Reason
    pad_radius: float = 6.0  # metres of flat ground the Landmark stands on
    ai_chosen: bool = False  # the AI added it; the Brief did not ask for it


@dataclass(frozen=True)
class Path:
    start: str
    end: str
    points: tuple[tuple[float, float], ...]
    reason: Reason
    decorative: bool = False  # drawn for looks; never measured


@dataclass(frozen=True)
class Zone:
    name: str
    center: tuple[float, float]
    radius: float  # metres; a Zone is a disc
    height: float  # metres; negative for a lake
    profile: str  # "dome" (a smooth hill) or "flat" (a plateau, or a lake)
    combine: str  # Combine Mode: "add", "max" or "replace"
    reason: Reason


@dataclass(frozen=True)
class Reading:
    """What the AI took a mood phrase to mean. A measurable Reading becomes a Check."""
    phrase: str  # words from the Brief's mood, e.g. "gentle hills"
    meaning: str  # the interpretation, in words
    measure: str | None  # "max_slope" (°) or "max_height" (m); None if it cannot be measured
    limit: float | None
    reason: Reason


@dataclass(frozen=True)
class Blockout:
    landmarks: tuple[Landmark, ...]
    paths: tuple[Path, ...]
    zones: tuple[Zone, ...] = ()  # in Stacking Order, bottom first
    readings: tuple[Reading, ...] = ()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(
            landmarks=tuple(
                Landmark(**{**l, "position": tuple(l["position"]), "reason": Reason(**l["reason"])})
                for l in data["landmarks"]
            ),
            paths=tuple(
                Path(**{**p, "points": tuple(map(tuple, p["points"])), "reason": Reason(**p["reason"])})
                for p in data["paths"]
            ),
            zones=tuple(
                Zone(**{**z, "center": tuple(z["center"]), "reason": Reason(**z["reason"])})
                for z in data.get("zones", [])
            ),
            readings=tuple(
                Reading(**{**r, "reason": Reason(**r["reason"])}) for r in data.get("readings", [])
            ),
        )
