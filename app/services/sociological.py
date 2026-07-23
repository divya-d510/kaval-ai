"""Sociological crime insights: demographic breakdowns of accused persons and
simple descriptive correlations between socio-economic indicators and crime
concentration.

These are observed patterns in this seeded dataset, presented as descriptive
statistics — not causal claims, and the LLM briefing is instructed to say so.
"""

import json
from collections import Counter, defaultdict

from app.core.catalyst_datastore import get_datastore
from app.core.llm_client import ask_safe

INSIGHT_SYSTEM = """You are a sociologist supporting Karnataka State Police crime analysis.
Given demographic breakdowns of accused persons (JSON), write a short briefing (4-6 sentences)
on the observed social patterns. Explicitly note these are correlations observed in this
dataset, not causal claims. Write in the requested language (en=English, kn=Kannada)."""


def compute_sociological_stats() -> dict:
    store = get_datastore()
    suspects = store.query("suspects", limit=1000)
    links = store.query("fir_suspect_links", limit=10000)
    firs = {f["fir_id"]: f for f in store.query("fir_records", limit=10000)}

    by_gender = Counter(s["gender"] for s in suspects)
    by_socio_band = Counter(s["socio_economic_band"] for s in suspects)
    by_education = Counter(s["education_level"] for s in suspects)

    suspect_band = {s["suspect_id"]: s["socio_economic_band"] for s in suspects}
    band_crime = defaultdict(Counter)
    for link in links:
        if link["role"] != "Accused":
            continue
        fir = firs.get(link["fir_id"])
        band = suspect_band.get(link["suspect_id"])
        if fir and band:
            band_crime[band][fir["crime_type"]] += 1

    area_suspect_count = Counter()
    area_low_band_count = Counter()
    for s in suspects:
        area_suspect_count[s["known_address"]] += 1
        if s["socio_economic_band"] == "Low":
            area_low_band_count[s["known_address"]] += 1
    area_low_band_share = {
        area: round(area_low_band_count[area] / area_suspect_count[area], 2)
        for area in area_suspect_count
    }

    area_crime_count = Counter(f["area"] for f in firs.values())

    return {
        "by_gender": dict(by_gender),
        "by_socio_economic_band": dict(by_socio_band),
        "by_education_level": dict(by_education),
        "crime_type_by_socio_band": {band: dict(c.most_common()) for band, c in band_crime.items()},
        "area_low_band_share": area_low_band_share,
        "area_crime_count": dict(area_crime_count.most_common(10)),
    }


def sociological_insights(language: str = "en") -> dict:
    stats = compute_sociological_stats()
    summary = ask_safe(
        INSIGHT_SYSTEM,
        f"Language: {language}\n\nDemographic breakdowns:\n{json.dumps(stats, ensure_ascii=False)}",
        fallback="AI briefing is temporarily unavailable — the breakdowns above are unaffected.",
    )
    return {**stats, "summary": summary}
