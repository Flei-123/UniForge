"""Minimal, spec-compliant .unif writer.

Builds the text representation block by block (see docs/FORMAT.md). This layer
is deliberately format-only: callers (mesh/materials export) decide *what* to
write; the writer decides *how* it is laid out on disk.
"""

FORMAT_VERSION = "1.0"
_INDENT = "  "


class UnifWriter:
    def __init__(self, generator="UniForge Blender Addon 1.0"):
        self.generator = generator
        self._lines = []

    # --- low-level helpers ------------------------------------------------
    def _block(self, header, depth=0):
        self._lines.append(f"{_INDENT * depth}[{header}]")

    def _kv(self, key, value, depth=1):
        self._lines.append(f"{_INDENT * depth}{key}: {value}")

    @staticmethod
    def _flat(values):
        """Format a flat numeric list as ``[a,b,c, d,e,f, ...]`` (no spaces in groups)."""
        return "[" + ",".join(_fmt(v) for v in values) + "]"

    # --- public block API -------------------------------------------------
    def write_header(self, source_file):
        self._block("UNIF")
        self._kv("version", FORMAT_VERSION)
        self._kv("generator", self.generator)
        self._kv("source_file", source_file or "<unsaved>")
        self._blank()

    def write_mesh(self, name, vertices, faces, uvs, normals):
        self._block("MESH")
        self._kv("name", name)
        self._kv("vertices", self._flat(vertices))
        self._kv("faces", self._flat(faces))
        self._kv("uvs", self._flat(uvs))
        self._kv("normals", self._flat(normals))
        self._blank()

    def write_transform(self, position, rotation, scale):
        self._block("TRANSFORM")
        self._kv("position", ", ".join(_fmt(v) for v in position))
        self._kv("rotation", ", ".join(_fmt(v) for v in rotation))
        self._kv("scale", ", ".join(_fmt(v) for v in scale))
        self._blank()

    def begin_material(self, name, slot):
        self._block("MATERIAL")
        self._kv("name", name)
        self._kv("slot", slot)

    def write_node(self, unif_type, node_id, attrs=None, params=None):
        attr_str = "".join(f" {k}={v}" for k, v in (attrs or {}).items())
        self._block(f"NODE {unif_type} id={node_id}{attr_str}", depth=1)
        for key, value in (params or {}).items():
            self._kv(key, _fmt(value), depth=2)

    def begin_connections(self):
        self._block("CONNECTION", depth=1)

    def write_connection(self, src_id, src_socket, dst_id, dst_socket):
        self._lines.append(
            f"{_INDENT * 2}{src_id}.{src_socket} -> {dst_id}.{dst_socket}"
        )

    def end_material(self):
        self._blank()

    def _blank(self):
        self._lines.append("")

    # --- output -----------------------------------------------------------
    def render(self):
        return "\n".join(self._lines).rstrip() + "\n"

    def save(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.render())


def _fmt(value):
    """Compact float/int formatting: drop trailing zeros, keep ints clean."""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
