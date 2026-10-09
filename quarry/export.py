"""Export: Terrain → a `.glb` that Godot 4 imports with collision (ADR-0002).

The terrain mesh appears twice: once as `terrain`, for display, and once as
`terrain_collision-colonly`, which Godot's importer turns into a static
collision body named `terrain_collision`.
The display mesh carries vegetation as density data, one value per height
sample, in its node's extras. `write_tscn` adds an optional Godot scene that
instances the `.glb` and makes each Path a Path3D. Under `landmarks` is an empty node per Landmark, standing on its Pad; under
`paths`, a line-strip curve per Path, laid along the ground.

`read_glb` is the round-trip's re-import. It parses the file's bytes through
glTF's own accessor tables rather than reusing anything from the writer, so
a writer bug cannot hide behind a matching reader bug.
"""
import json
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path

COLLISION = "terrain_collision-colonly"
# Godot's import hints: a node name ending in one, after `-`, `_` or `$`, is
# acted on (made collision, a vehicle, dropped...) and loses the hint.
GODOT_HINTS = (
    "noimp", "col", "convcol", "colonly", "convcolonly", "occ", "occonly",
    "navmesh", "rigid", "vehicle", "wheel", "vcol", "loop", "cycle",
)
LANDMARKS = "landmarks"
PATHS = "paths"
_JSON, _BIN = 0x4E4F534A, 0x004E4942
_FLOAT, _UINT = 5126, 5125
_TRIANGLES, _LINE_STRIP = 4, 3
_COMPONENTS = {_FLOAT: "f", _UINT: "I", 5123: "H", 5121: "B"}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
_CLOSE = 1e-3  # metres; float32 storage is well inside it


class ExportError(Exception):
    """An Export whose re-import does not match the Terrain it came from."""


@dataclass(frozen=True)
class Imported:
    """What a re-import finds. Points are glTF's Y-up order: (x, height, y)."""
    meshes: dict  # node name → ImportedMesh
    anchors: dict  # Landmark name → its point
    curves: dict  # "start→end" → the Path's points, in order
    metadata: dict  # node name → its metadata as Godot imports it: the glTF extras, under "extras"
    children: dict  # node name → its children's names, in order; "" is the scene


@dataclass(frozen=True)
class ImportedMesh:
    positions: tuple[tuple[float, float, float], ...]
    triangles: tuple[tuple[int, int, int], ...]

    def facing_up(self):
        """The Y part of each triangle's normal; positive means it faces the sky."""
        result = []
        for a, b, c in self.triangles:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (self.positions[i] for i in (a, b, c))
            ux, uz, vx, vz = bx - ax, bz - az, cx - ax, cz - az
            result.append(uz * vx - ux * vz)
        return result


