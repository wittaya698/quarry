"""The Agent port's Claude adapters' shared prompts and schemas, and the API
adapter: drafts Blockouts and Refine Plans with the latest Claude model. The
API key comes from the environment (ANTHROPIC_API_KEY).

The model is offered no tools, so it has nothing to call: it can only answer
with a Draft as JSON, which the Site then validates before anything is kept.
"""
import json

from quarry.validation import InvalidDraft

MODEL = "claude-opus-5-5"  # both Claude adapters draft with this, at this effort
EFFORT = "high"


class AgentUnavailable(Exception):
    """Claude cannot be reached as configured, e.g. no API key in the environment."""

_REASON = {
    "type": "object",
    "properties": {"author": {"type": "string", "enum": ["ai"]}, "text": {"type": "string"}},
    "required": ["author", "text"],
    "additionalProperties": False,
}
_POINT = {"type": "array", "items": {"type": "number"}}


def _object(**properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


BLOCKOUT_SCHEMA = _object(
    landmarks={"type": "array", "items": _object(
        name={"type": "string"},
        position=_POINT,
        reason=_REASON,
        pad_radius={"type": "number"},
        ai_chosen={"type": "boolean"},
    )},
    paths={"type": "array", "items": _object(
        start={"type": "string"},
        end={"type": "string"},
        points={"type": "array", "items": _POINT},
        reason=_REASON,
        decorative={"type": "boolean"},
    )},
    zones={"type": "array", "items": _object(
        name={"type": "string"},
        center=_POINT,
        radius={"type": "number"},
        height={"type": "number"},
        profile={"type": "string", "enum": ["dome", "flat"]},
        combine={"type": "string", "enum": ["add", "max", "replace"]},
        reason=_REASON,
    )},
    readings={"type": "array", "items": _object(
        phrase={"type": "string"},
        meaning={"type": "string"},
        measure={"anyOf": [{"type": "string", "enum": ["max_slope", "max_height"]}, {"type": "null"}]},
        limit={"anyOf": [{"type": "number"}, {"type": "null"}]},
        reason=_REASON,
    )},
)

BLOCKOUT_SYSTEM = """\
You draft Blockouts for Quarry, a terrain-authoring tool. A Blockout is a coarse
layout of a Site that a human reviews and approves before anything is built.

Coordinates are metres on the Brief's footprint: x from 0 to width, y from 0 to depth.

- Place every Waypoint the Brief names as exactly one Landmark with that name
  (ai_chosen false). You may add Landmarks of your own, marked ai_chosen true.
  pad_radius is the flat buildable area each Landmark stands on, in metres.
- Draw exactly one Path (decorative false) for every Walk Target, from its start
  Waypoint to its end, as a polyline whose first and last points are the two
  Landmarks' positions. Its walk is measured along the ground at the Brief's Walk
  Speed, slope included. Decorative Paths are allowed and never measured.
- Zones are discs on the Ground: dome is a smooth hill, flat a plateau (or a lake,
  with negative height). Combine Mode: add, max or replace. Zones are listed in
  Stacking Order, bottom first.
- Give one Reading per mood phrase you act on. A Reading is measurable when it
  becomes a ceiling: max_slope (degrees) or max_height (metres). Otherwise set
  measure and limit to null.
- Every choice carries a Reason: one plain sentence saying why.
- Reasons describe what the ground and the trail look like: where a Path climbs,
  what it passes, what it avoids, how it turns. Never state a slope, gradient or
  angle. Code measures those on the Terrain afterwards, and a number you guessed
  will be wrong. A length or walk time you worked out from a Path's points is fine.
- Keep every measured Path under the Max Walkable Slope, and keep Pads off slopes.
  The ground is built exactly as below, and code measures it; plan with it:
  - A dome Zone of height h and radius r stands h * (1 + cos(pi * d / r)) / 2
    above what lies beneath, at distance d from its center. It is steepest halfway
    out, at atan(1.57 * h / r). To stay under a slope limit keep h / r at most:
    0.37 for 30°, 0.30 for 25°, 0.23 for 20°, 0.17 for 15°, 0.11 for 10°.
    Overlapping domes add their slopes, so keep them apart or lower.
  - A flat Zone has a sheer step at its rim, and so does any Zone combined with
    max or replace where it changes the height. The Refine Plan eases rims later;
    here they are vertical. A measured Path that crosses such a rim misses its
    slope limit. Reach raised ground over domes, keep Paths off flat rims, and
    use a step only where a step is the point, like a cliff.
  - If a Waypoint must sit on raised flat ground (a terrace, a plateau), a Path to
    it has to cross the step: say so in its Reason, e.g. "climbs the terrace step,
    which stays sheer until the Refine Plan eases it". Never call a step a ramp.
  - A Pad inside a flat Zone is level. A Pad of radius p on a dome's crown tilts
    by about atan(4.93 * h * p / r^2); it must stay under 3°.
  - A max_slope Reading measures the steepest point anywhere on the footprint,
    every Zone rim included, and a max_height Reading the highest point. Set a
    ceiling only if your own Zones stay under it; otherwise leave it unmeasured.
- If you cannot meet a Walk Target, still deliver the Blockout and say so in that
  Path's Reason. Never change the Brief's targets.
- Where and how big belongs to the Blockout. How the ground looks up close
  (roughness, seed, vegetation, slope profile, falloff) belongs to the Refine
  Plan, which comes later; do not set any of it here.
"""

REFINE_PLAN_SCHEMA = _object(
    surfaces={"type": "array", "items": _object(
        surface={"type": "string"},
        slope_profile={"type": "string", "enum": ["linear", "smooth", "steep"]},
        falloff_width={"type": "number"},
        roughness={"type": "number"},
        seed={"type": "integer"},
        vegetation_density={"type": "number"},
        reason=_REASON,
    )},
)

REFINE_PLAN_SYSTEM = """\
You write Refine Plans for Quarry, a terrain-authoring tool. A Refine Plan says
how each surface of an approved Blockout looks up close; code then builds the
Terrain from the two, and every Check runs again on that Terrain.

- Refine every surface exactly once: "ground", then each Zone by name.
- For each give slope_profile (linear, smooth or steep), falloff_width (metres a
  Zone's edge blends over), roughness (metres of height noise), seed (an integer;
  the only randomness in the Terrain) and vegetation_density (0 to 1).
- Every Refinement carries a Reason: one plain sentence saying why, including how
  it affects each Path it touches, e.g. "kept roughness low where the Path crosses
  so the trail stays smooth underfoot". Roughness and falloff can steepen a Path
  or slow its walk.
- Reasons describe what the surface looks and feels like. Never state a slope,
  angle or walk time: code measures those on the Terrain afterwards, and a number
  you guessed will be wrong.
- The Blockout is approved and fixed: where things are and how big (positions,
  radii, heights, Combine Modes, Stacking Order, Landmarks, Paths, Readings)
  belongs to it. Do not restate or change any of it.
"""


class ClaudeDrafter:
    """What every Claude adapter shares: the prompts and the schemas. Each
    adapter supplies only `_ask`, which reaches the model its own way."""

    def draft_blockout(self, brief, rejection_note=None):
        prompt = f"The Brief:\n{json.dumps(brief.to_dict(), indent=2)}"
        if rejection_note:
            prompt += f"\n\nThe human rejected the last Blockout, saying:\n{rejection_note}\nDraft a fresh one that answers this."
        return self._ask(BLOCKOUT_SYSTEM, prompt, BLOCKOUT_SCHEMA)

    def draft_refine_plan(self, brief, blockout, rejection_note=None):
        prompt = (
            f"The Brief:\n{json.dumps(brief.to_dict(), indent=2)}\n\n"
            f"The approved Blockout:\n{json.dumps(blockout.to_dict(), indent=2)}"
        )
        if rejection_note:
            prompt += f"\n\nThe human rejected the last Refine Plan, saying:\n{rejection_note}\nWrite a fresh one that answers this."
        return self._ask(REFINE_PLAN_SYSTEM, prompt, REFINE_PLAN_SCHEMA)

    def _ask(self, system, prompt, schema):
        raise NotImplementedError


class ClaudeAgent(ClaudeDrafter):
    """Drafts through the Anthropic API, billed per token (`--agent api`)."""

    def __init__(self, client=None, model=MODEL):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model

    def _ask(self, system, prompt, schema):
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # a declined request is re-run on a fallback model
            )
        except TypeError as error:
            if "authentication" not in str(error):
                raise
            raise AgentUnavailable(
                "no Anthropic credentials: set ANTHROPIC_API_KEY, or use --agent subscription"
            ) from None
        if response.stop_reason != "end_turn":
            raise InvalidDraft(f"the model stopped early ({response.stop_reason}); nothing was drafted")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text  # the validation layer reports it as malformed
