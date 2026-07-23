"""Build the criminal association network with NetworkX.

Suspect-suspect edges come from two sources:
  1. suspect_associations rows (explicit ties: gang/family/associate)
  2. co-occurrence as 'Accused' in the same FIR (implicit ties)

Locations (the distinct areas a suspect has cases in) are always included as a
third node type — there are only ~15 of them, so they add signal without
clutter. Victims are optional (320 of them would swamp the layout) and are
only added when include_victims=True.
"""

from collections import defaultdict

import networkx as nx

from app.core.catalyst_datastore import get_datastore


def build_graph(include_victims: bool = False) -> nx.Graph:
    store = get_datastore()
    G = nx.Graph()

    for s in store.query("suspects", limit=1000):
        G.add_node(
            s["suspect_id"],
            node_type="suspect",
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

    firs = {f["fir_id"]: f for f in store.query("fir_records", limit=10000)}

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

    # Locations: one node per distinct area, linked to suspects who had a case there
    seen_location_edge = set()
    for fir_id, accused in fir_accused.items():
        fir = firs.get(fir_id)
        if not fir:
            continue
        loc_id = f"LOC::{fir['area']}"
        if loc_id not in G:
            G.add_node(loc_id, node_type="location", name=fir["area"])
        for sid in accused:
            key = (sid, loc_id)
            if key in seen_location_edge:
                continue
            seen_location_edge.add(key)
            G.add_edge(sid, loc_id, relation="Case in area", weight=0.3)

    if include_victims:
        victim_names = {v["victim_id"]: v["name"] for v in store.query("victims", limit=2000)}
        fir_victims = defaultdict(list)
        for link in store.query("fir_victim_links", limit=5000):
            fir_victims[link["fir_id"]].append((link["victim_id"], link["impact"]))

        for fir_id, victims in fir_victims.items():
            for vid, impact in victims:
                if vid not in G:
                    G.add_node(vid, node_type="victim", name=victim_names.get(vid, vid))
                for sid in fir_accused.get(fir_id, []):
                    G.add_edge(sid, vid, relation=f"Victim-Accused ({impact})", weight=0.3)

    return G


def graph_summary(include_victims: bool = False) -> dict:
    G = build_graph(include_victims=include_victims)
    # keep only connected nodes for the visual
    G.remove_nodes_from(list(nx.isolates(G)))

    centrality = nx.degree_centrality(G)
    suspect_centrality = {n: c for n, c in centrality.items() if G.nodes[n].get("node_type") == "suspect"}
    top_central = sorted(suspect_centrality.items(), key=lambda x: -x[1])[:10]

    communities = list(nx.community.greedy_modularity_communities(G)) if G.number_of_nodes() else []

    pos = nx.spring_layout(G, seed=42, k=0.3)
    node_community = {}
    for idx, comm in enumerate(communities):
        for n in comm:
            node_community[n] = idx

    nodes = [
        {
            "id": n,
            "type": G.nodes[n].get("node_type", "suspect"),
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

    n_suspects = sum(1 for n in nodes if n["type"] == "suspect")
    n_locations = sum(1 for n in nodes if n["type"] == "location")
    n_victims = sum(1 for n in nodes if n["type"] == "victim")

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "num_suspects": n_suspects,
            "num_locations": n_locations,
            "num_victims": n_victims,
            "num_links": G.number_of_edges(),
            "num_communities": len(communities),
            "top_central": [
                {"suspect_id": sid, "name": G.nodes[sid].get("name", sid), "centrality": round(c, 3)}
                for sid, c in top_central
            ],
        },
    }
