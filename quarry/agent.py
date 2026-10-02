"""The Agent port, and a fake that drafts without an LLM."""
import math

from quarry.blockout import Blockout, Landmark, Path, Reason


class FakeAgent:
    """Places Waypoints on a ring around the footprint's centre and joins each
    Walk Target with a straight Path. Deterministic, so tests know the answer."""

    def draft_blockout(self, brief, rejection_note=None):
        width, depth = brief.footprint
        radius = min(width, depth) / 3
        landmarks = {}
        for i, name in enumerate(brief.waypoints):
            angle = 2 * math.pi * i / len(brief.waypoints)
            position = (width / 2 + radius * math.cos(angle), depth / 2 + radius * math.sin(angle))
            landmarks[name] = Landmark(name, position, Reason("ai", f"placed {name} on the ring"))
        paths = tuple(
            Path(
                t.start,
                t.end,
                (landmarks[t.start].position, landmarks[t.end].position),
                Reason("ai", f"straight route from {t.start} to {t.end}"),
            )
            for t in brief.walk_targets
        )
        return Blockout(tuple(landmarks.values()), paths)
