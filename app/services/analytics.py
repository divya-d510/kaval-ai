"""Aggregate crime statistics for dashboards, plus a Claude-written summary."""

import json
from collections import Counter, defaultdict

from app.core.catalyst_datastore import get_datastore
from app.core.llm_client import ask

SUMMARY_SYSTEM = """You are a crime analyst for Karnataka State Police.
Given aggregate FIR statistics (JSON), write a short briefing (4-6 sentences)
highlighting the most notable patterns: dominant crime types, hotspot districts/areas,
and case-status distribution. Write in the requested language (en=English, kn=Kannada).
Be factual — only reference the numbers given."""


def compute_stats() -> dict:
    firs = get_datastore().query("fir_records", limit=10000)

    by_crime = Counter(f["crime_type"] for f in firs)
    by_district = Counter(f["district"] for f in firs)
    by_status = Counter(f["status"] for f in firs)
    by_area = Counter(f["area"] for f in firs)

    by_month = defaultdict(int)
    for f in firs:
        by_month[f["date_filed"][:7]] += 1

    return {
        "total_firs": len(firs),
        "by_crime_type": dict(by_crime.most_common()),
        "by_district": dict(by_district.most_common()),
        "by_status": dict(by_status),
        "top_areas": dict(by_area.most_common(10)),
        "by_month": dict(sorted(by_month.items())),
    }


def stats_with_summary(language: str = "en") -> dict:
    stats = compute_stats()
    summary = ask(
        SUMMARY_SYSTEM,
        f"Language: {language}\n\nStatistics:\n{json.dumps(stats, ensure_ascii=False)}",
    )
    return {**stats, "summary": summary}
