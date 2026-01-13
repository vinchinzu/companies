"""Network visualization module for fraud investigation.

Builds interactive network graphs showing relationships between
companies, persons, addresses, and legal cases.
"""

import json
from pathlib import Path
from typing import Any

import networkx as nx
from pyvis.network import Network


# Node type styling configuration
NODE_STYLES = {
    "company": {
        "color": "#e74c3c",  # Red
        "shape": "box",
        "size": 30,
        "font": {"size": 14, "color": "#ffffff"},
    },
    "person": {
        "color": "#3498db",  # Blue
        "shape": "dot",
        "size": 25,
        "font": {"size": 12, "color": "#333333"},
    },
    "address": {
        "color": "#2ecc71",  # Green
        "shape": "triangle",
        "size": 20,
        "font": {"size": 10, "color": "#333333"},
    },
    "case": {
        "color": "#9b59b6",  # Purple
        "shape": "diamond",
        "size": 25,
        "font": {"size": 11, "color": "#ffffff"},
    },
}

# Edge type styling
EDGE_STYLES = {
    "founded": {"color": "#3498db", "width": 3, "dashes": False},
    "executive": {"color": "#3498db", "width": 2, "dashes": False},
    "subsidiary": {"color": "#e74c3c", "width": 3, "dashes": False},
    "affiliate": {"color": "#e74c3c", "width": 2, "dashes": True},
    "financial_link": {"color": "#f39c12", "width": 2, "dashes": True},
    "control": {"color": "#8e44ad", "width": 2, "dashes": False},
    "registered_at": {"color": "#2ecc71", "width": 1, "dashes": True},
    "defendant_in": {"color": "#9b59b6", "width": 2, "dashes": False},
}


def load_network_data(json_path: str | Path) -> dict[str, Any]:
    """Load network data from JSON file.

    Args:
        json_path: Path to JSON file with network data

    Returns:
        Dict with nodes, edges, and metadata
    """
    with open(json_path, encoding='utf-8') as f:
        return json.load(f)


def get_risk_color(risk_score: float) -> str:
    """Get color based on risk score (0=high risk, 4=low risk).

    Args:
        risk_score: Risk score from 0 to 4

    Returns:
        Hex color string
    """
    if risk_score >= 3.0:
        return "#27ae60"  # Green - low risk
    elif risk_score >= 2.0:
        return "#f39c12"  # Orange - medium risk
    return "#c0392b"  # Red - high risk


def build_networkx_graph(data: dict[str, Any]) -> nx.Graph:
    """Build NetworkX graph from network data.

    Args:
        data: Dict with nodes and edges lists

    Returns:
        NetworkX Graph object
    """
    G = nx.Graph()

    # Add nodes with attributes
    for node in data.get("nodes", []):
        G.add_node(
            node["id"],
            label=node["label"],
            node_type=node["type"],
            **{k: v for k, v in node.items() if k not in ["id", "label", "type"]}
        )

    # Add edges with attributes
    for edge in data.get("edges", []):
        G.add_edge(
            edge["source"],
            edge["target"],
            relationship=edge.get("relationship", "related"),
            label=edge.get("label", ""),
        )

    return G


def create_pyvis_network(
    data: dict[str, Any],
    height: str = "700px",
    width: str = "100%",
    bgcolor: str = "#1a1a2e",
    font_color: str = "#ffffff",
    select_menu: bool = True,
    filter_menu: bool = True,
) -> Network:
    """Create PyVis network visualization.

    Args:
        data: Dict with nodes and edges
        height: Canvas height
        width: Canvas width
        bgcolor: Background color
        font_color: Default font color
        select_menu: Show node selection dropdown
        filter_menu: Show filter controls

    Returns:
        PyVis Network object
    """
    net = Network(
        height=height,
        width=width,
        bgcolor=bgcolor,
        font_color=font_color,
        select_menu=select_menu,
        filter_menu=filter_menu,
        directed=True,
    )

    # Configure physics for better layout
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=150,
        spring_strength=0.05,
        damping=0.09,
    )

    # Add nodes
    for node in data.get("nodes", []):
        node_type = node.get("type", "company")
        style = NODE_STYLES.get(node_type, NODE_STYLES["company"])

        # Build title (tooltip) from node attributes
        title_parts = [f"<b>{node['label']}</b>"]
        if "description" in node:
            title_parts.append(f"<br>{node['description']}")
        if "jurisdiction" in node:
            title_parts.append(f"<br>Jurisdiction: {node['jurisdiction']}")
        if "fraud_type" in node:
            title_parts.append(f"<br>Fraud Type: {node['fraud_type']}")
        if "status" in node:
            title_parts.append(f"<br>Status: {node['status']}")
        if "risk_score" in node:
            title_parts.append(f"<br>Risk Score: {node['risk_score']:.1f}")
        if "penalty" in node and node["penalty"]:
            title_parts.append(f"<br>Penalty: ${node['penalty']:,.0f}")

        # Use risk-based color for companies if available
        color = style["color"]
        if node_type == "company" and "risk_score" in node:
            color = get_risk_color(node["risk_score"])

        net.add_node(
            node["id"],
            label=node["label"],
            title="".join(title_parts),
            color=color,
            shape=style["shape"],
            size=style["size"],
            font=style["font"],
            group=node_type,
        )

    # Add edges
    for edge in data.get("edges", []):
        rel_type = edge.get("relationship", "related")
        style = EDGE_STYLES.get(rel_type, {"color": "#888888", "width": 1, "dashes": False})

        net.add_edge(
            edge["source"],
            edge["target"],
            title=edge.get("label", rel_type),
            label=edge.get("label", ""),
            color=style["color"],
            width=style["width"],
            dashes=style["dashes"],
            arrows="to",
        )

    return net


