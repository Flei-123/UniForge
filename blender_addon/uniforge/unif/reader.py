"""Minimal .unif reader — parses the format back into a document model.

The bpy-free counterpart to writer.py (mirrors the Unity-side UnifParser), so
the Blender importer can rebuild objects/materials from a .unif file.
"""

import base64


class UnifDoc:
    def __init__(self):
        self.version = None
        self.generator = None
        self.source_file = None
        self.objects = []           # list[UnifObj]
        self.embedded = {}          # name -> (format, bytes)


class UnifObj:
    def __init__(self, name=None, parent=None):
        self.name = name
        self.parent = parent
        self.mesh = None            # dict: name, vertices, faces, uvs, normals, colors, submeshes
        self.transform = None       # dict: position, rotation, scale
        self.materials = []         # list[UnifMat]


class UnifMat:
    def __init__(self, name=None, slot=0):
        self.name = name
        self.slot = slot
        self.nodes = []             # list[UnifNode]
        self.connections = []       # list[(src_id, src_socket, dst_id, dst_socket)]


class UnifNode:
    def __init__(self, type=None, id=0):
        self.type = type
        self.id = id
        self.attrs = {}
        self.params = {}


def parse_file(path):
    with open(path, encoding="utf-8") as handle:
        return parse(handle.read())


def parse(text):
    doc = UnifDoc()
    section = None
    current_obj = None
    current_mat = None
    current_node = None
    in_connections = False
    pending_embedded = None

    def ensure_obj():
        nonlocal current_obj
        if current_obj is None:
            current_obj = UnifObj()
            doc.objects.append(current_obj)
        return current_obj

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue

        if line[0] == "[" and line.endswith("]"):
            tokens = _tokenize(line[1:-1].strip())
            if not tokens:
                continue
            kind = tokens[0]
            pending_embedded = None
            if kind == "UNIF":
                section = "unif"
                current_mat = current_node = None
                in_connections = False
            elif kind == "OBJECT":
                attrs = _attrs(tokens)
                current_obj = UnifObj(attrs.get("name"), attrs.get("parent"))
                doc.objects.append(current_obj)
                section = None
                current_mat = current_node = None
                in_connections = False
            elif kind == "MESH":
                section = "mesh"
                ensure_obj().mesh = {}
                current_mat = current_node = None
                in_connections = False
            elif kind == "TRANSFORM":
                section = "transform"
                ensure_obj().transform = {}
                current_mat = current_node = None
                in_connections = False
            elif kind == "MATERIAL":
                section = "material"
                current_mat = UnifMat()
                ensure_obj().materials.append(current_mat)
                current_node = None
                in_connections = False
            elif kind == "NODE":
                current_node = _parse_node(tokens)
                if current_mat is not None:
                    current_mat.nodes.append(current_node)
                in_connections = False
            elif kind == "CONNECTION":
                in_connections = True
                current_node = None
            elif kind == "TEXTURE_EMBEDDED":
                attrs = _attrs(tokens)
                pending_embedded = (attrs.get("name"), attrs.get("format", "png"))
                current_node = None
                in_connections = False
            else:
                current_node = None
                in_connections = False
            continue

        if in_connections and "->" in line:
            conn = _parse_connection(line)
            if conn and current_mat is not None:
                current_mat.connections.append(conn)
            continue

        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()

        if pending_embedded is not None and key == "data":
            name, fmt = pending_embedded
            try:
                doc.embedded[name] = (fmt, base64.b64decode(value))
            except (ValueError, TypeError):
                pass
            pending_embedded = None
        elif current_node is not None:
            current_node.params[key] = value
        elif section == "material" and current_mat is not None:
            if key == "name":
                current_mat.name = value
            elif key == "slot":
                current_mat.slot = _to_int(value, 0)
        elif section == "unif":
            if key in ("version", "generator", "source_file"):
                setattr(doc, key, value)
        elif section == "mesh" and current_obj and current_obj.mesh is not None:
            if key == "name":
                current_obj.mesh["name"] = value
            elif key in ("vertices", "uvs", "normals", "colors"):
                current_obj.mesh[key] = _float_list(value)
            elif key in ("faces", "submeshes"):
                current_obj.mesh[key] = _int_list(value)
        elif section == "transform" and current_obj and current_obj.transform is not None:
            if key in ("position", "rotation", "scale"):
                current_obj.transform[key] = _float_list(value)

    return doc


# --- helpers --------------------------------------------------------------
def _tokenize(header):
    """Split a header on spaces, honoring double quotes with backslash escapes."""
    tokens = []
    buf = []
    in_quotes = False
    has = False
    i = 0
    while i < len(header):
        c = header[i]
        if in_quotes:
            if c == "\\" and i + 1 < len(header):
                buf.append(header[i + 1])
                has = True
                i += 1
            elif c == '"':
                in_quotes = False
            else:
                buf.append(c)
                has = True
        elif c == '"':
            in_quotes = True
            has = True
        elif c in " \t":
            if has:
                tokens.append("".join(buf))
                buf = []
                has = False
        else:
            buf.append(c)
            has = True
        i += 1
    if has:
        tokens.append("".join(buf))
    return tokens


def _attrs(tokens):
    out = {}
    for tok in tokens[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out


def _parse_node(tokens):
    node = UnifNode(type=tokens[1] if len(tokens) >= 2 else None)
    for tok in tokens[2:]:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        if k == "id":
            node.id = _to_int(v, 0)
        else:
            node.attrs[k] = v
    return node


def _parse_connection(line):
    left, right = line.split("->", 1)
    src = _split_endpoint(left)
    dst = _split_endpoint(right)
    if src is None or dst is None:
        return None
    return (src[0], src[1], dst[0], dst[1])


def _split_endpoint(text):
    text = text.strip()
    if "." not in text:
        return None
    id_part, socket = text.split(".", 1)
    return (_to_int(id_part.strip(), -1), socket.strip())


def _float_list(token):
    token = token.strip().lstrip("[").rstrip("]")
    if not token:
        return []
    return [float(p) for p in token.split(",") if p.strip() != ""]


def _int_list(token):
    token = token.strip().lstrip("[").rstrip("]")
    if not token:
        return []
    return [int(float(p)) for p in token.split(",") if p.strip() != ""]


def _to_int(value, default):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
