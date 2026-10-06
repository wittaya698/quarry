"""The Agent port's Claude adapter: drafts Blockouts and Refine Plans with the
latest Claude model. The API key comes from the environment (ANTHROPIC_API_KEY).

The model is offered no tools, so it has nothing to call: it can only answer
with a Draft as JSON, which the Site then validates before anything is kept.
"""
import json

from quarry.validation import InvalidDraft

MODEL = "claude-opus-5-5"


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
- Keep every measured Path under the Max Walkable Slope, and keep Pads off slopes.
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
  it affects each Path it touches, e.g. "kept roughness low along the Path so the
  walk stays at 3:05". Roughness and falloff can steepen a Path or slow its walk.
- The Blockout is approved and fixed: where things are and how big (positions,
  radii, heights, Combine Modes, Stacking Order, Landmarks, Paths, Readings)
  belongs to it. Do not restate or change any of it.
"""


class ClaudeAgent:
    def __init__(self, client=None, model=MODEL):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model

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
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # a declined request is re-run on a fallback model
            )
        except TypeError as error:
            if "authentication" not in str(error):
                raise
            raise AgentUnavailable(
                "no Anthropic credentials: set ANTHROPIC_API_KEY, or use --agent fake"
            ) from None
        if response.stop_reason != "end_turn":
            raise InvalidDraft(f"the model stopped early ({response.stop_reason}); nothing was drafted")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text  # the validation layer reports it as malformed
