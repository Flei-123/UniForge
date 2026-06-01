"""Material / shader node-tree extraction (spec §4.3, steps 6-9).

For each material slot:
  - Walk the node tree, identify node types via node_map.
  - Supported nodes  -> serialize to [NODE] blocks.
  - Unsupported nodes -> bake to PNG (if options.bake_unsupported).
  - Serialize all connections to [CONNECTION] blocks.
"""

from . import node_map


def export_materials(obj, writer, options):
    """Serialize every material slot of ``obj`` into ``writer``.

    TODO(v1.0):
      - Iterate obj.material_slots; for each, open a [MATERIAL] block.
      - Walk material.node_tree.nodes, assign stable ids.
      - Map node.bl_idname via node_map.lookup(); emit [NODE] blocks.
      - For BAKE_ONLY / unsupported nodes, bake when enabled.
      - Walk node_tree.links; emit [CONNECTION] entries.
    """
    raise NotImplementedError(
        "materials.export_materials — implemented in the exporter milestone"
    )
