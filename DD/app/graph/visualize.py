from __future__ import annotations

from pyvis.network import Network


def build_graph_html(
    center_id: str,
    center_label: str,
    center_name: str,
    neighbors: list[dict[str, object]],
) -> str:
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#222222")
    net.add_node(
        center_id,
        label=center_name or center_id,
        title=f"{center_label} ({center_id})",
        color="#ffcc00",
    )

    for neighbor in neighbors:
        target_id = str(neighbor.get("target_id") or neighbor.get("target_name") or "unknown")
        target_label = str(neighbor.get("target_label") or "Unknown")
        target_name = str(neighbor.get("target_name") or target_id)
        rel = str(neighbor.get("rel") or "")

        net.add_node(
            target_id,
            label=target_name,
            title=f"{target_label} ({target_id})",
            color="#4c78a8",
        )
        net.add_edge(center_id, target_id, label=rel)

    net.repulsion(node_distance=140, spring_length=120)
    return net.generate_html()
