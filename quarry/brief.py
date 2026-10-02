"""The Brief: what the user asked for, read from a JSON file."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WalkTarget:
    start: str
    end: str
    time: float | None  # seconds; exactly one of time and distance is set
    distance: float | None  # metres
    tolerance: float  # fraction of the target, e.g. 0.1 for ±10%


@dataclass(frozen=True)
class Brief:
    footprint: tuple[float, float]  # metres, x by y
    waypoints: tuple[str, ...]
    walk_targets: tuple[WalkTarget, ...]
    mood: str
    walk_speed: float = 1.4  # metres per second
    max_walkable_slope: float = 30.0  # degrees

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    def to_dict(self):
        targets = []
        for t in self.walk_targets:
            target = {"from": t.start, "to": t.end, "tolerance": t.tolerance}
            target.update({"time": t.time} if t.time is not None else {"distance": t.distance})
            targets.append(target)
        return {
            "footprint": list(self.footprint),
            "waypoints": list(self.waypoints),
            "walk_targets": targets,
            "mood": self.mood,
            "walk_speed": self.walk_speed,
            "max_walkable_slope": self.max_walkable_slope,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            footprint=tuple(data["footprint"]),
            waypoints=tuple(data["waypoints"]),
            walk_targets=tuple(
                WalkTarget(
                    t["from"], t["to"], t.get("time"), t.get("distance"), t.get("tolerance", 0.1)
                )
                for t in data.get("walk_targets", [])
            ),
            mood=data.get("mood", ""),
            walk_speed=data.get("walk_speed", 1.4),
            max_walkable_slope=data.get("max_walkable_slope", 30.0),
        )