class _Document:
    """A glTF document and its one binary buffer, built up a mesh at a time."""

    def __init__(self):
        self.json = {
            "asset": {"version": "2.0", "generator": "quarry"},
            "scene": 0,
            "scenes": [{"nodes": []}],
            "nodes": [],
            "meshes": [],
            "accessors": [],
            "bufferViews": [],
        }
        self.blob = b""

    def node(self, node, parent=None):
        index = len(self.json["nodes"])
        self.json["nodes"].append(node)
        if parent is None:
            self.json["scenes"][0]["nodes"].append(index)
        else:
            self.json["nodes"][parent].setdefault("children", []).append(index)
        return index

    def mesh(self, name, positions, indices=None, mode=_TRIANGLES):
        primitive = {"attributes": {"POSITION": self._positions(positions)}, "mode": mode}
        if indices is not None:
            primitive["indices"] = self._view(struct.pack(f"<{len(indices)}I", *indices), 34963, {
                "componentType": _UINT, "count": len(indices), "type": "SCALAR",
            })
        self.json["meshes"].append({"name": name, "primitives": [primitive]})
        return len(self.json["meshes"]) - 1

    def _positions(self, positions):
        data = struct.pack(f"<{len(positions) * 3}f", *(v for p in positions for v in p))
        return self._view(data, 34962, {
            "componentType": _FLOAT,
            "count": len(positions),
            "type": "VEC3",
            # glTF wants the bounds as the float32 values actually stored.
            "min": [_float32(min(p[i] for p in positions)) for i in range(3)],
            "max": [_float32(max(p[i] for p in positions)) for i in range(3)],
        })

    def _view(self, data, target, accessor):
        self.json["bufferViews"].append(
            {"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data), "target": target}
        )
        self.blob += data + b"\0" * (-len(data) % 4)
        self.json["accessors"].append({"bufferView": len(self.json["bufferViews"]) - 1, **accessor})
        return len(self.json["accessors"]) - 1

    def write(self, path):
        self.json["buffers"] = [{"byteLength": len(self.blob)}]
        text = json.dumps(self.json, separators=(",", ":")).encode()
        text += b" " * (-len(text) % 4)
        total = 12 + 8 + len(text) + 8 + len(self.blob)
        with open(path, "wb") as out:
            out.write(struct.pack("<4sII", b"glTF", 2, total))
            out.write(struct.pack("<II", len(text), _JSON) + text)
            out.write(struct.pack("<II", len(self.blob), _BIN) + self.blob)


def export_glb(terrain, blockout, path):
    rows, columns = len(terrain.heights), len(terrain.heights[0])
    positions = [
        (c * terrain.spacing, terrain.heights[r][c], r * terrain.spacing)
        for r in range(rows)
        for c in range(columns)
    ]
    indices = []
    for r in range(rows - 1):
        for c in range(columns - 1):
            v00, v10 = r * columns + c, r * columns + c + 1
            v01, v11 = v00 + columns, v10 + columns
            indices += [v00, v01, v10, v10, v01, v11]

    document = _Document()
    document.node({"name": "terrain", "mesh": document.mesh("terrain", positions, indices), "extras": {
        "vegetation_density": {
            "spacing": terrain.spacing,
            "rows": rows,
            "columns": columns,
            "density": [d for row in terrain.vegetation for d in row],
        },
    }})
    document.node({"name": COLLISION, "mesh": document.mesh(COLLISION, positions, indices)})
    landmarks = document.node({"name": LANDMARKS})
    for landmark in blockout.landmarks:
        document.node(_anchor(terrain, landmark), parent=landmarks)
    paths = document.node({"name": PATHS})
    for route in blockout.paths:
        name = f"{route.start}→{route.end}"
        curve = document.mesh(name, _drape(terrain, route.points), mode=_LINE_STRIP)
        document.node({"name": name, "mesh": curve}, parent=paths)
    document.write(path)


def _anchor(terrain, landmark):
    """An empty node where the Landmark stands, on its Pad: the asset is the game's to place."""
    x, y = landmark.position
    return {"name": landmark.name, "translation": [x, terrain.height(x, y), y]}


def _drape(terrain, points):
    """The Path's points, with more in between every half sample, each on the ground."""
    step = terrain.spacing / 2
    flat = [points[0]]
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        pieces = max(1, math.ceil(math.dist((ax, ay), (bx, by)) / step))
        flat += [(ax + (bx - ax) * i / pieces, ay + (by - ay) * i / pieces) for i in range(1, pieces + 1)]
    return [(x, terrain.height(x, y), y) for x, y in flat]


def godot_name(name):
    """What Godot 4's importer makes of a node name: (the name it keeps, the
    import hint it acts on, or None)."""
    for hint in GODOT_HINTS:
        for mark in "-_$":
            if name.lower().endswith(mark + hint):
                return name[: -len(mark + hint)], hint
    return name, None


def _float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def read_glb(path):
    """Re-import a `.glb`: each named node's mesh, the anchors under `landmarks`
    and the curves under `paths`."""
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ExportError(f"{path} is not a whole glTF 2.0 binary")
    document, blob, offset = None, b"", 12
    while offset < length:
        size, kind = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8 : offset + 8 + size]
        if kind == _JSON:
            document = json.loads(chunk)
        elif kind == _BIN:
            blob = chunk
        offset += 8 + size
    if document is None:
        raise ExportError(f"{path} has no JSON chunk")

    def accessor(index):
        a = document["accessors"][index]
        view = document["bufferViews"][a["bufferView"]]
        width = _WIDTH[a["type"]]
        start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
        values = struct.unpack_from(f"<{a['count'] * width}{_COMPONENTS[a['componentType']]}", blob, start)
        return [tuple(values[i : i + width]) for i in range(0, len(values), width)]

    nodes = document.get("nodes", [])

    def children(name):
        for parent in nodes:
            if parent.get("name") == name:
                return [nodes[i] for i in parent.get("children", [])]
        return []

    meshes, curves = {}, {}
    for node in nodes:
        if "mesh" not in node:
            continue
        [primitive] = document["meshes"][node["mesh"]]["primitives"]
        positions = tuple(accessor(primitive["attributes"]["POSITION"]))
        if primitive.get("mode", _TRIANGLES) == _LINE_STRIP:
            curves[node["name"]] = positions
            continue
        flat = [i for (i,) in accessor(primitive["indices"])]
        triangles = tuple(tuple(flat[i : i + 3]) for i in range(0, len(flat), 3))
        meshes[node["name"]] = ImportedMesh(positions, triangles)
    anchors = {
        node["name"]: tuple(node.get("translation", (0.0, 0.0, 0.0)))
        for node in children(LANDMARKS)
        if "mesh" not in node
    }
    curves = {node["name"]: curves[node["name"]] for node in children(PATHS) if node["name"] in curves}
    metadata = {node["name"]: {"extras": node["extras"]} for node in nodes if "name" in node and "extras" in node}
    tree = {"": tuple(nodes[i].get("name", "") for i in document["scenes"][document.get("scene", 0)]["nodes"])}
    for node in nodes:
        if node.get("children"):
            tree[node.get("name", "")] = tuple(nodes[i].get("name", "") for i in node["children"])
    return Imported(meshes, anchors, curves, metadata, tree)


