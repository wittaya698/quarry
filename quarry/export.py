"""Export: Terrain → a `.glb` that Godot 4 imports with collision (ADR-0002).

The terrain mesh appears twice: once as `terrain`, for display, and once as
`terrain-colonly`, which Godot's importer turns into a static collision body.

`read_glb` is the round-trip's re-import. It parses the file's bytes through
glTF's own accessor tables rather than reusing anything from the writer, so
a writer bug cannot hide behind a matching reader bug.
"""
import json
import struct
from dataclasses import dataclass

COLLISION = "terrain-colonly"
_JSON, _BIN = 0x4E4F534A, 0x004E4942
_FLOAT, _UINT = 5126, 5125
_COMPONENTS = {_FLOAT: "f", _UINT: "I", 5123: "H", 5121: "B"}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


class ExportError(Exception):
    """An Export whose re-import does not match the Terrain it came from."""


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


def export_glb(terrain, path):
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

    vertex_bytes = struct.pack(f"<{len(positions) * 3}f", *(v for p in positions for v in p))
    index_bytes = struct.pack(f"<{len(indices)}I", *indices)
    blob = vertex_bytes + index_bytes
    primitive = {"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}
    document = {
        "asset": {"version": "2.0", "generator": "quarry"},
        "scene": 0,
        "scenes": [{"nodes": [0, 1]}],
        "nodes": [{"name": "terrain", "mesh": 0}, {"name": COLLISION, "mesh": 1}],
        "meshes": [
            {"name": "terrain", "primitives": [primitive]},
            {"name": COLLISION, "primitives": [primitive]},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": _FLOAT,
                "count": len(positions),
                "type": "VEC3",
                # glTF wants the bounds as the float32 values actually stored.
                "min": [_float32(min(p[i] for p in positions)) for i in range(3)],
                "max": [_float32(max(p[i] for p in positions)) for i in range(3)],
            },
            {"bufferView": 1, "componentType": _UINT, "count": len(indices), "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(vertex_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(vertex_bytes), "byteLength": len(index_bytes), "target": 34963},
        ],
        "buffers": [{"byteLength": len(blob)}],
    }
    text = json.dumps(document, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    blob += b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(text) + 8 + len(blob)
    with open(path, "wb") as out:
        out.write(struct.pack("<4sII", b"glTF", 2, total))
        out.write(struct.pack("<II", len(text), _JSON) + text)
        out.write(struct.pack("<II", len(blob), _BIN) + blob)


def _float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def read_glb(path):
    """Re-import a `.glb`: each named node's mesh, as positions and triangles."""
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

    nodes = {}
    for node in document.get("nodes", []):
        if "mesh" not in node:
            continue
        [primitive] = document["meshes"][node["mesh"]]["primitives"]
        positions = tuple(accessor(primitive["attributes"]["POSITION"]))
        flat = [i for (i,) in accessor(primitive["indices"])]
        triangles = tuple(tuple(flat[i : i + 3]) for i in range(0, len(flat), 3))
        nodes[node["name"]] = ImportedMesh(positions, triangles)
    return nodes


def verify_export(terrain, path):
    """Re-import and re-measure: the collision is present and spans the Terrain."""
    nodes = read_glb(path)
    if COLLISION not in nodes:
        raise ExportError(f"{path} has no {COLLISION} node, so Godot would build no collision")
    xs, ys, zs = zip(*nodes[COLLISION].positions)
    heights = [h for row in terrain.heights for h in row]
    measured = {
        "x extent": (min(xs), max(xs)),
        "y extent": (min(zs), max(zs)),
        "height": (min(ys), max(ys)),
    }
    expected = {
        "x extent": (0, terrain.extent[0]),
        "y extent": (0, terrain.extent[1]),
        "height": (min(heights), max(heights)),
    }
    for name, (low, high) in expected.items():
        got_low, got_high = measured[name]
        if abs(got_low - low) > 1e-3 or abs(got_high - high) > 1e-3:
            raise ExportError(
                f"collision {name} is {got_low:.3f}..{got_high:.3f}, the Terrain's is {low:.3f}..{high:.3f}"
            )
