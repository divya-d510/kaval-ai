"""Criminology-based offender profiling and risk scoring.

The risk score is a transparent, weighted formula (not a black box), combining:
  - prior_cases       : volume of criminal history
  - network centrality: how connected the suspect is in the association graph
  - recency           : how recent their most recent case involvement is
  - versatility       : how many distinct crime types they're linked to
Each component and its contribution is returned alongside the score, so the
score itself is explainable rather than an opaque number.
"""

import datetime
from collections import defaultdict

import networkx as nx

from app.core.catalyst_datastore import get_datastore
from app.core.llm_client import ask_safe
from app.services.graph_builder import build_graph

W_PRIOR = 0.35
W_CENTRALITY = 0.25
W_RECENCY = 0.20
W_VERSATILITY = 0.20

BEHAVIORAL_SYSTEM = """You are a criminology analyst for Karnataka State Police.
Given a suspect's case history (JSON: crime types, dates, modus operandi on file),
write a short behavioral profile (3-4 sentences) describing their offending pattern.
Be factual and only reference the given data — do not speculate beyond it. Write in English."""


def _num(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _recency_score(firs: list[dict]) -> float:
    if not firs:
        return 0.0
    dates = [datetime.date.fromisoformat(f["date_filed"]) for f in firs]
    days_ago = (datetime.date.today() - max(dates)).days
    return max(0.0, 1.0 - days_ago / 540)


def compute_risk_score(suspect: dict, firs: list[dict], centrality: float) -> tuple[float, dict]:
    prior_cases = _num(suspect.get("prior_cases"))
    prior_component = min(prior_cases / 8, 1.0)
    centrality_component = min(centrality * 5, 1.0)
    recency_component = _recency_score(firs)
    crime_types = {f["crime_type"] for f in firs}
    versatility_component = min(len(crime_types) / 4, 1.0)

    score = (
        W_PRIOR * prior_component
        + W_CENTRALITY * centrality_component
        + W_RECENCY * recency_component
        + W_VERSATILITY * versatility_component
    )
    breakdown = {
        "prior_cases": {"value": prior_cases, "weight": W_PRIOR, "contribution": round(W_PRIOR * prior_component * 100, 1)},
        "network_centrality": {"value": round(centrality, 3), "weight": W_CENTRALITY, "contribution": round(W_CENTRALITY * centrality_component * 100, 1)},
        "recency": {"value": round(recency_component, 2), "weight": W_RECENCY, "contribution": round(W_RECENCY * recency_component * 100, 1)},
        "crime_type_versatility": {"value": len(crime_types), "weight": W_VERSATILITY, "contribution": round(W_VERSATILITY * versatility_component * 100, 1)},
    }
    return round(score * 100, 1), breakdown


def profile_suspect(suspect_id: str) -> dict:
    store = get_datastore()
    matches = store.query("suspects", filters={"suspect_id": suspect_id}, limit=1)
    if not matches:
        return {"error": f"Suspect {suspect_id} not found"}
    suspect = matches[0]

    links = store.query("fir_suspect_links", filters={"suspect_id": suspect_id, "role": "Accused"}, limit=200)
    firs = []
    for link in links:
        found = store.query("fir_records", filters={"fir_id": link["fir_id"]}, limit=1)
        if found:
            firs.append(found[0])

    centrality = nx.degree_centrality(build_graph()).get(suspect_id, 0.0)
    score, breakdown = compute_risk_score(suspect, firs, centrality)

    behavioral_summary = (
        ask_safe(
            BEHAVIORAL_SYSTEM,
            f"Suspect: {suspect['name']}, modus operandi on file: {suspect.get('modus_operandi', 'Unknown')}\n"
            f"Case history (JSON): "
            f"{[{'crime_type': f['crime_type'], 'date_filed': f['date_filed'], 'status': f['status']} for f in firs]}",
            fallback="AI behavioral summary is temporarily unavailable — risk score and case history above are unaffected.",
        )
        if firs
        else "No case history on file for this suspect."
    )

    return {
        "suspect_id": suspect_id,
        "name": suspect["name"],
        "modus_operandi": suspect.get("modus_operandi", ""),
        "risk_score": score,
        "risk_breakdown": breakdown,
        "behavioral_summary": behavioral_summary,
        "case_history": [
            {"fir_id": f["fir_id"], "crime_type": f["crime_type"], "date_filed": f["date_filed"], "status": f["status"]}
            for f in firs
        ],
    }


def top_risk_suspects(limit: int = 15) -> list[dict]:
    """Priority investigation list: highest-risk suspects ranked by score."""
    store = get_datastore()
    suspects = store.query("suspects", limit=1000)
    centrality = nx.degree_centrality(build_graph())

    all_links = store.query("fir_suspect_links", limit=10000)
    all_firs = {f["fir_id"]: f for f in store.query("fir_records", limit=10000)}
    firs_by_suspect = defaultdict(list)
    for link in all_links:
        if link["role"] == "Accused" and link["fir_id"] in all_firs:
            firs_by_suspect[link["suspect_id"]].append(all_firs[link["fir_id"]])

    results = []
    for s in suspects:
        firs = firs_by_suspect.get(s["suspect_id"], [])
        score, _ = compute_risk_score(s, firs, centrality.get(s["suspect_id"], 0.0))
        results.append({
            "suspect_id": s["suspect_id"],
            "name": s["name"],
            "risk_score": score,
            "prior_cases": _num(s.get("prior_cases")),
            "modus_operandi": s.get("modus_operandi", ""),
        })
    results.sort(key=lambda r: -r["risk_score"])
    return results[:limit]
