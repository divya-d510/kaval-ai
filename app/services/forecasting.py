"""Crime forecasting & early warning.

This is a transparent trend-extrapolation heuristic (linear regression over
the last few months per district+crime_type), not a trained ML model — framed
honestly as a first-pass indicator, not a calibrated forecast.
"""

from collections import defaultdict

from app.core.catalyst_datastore import get_datastore

TREND_WINDOW = 6  # months considered
WARNING_THRESHOLD = 1.5  # projected >= 1.5x recent 3-month average triggers a flag


def compute_forecast() -> dict:
    firs = get_datastore().query("fir_records", limit=10000)

    counts = defaultdict(lambda: defaultdict(int))
    months = set()
    for f in firs:
        m = f["date_filed"][:7]
        months.add(m)
        counts[(f["district"], f["crime_type"])][m] += 1

    recent_months = sorted(months)[-TREND_WINDOW:]

    projections = []
    for (district, crime_type), by_month in counts.items():
        series = [by_month.get(m, 0) for m in recent_months]
        if len(series) < 3 or sum(series) < 3:
            continue

        n = len(series)
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(series) / n
        num = sum((xs[i] - x_mean) * (series[i] - y_mean) for i in range(n))
        den = sum((xs[i] - x_mean) ** 2 for i in range(n)) or 1
        slope = num / den
        next_projection = max(0.0, round(y_mean + slope * (n - x_mean), 1))
        recent_avg = sum(series[-3:]) / 3

        projections.append({
            "district": district,
            "crime_type": crime_type,
            "recent_months": recent_months,
            "monthly_counts": series,
            "trend_slope": round(slope, 2),
            "next_month_projection": next_projection,
            "early_warning": bool(recent_avg > 0 and next_projection >= WARNING_THRESHOLD * recent_avg),
        })

    projections.sort(key=lambda p: -p["trend_slope"])

    return {
        "window_months": recent_months,
        "projections": projections[:20],
        "early_warnings": [p for p in projections if p["early_warning"]],
    }
