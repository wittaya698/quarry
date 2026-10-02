"""The Blockout: a coarse layout of a Site, every choice carrying a Reason."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Reason:
    author: str  # "ai" or "human"
    text: str


@dataclass(frozen=True)
class Landmark:
    waypoint: str
    position: tuple[float, float]
    reason: Reason


@dataclass(frozen=True)
class Path:
    start: str
    end: str
    points: tuple[tuple[float, float], ...]
    reason: Reason


@dataclass(frozen=True)
class Blockout:
    landmarks: tuple[Landmark, ...]
    paths: tuple[Path, ...]

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(
            landmarks=tuple(
                Landmark(l["waypoint"], tuple(l["position"]), Reason(**l["reason"]))
                for l in data["landmarks"]
            ),
            paths=tuple(
                Path(p["start"], p["end"], tuple(map(tuple, p["points"])), Reason(**p["reason"]))
                for p in data["paths"]
            ),
        )
