"""Build the suspect-association network with NetworkX.

Edges come from two sources:
  1. suspect_associations rows (explicit ties: gang/family/associate)
  2. co-occurrence as 'Accused' in the same FIR (implicit ties)
"""

from collections import defaultdict

import networkx as nx

from app.core.catalyst_datastore import get_datastore


def build_graph() -> nx.Graph:
    store = get_datastore()
    G = nx.Graph()

    for s in store.query("suspects", limit=1000):
        G.add_node(
            s["suspect_id"],
            name=s["name"],
            prior_cases=int(s["prior_cases"]) if s["prior_cases"] not in (None, "") else 0,
            address=s["known_address"],
        )

    for a in store.query("suspect_associations", limit=5000):
        G.add_edge(
            a["suspect_id_a"], a["suspect_id_b"],
            relation=a["relation_type"],
            weight=float(a["confidence"]) if a["confidence"] not in (None, "") else 0.5,
        )

    fir_accused = defaultdict(list)
    for link in store.query("fir_suspect_links", limit=10000):
        if link["role"] == "Accused":
            fir_accused[link["fir_id"]].append(link["suspect_id"])

    for fir_id, accused in fir_accused.items():
        for i in range(len(accused)):
            for j in range(i + 1, len(accused)):
                a, b = accused[i], accused[j]
                if G.has_edge(a, b):
                    G[a][b]["co_firs"] = G[a][b].get("co_firs", 0) + 1
                else:
                    G.add_edge(a, b, relation="Co-accused (same FIR)", weight=0.5, co_firs=1)

    return G


def graph_summary() -> dict:
    G = build_graph()
    # keep only connected suspects for the visual
    G.remove_nodes_from(list(nx.isolates(G)))

    centrality = nx.degree_centrality(G)
    top_central = sorted(centrality.items(), key=lambda x: -x[1])[:10]

    communities = list(nx.community.greedy_modularity_communities(G)) if G.number_of_nodes() else []

    pos = nx.spring_layout(G, seed=42, k=0.3)
    node_community = {}
    for idx, comm in enumerate(communities):
        for n in comm:
            node_community[n] = idx

    nodes = [
        {
            "id": n,
            "name": G.nodes[n].get("name", n),
            "prior_cases": G.nodes[n].get("prior_cases", 0),
            "degree": G.degree(n),
            "community": node_community.get(n, -1),
            "x": float(pos[n][0]),
            "y": float(pos[n][1]),
        }
        for n in G.nodes
    ]
    edges = [
        {
            "source": u,
            "target": v,
            "relation": d.get("relation", ""),
            "weight": d.get("weight", 0.5),
        }
        for u, v, d in G.edges(data=True)
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "num_suspects": G.number_of_nodes(),
            "num_links": G.number_of_edges(),
            "num_communities": len(communities),
            "top_central": [
                {"suspect_id": sid, "name": G.nodes[sid].get("name", sid), "centrality": round(c, 3)}
                for sid, c in top_central
            ],
        },
    }
