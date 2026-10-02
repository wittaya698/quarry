"""The Refine Plan: how each surface of an approved Blockout looks up close.

It owns only what ADR-0003 gives it — slope profile, falloff width, roughness,
seed and vegetation density. Where things are and how big belongs to the Blockout.
"""
from dataclasses import asdict, dataclass

from quarry.blockout import Reason


@dataclass(frozen=True)
class Refinement:
    surface: str  # "ground", or a Zone's name
    slope_profile: str  # "linear", "smooth" or "steep"
    falloff_width: float  # metres
    roughness: float  # metres of height noise
    seed: int  # the only source of randomness in Terrain
    vegetation_density: float  # 0 to 1
    reason: Reason


@dataclass(frozen=True)
class RefinePlan:
    surfaces: tuple[Refinement, ...]

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(
            tuple(
                Refinement(**{**s, "reason": Reason(**s["reason"])}) for s in data["surfaces"]
            )
        )