def verify_export(terrain, blockout, path):
    """Re-import and re-measure: the collision is the Terrain, sample for sample,
    every Landmark's anchor stands on its Pad, and every Path's curve lies on the
    ground from its start to its end."""
    imported = read_glb(path)
    _verify_names(imported)
    _verify_collision(terrain, imported, path)
    _verify_heights(terrain, imported)
    _verify_anchors(terrain, blockout, imported, path)
    _verify_curves(terrain, blockout, imported, path)


def _verify_names(imported):
    """Godot acts on the hint ending a node's name, and finds the node by the
    name it keeps: only the collision may carry a hint, and no two siblings may
    keep the same name."""
    for siblings in imported.children.values():
        kept = {}
        for name in siblings:
            stem, hint = godot_name(name)
            if hint and name != COLLISION:
                raise ExportError(f"Godot would read {name} as {stem} with the {hint} import hint, and act on it")
            other = kept.setdefault(godot_name(name)[0], name)
            if other != name:
                raise ExportError(
                    f"Godot would name both {name} and {other} {godot_name(name)[0]}, "
                    "and rename one at random on every import"
                )


def _verify_collision(terrain, imported, path):
    """Godot builds collision from it, and it spans the footprint."""
    if COLLISION not in imported.meshes:
        raise ExportError(f"{path} has no {COLLISION} node, so Godot would build no collision")
    xs, _, zs = zip(*imported.meshes[COLLISION].positions)
    for name, values, size in (("x", xs, terrain.extent[0]), ("y", zs, terrain.extent[1])):
        if abs(min(values)) > _CLOSE or abs(max(values) - size) > _CLOSE:
            raise ExportError(
                f"collision {name} extent is {min(values):.3f}..{max(values):.3f}, the Terrain's is 0..{size:.3f}"
            )


def _verify_heights(terrain, imported):
    """Every collision point is the Terrain's height there: nothing changed it
    on the way out, so it is the Terrain the approved Revisions build."""
    for x, height, y in imported.meshes[COLLISION].positions:
        if abs(height - terrain.height(x, y)) > _CLOSE:
            raise ExportError(
                f"collision height at ({x:.1f}, {y:.1f}) is {height:.3f}, "
                f"the Terrain's is {terrain.height(x, y):.3f}: changed without a Revision"
            )


def _verify_anchors(terrain, blockout, imported, path):
    for landmark in blockout.landmarks:
        if landmark.name not in imported.anchors:
            raise ExportError(f"{path} has no anchor for {landmark.name}")
        x, height, y = imported.anchors[landmark.name]
        lx, ly = landmark.position
        if math.dist((x, y), (lx, ly)) > _CLOSE or abs(height - terrain.height(lx, ly)) > _CLOSE:
            raise ExportError(
                f"anchor {landmark.name} is at ({x:.2f}, {y:.2f}, height {height:.2f}), off its Pad at "
                f"({lx:.2f}, {ly:.2f}, height {terrain.height(lx, ly):.2f})"
            )


