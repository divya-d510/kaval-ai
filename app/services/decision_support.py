"""Investigator decision support: case summaries, similar-past-case search,
and LLM-suggested investigative leads.

Similarity is by shared attributes (crime type, district, area) — a
transparent, explainable similarity measure, not embeddings.
"""

from app.core.catalyst_datastore import get_datastore
from app.core.llm_client import ask_safe

CASE_SUMMARY_SYSTEM = """You are an investigation support analyst for Karnataka State Police.
Given a case file (FIR details, accused, victims, similar past case count) as JSON, write:

Summary: a concise 3-4 sentence case summary.
Suggested leads: 2-4 specific investigative leads to pursue, grounded only in the given facts.

Do not speculate beyond the given data. Write in English."""


def _similar_cases(fir: dict, all_firs: list[dict], limit: int = 5) -> list[dict]:
    scored = []
    for other in all_firs:
        if other["fir_id"] == fir["fir_id"]:
            continue
        score = 0
        if other["crime_type"] == fir["crime_type"]:
            score += 2
        if other["district"] == fir["district"]:
            score += 1
        if other["area"] == fir["area"]:
            score += 1
        if score > 0:
            scored.append((score, other))
    scored.sort(key=lambda x: -x[0])
    return [
        {
            "fir_id": o["fir_id"], "crime_type": o["crime_type"], "district": o["district"],
            "area": o["area"], "status": o["status"], "date_filed": o["date_filed"], "match_score": s,
        }
        for s, o in scored[:limit]
    ]


def case_summary(fir_id: str) -> dict:
    store = get_datastore()
    matches = store.query("fir_records", filters={"fir_id": fir_id}, limit=1)
    if not matches:
        return {"error": f"FIR {fir_id} not found"}
    fir = matches[0]

    links = store.query("fir_suspect_links", filters={"fir_id": fir_id}, limit=50)
    accused_ids = {l["suspect_id"] for l in links if l["role"] == "Accused"}
    accused = [s for s in store.query("suspects", limit=1000) if s["suspect_id"] in accused_ids]

    victim_links = store.query("fir_victim_links", filters={"fir_id": fir_id}, limit=50)
    victim_ids = {l["victim_id"] for l in victim_links}
    victims = [v for v in store.query("victims", limit=2000) if v["victim_id"] in victim_ids]

    similar = _similar_cases(fir, store.query("fir_records", limit=10000))

    llm_input = {
        "fir": {k: fir[k] for k in ("fir_id", "date_filed", "crime_type", "district", "area", "description", "status")},
        "accused": [{"name": s["name"], "prior_cases": s["prior_cases"], "modus_operandi": s.get("modus_operandi", "")} for s in accused],
        "victims": [{"name": v["name"], "age": v["age"]} for v in victims],
        "similar_case_count": len(similar),
    }
    narrative = ask_safe(
        CASE_SUMMARY_SYSTEM,
        f"Case file (JSON): {llm_input}",
        fallback="AI case summary is temporarily unavailable — accused/victim/similar-case data above is unaffected.",
    )

    return {
        "fir": fir,
        "accused": [
            {"suspect_id": s["suspect_id"], "name": s["name"], "prior_cases": s["prior_cases"],
             "modus_operandi": s.get("modus_operandi", "")}
            for s in accused
        ],
        "victims": [{"victim_id": v["victim_id"], "name": v["name"]} for v in victims],
        "similar_cases": similar,
        "narrative": narrative,
    }