def create_cluster_subgraph(
    data: dict[str, Any],
    cluster_id: str,
) -> dict[str, Any]:
    """Extract subgraph for a specific cluster.

    Args:
        data: Full network data
        cluster_id: ID of cluster to extract

    Returns:
        Dict with filtered nodes and edges
    """
    clusters = {c["id"]: c for c in data.get("clusters", [])}
    if cluster_id not in clusters:
        return data

    cluster = clusters[cluster_id]
    entity_ids = set(cluster["entities"])

    # Filter nodes
    filtered_nodes = [n for n in data["nodes"] if n["id"] in entity_ids]

    # Filter edges (both endpoints must be in cluster)
    filtered_edges = [
        e for e in data["edges"]
        if e["source"] in entity_ids and e["target"] in entity_ids
    ]

    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "metadata": {
            **data.get("metadata", {}),
            "cluster": cluster["label"],
        },
    }


def filter_by_node_type(
    data: dict[str, Any],
    include_types: list[str],
) -> dict[str, Any]:
    """Filter network to include only specified node types.

    Args:
        data: Full network data
        include_types: List of node types to include

    Returns:
        Dict with filtered nodes and edges
    """
    filtered_nodes = [n for n in data["nodes"] if n["type"] in include_types]
    node_ids = {n["id"] for n in filtered_nodes}

    filtered_edges = [
        e for e in data["edges"]
        if e["source"] in node_ids and e["target"] in node_ids
    ]

    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "metadata": data.get("metadata", {}),
    }


def get_connected_entities(
    data: dict[str, Any],
    entity_id: str,
    max_depth: int = 2,
) -> dict[str, Any]:
    """Get subgraph of entities connected to a specific node.

    Args:
        data: Full network data
        entity_id: Starting entity ID
        max_depth: Maximum traversal depth

    Returns:
        Dict with connected nodes and edges
    """
    G = build_networkx_graph(data)

    if entity_id not in G:
        return {"nodes": [], "edges": []}

    # BFS to find connected nodes within depth
    connected = {entity_id}
    frontier = {entity_id}

    for _ in range(max_depth):
        next_frontier = set()
        for node in frontier:
            for neighbor in G.neighbors(node):
                if neighbor not in connected:
                    connected.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    # Filter data
    filtered_nodes = [n for n in data["nodes"] if n["id"] in connected]
    filtered_edges = [
        e for e in data["edges"]
        if e["source"] in connected and e["target"] in connected
    ]

    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "metadata": {
            **data.get("metadata", {}),
            "focus_entity": entity_id,
        },
    }


def compute_network_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """Compute network analysis metrics.

    Args:
        data: Network data with nodes and edges

    Returns:
        Dict with centrality and other metrics
    """
    G = build_networkx_graph(data)

    metrics = {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "density": nx.density(G),
        "is_connected": nx.is_connected(G),
    }

    if G.number_of_nodes() > 0:
        # Degree centrality - who has the most connections
        degree_cent = nx.degree_centrality(G)
        metrics["top_connected"] = sorted(
            degree_cent.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Betweenness centrality - who bridges groups
        if G.number_of_nodes() > 2:
            between_cent = nx.betweenness_centrality(G)
            metrics["key_bridges"] = sorted(
                between_cent.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

        # Connected components
        components = list(nx.connected_components(G))
        metrics["component_count"] = len(components)
        metrics["largest_component_size"] = max(len(c) for c in components) if components else 0

    return metrics


def generate_html(
    net: Network,
    output_path: str | Path | None = None,
) -> str:
    """Generate HTML for network visualization.

    Args:
        net: PyVis Network object
        output_path: Optional path to save HTML file

    Returns:
        HTML string
    """
    if output_path:
        net.save_graph(str(output_path))
        with open(output_path, encoding='utf-8') as f:
            return f.read()
    else:
        return net.generate_html()


# Default demo data path
DEMO_DATA_PATH = Path(__file__).parent.parent / "data" / "examples" / "fraud_network_demo.json"


def load_demo_network() -> dict[str, Any]:
    """Load the demo fraud network data.

    Returns:
        Dict with demo network data
    """
    return load_network_data(DEMO_DATA_PATH)