def _verify_curves(terrain, blockout, imported, path):
    for route in blockout.paths:
        name = f"{route.start}→{route.end}"
        if name not in imported.curves:
            raise ExportError(f"{path} has no curve for {name}")
        curve = [((x, y), height) for x, height, y in imported.curves[name]]
        ends = (curve[0][0], curve[-1][0])
        off = [
            point for point, height in curve
            if _off_line(point, route.points) > _CLOSE or abs(height - terrain.height(*point)) > _CLOSE
        ]
        if math.dist(ends[0], route.points[0]) > _CLOSE or math.dist(ends[1], route.points[-1]) > _CLOSE or off:
            raise ExportError(f"curve {name} leaves its Path or the ground")
        if any(math.dist(a, b) > terrain.spacing + _CLOSE for (a, _), (b, _) in zip(curve, curve[1:])):
            raise ExportError(f"curve {name} skips over the ground between its points")


def _off_line(point, points):
    """How far a point lies from a polyline, across the ground."""
    best = math.inf
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = 0.0 if length == 0 else max(0.0, min(1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / length))
        best = min(best, math.dist(point, (ax + t * dx, ay + t * dy)))
    return best


def write_tscn(glb):
    """A thin Godot 4 scene beside the `.glb` that instances it, for dropping
    the Site straight into a game. glTF has no curve type, so the scene makes
    each Path a Path3D, from the curve the `.glb` holds, and hides the `.glb`'s
    own lines. Returns the scene's path."""
    glb = Path(glb)
    curves = read_glb(glb).curves
    scene = glb.with_suffix(".tscn")
    parts = [
        f"[gd_scene load_steps={2 + len(curves)} format=3]",
        f'[ext_resource type="PackedScene" path="{glb.name}" id="1_glb"]',
    ]
    for i, points in enumerate(curves.values(), 1):
        # each point is its in handle, its out handle and its position
        vectors = ", ".join(f"0, 0, 0, 0, 0, 0, {x!r}, {height!r}, {y!r}" for x, height, y in points)
        tilts = ", ".join("0" for _ in points)
        parts.append(
            f'[sub_resource type="Curve3D" id="Curve3D_{i}"]\n'
            f'_data = {{\n"points": PackedVector3Array({vectors}),\n"tilts": PackedFloat32Array({tilts})\n}}\n'
            f"point_count = {len(points)}"
        )
    parts += [
        f'[node name="{glb.stem}" type="Node3D"]',
        '[node name="terrain" parent="." instance=ExtResource("1_glb")]',
        f'[node name="{PATHS}" parent="terrain"]\nvisible = false',
        f'[node name="{PATHS}" type="Node3D" parent="."]',
        *(
            f'[node name="{name}" type="Path3D" parent="{PATHS}"]\ncurve = SubResource("Curve3D_{i}")'
            for i, name in enumerate(curves, 1)
        ),
        '[editable path="terrain"]',
    ]
    scene.write_text("\n\n".join(parts) + "\n")
    return scene


@dataclass(frozen=True)
class ImportedScene:
    """What a re-read of the `.tscn` finds. Points are Godot's order: (x, height, y)."""
    path3ds: dict  # Path3D name → its curve's points, in order
    hidden: frozenset  # node paths, from the scene's root, set not visible


def read_tscn(scene):
    """Read the scene back, as Godot would, without the writer's help."""
    text = Path(scene).read_text()
    curves, path3ds, hidden = {}, {}, set()
    for section in re.split(r"\n(?=\[)", text):
        header, _, body = section.partition("]")
        fields = dict(re.findall(r'(\w+)="([^"]*)"', header))
        if header.startswith("[sub_resource") and fields.get("type") == "Curve3D":
            numbers = [float(n) for n in re.search(r"PackedVector3Array\(([^)]*)\)", body)[1].split(",")]
            curves[fields["id"]] = tuple(tuple(numbers[i + 6 : i + 9]) for i in range(0, len(numbers), 9))
        elif header.startswith("[node"):
            if fields.get("type") == "Path3D":
                path3ds[fields["name"]] = curves[re.search(r'SubResource\("([^"]*)"\)', body)[1]]
            if re.search(r"^visible = false$", body, re.M):
                parent = fields["parent"]
                hidden.add(fields["name"] if parent == "." else f"{parent}/{fields['name']}")
    return ImportedScene(path3ds, frozenset(hidden))
