"""Generate synthetic Karnataka State Police FIR/suspect data and load it
into the datastore (SQLite locally, Catalyst Data Store when deployed).

Run from the project root:  python -m data.seed
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.catalyst_datastore import get_datastore

random.seed(42)

DISTRICTS = {
    "Bengaluru Urban": {
        "stations": ["Cubbon Park PS", "Indiranagar PS", "Jayanagar PS", "Whitefield PS", "Yeshwanthpur PS"],
        "areas": ["MG Road", "Indiranagar", "Jayanagar 4th Block", "Whitefield", "Malleshwaram", "Koramangala"],
    },
    "Mysuru": {
        "stations": ["Devaraja PS", "Lashkar PS", "VV Puram PS"],
        "areas": ["Devaraja Mohalla", "Lashkar Mohalla", "Kuvempunagar", "Hebbal Industrial Area"],
    },
    "Mangaluru": {
        "stations": ["Mangaluru North PS", "Kadri PS", "Panambur PS"],
        "areas": ["Hampankatta", "Kadri", "Panambur", "Surathkal"],
    },
    "Hubballi-Dharwad": {
        "stations": ["Hubballi City PS", "Dharwad PS"],
        "areas": ["Vidyanagar", "Gokul Road", "Old Hubballi", "Dharwad Market"],
    },
}

CRIME_TYPES = [
    ("Theft", "IPC 379", 0.28),
    ("Assault", "IPC 323", 0.16),
    ("Cybercrime", "IT Act 66", 0.14),
    ("Robbery", "IPC 392", 0.10),
    ("Burglary", "IPC 457", 0.10),
    ("Fraud", "IPC 420", 0.09),
    ("Vehicle Theft", "IPC 379A", 0.08),
    ("Chain Snatching", "IPC 356", 0.05),
]

FIRST_NAMES = [
    "Ravi", "Suresh", "Manjunath", "Prakash", "Kiran", "Santosh", "Venkatesh",
    "Lokesh", "Harish", "Nagesh", "Deepa", "Lakshmi", "Sunita", "Rekha",
    "Anand", "Girish", "Mahesh", "Basavaraj", "Shivakumar", "Raghavendra",
]
LAST_NAMES = [
    "Kumar", "Gowda", "Reddy", "Shetty", "Rao", "Naik", "Hegde", "Patil",
    "Shastri", "Acharya", "Murthy", "Swamy",
]

DESCRIPTION_TEMPLATES = {
    "Theft": "Complainant reported theft of {item} from {place} in {area}. Estimated value Rs. {value}.",
    "Assault": "Physical altercation reported near {place} in {area}. Complainant sustained minor injuries.",
    "Cybercrime": "Complainant reported online fraud of Rs. {value} via {cyber_mode}. Transaction traced to unknown account.",
    "Robbery": "Armed robbery reported at {place} in {area}. Cash and valuables worth Rs. {value} taken.",
    "Burglary": "House break-in reported in {area} during night hours. Jewellery and cash worth Rs. {value} stolen.",
    "Fraud": "Complainant defrauded of Rs. {value} in a {fraud_mode} scheme operating in {area}.",
    "Vehicle Theft": "Two-wheeler bearing registration KA-{reg} stolen from parking area near {place}, {area}.",
    "Chain Snatching": "Gold chain snatched from complainant by two persons on a motorcycle near {place}, {area}.",
}

ITEMS = ["a mobile phone", "a laptop", "cash", "gold ornaments", "a bicycle"]
PLACES = ["the bus stand", "a shopping complex", "the market", "a residential building", "the railway station", "a parking lot"]
CYBER_MODES = ["a fake UPI payment link", "an OTP scam call", "a fraudulent job portal", "a phishing email"]
FRAUD_MODES = ["chit fund", "fake investment", "real-estate advance", "loan processing fee"]

N_FIRS = 400
N_SUSPECTS = 120


def make_suspects():
    suspects = []
    all_areas = [a for d in DISTRICTS.values() for a in d["areas"]]
    for i in range(1, N_SUSPECTS + 1):
        suspects.append({
            "suspect_id": f"SUS-{i:05d}",
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "age": random.randint(18, 60),
            "gender": random.choices(["Male", "Female"], weights=[0.8, 0.2])[0],
            "known_address": random.choice(all_areas),
            "prior_cases": random.choices([0, 1, 2, 3, 5, 8], weights=[40, 25, 15, 10, 7, 3])[0],
        })
    return suspects


def make_description(crime_type, area):
    return DESCRIPTION_TEMPLATES[crime_type].format(
        item=random.choice(ITEMS),
        place=random.choice(PLACES),
        area=area,
        value=random.choice([5000, 12000, 25000, 40000, 75000, 150000, 300000]),
        cyber_mode=random.choice(CYBER_MODES),
        fraud_mode=random.choice(FRAUD_MODES),
        reg=f"{random.randint(1, 60):02d}-{random.choice('ABCDEFGH')}{random.choice('JKLMNPQR')}-{random.randint(1000, 9999)}",
    )


def make_firs():
    firs = []
    crime_names = [c[0] for c in CRIME_TYPES]
    crime_weights = [c[2] for c in CRIME_TYPES]
    sections = {c[0]: c[1] for c in CRIME_TYPES}
    start = date(2025, 1, 1)
    for i in range(1, N_FIRS + 1):
        district = random.choices(
            list(DISTRICTS), weights=[0.5, 0.2, 0.15, 0.15]
        )[0]
        d = DISTRICTS[district]
        crime = random.choices(crime_names, weights=crime_weights)[0]
        area = random.choice(d["areas"])
        firs.append({
            "fir_id": f"FIR-{2025 + (i > 300)}-{i:05d}",
            "date_filed": (start + timedelta(days=random.randint(0, 540))).isoformat(),
            "police_station": random.choice(d["stations"]),
            "district": district,
            "crime_type": crime,
            "area": area,
            "description": make_description(crime, area),
            "status": random.choices(
                ["Open", "Under Investigation", "Closed"], weights=[0.3, 0.4, 0.3]
            )[0],
            "section_of_law": sections[crime],
        })
    return firs


def make_links(firs, suspects):
    """Link suspects to FIRs. A subset of suspects are 'repeat offenders' who
    appear in many FIRs — this is what makes the network graph interesting."""
    links = []
    suspect_ids = [s["suspect_id"] for s in suspects]
    repeat_offenders = random.sample(suspect_ids, 15)
    for fir in firs:
        n_accused = random.choices([0, 1, 2, 3], weights=[0.25, 0.45, 0.2, 0.1])[0]
        pool = repeat_offenders if random.random() < 0.4 else suspect_ids
        for sid in random.sample(pool, min(n_accused, len(pool))):
            links.append({"fir_id": fir["fir_id"], "suspect_id": sid, "role": "Accused"})
        if random.random() < 0.3:
            witness = random.choice(suspect_ids)
            links.append({"fir_id": fir["fir_id"], "suspect_id": witness, "role": "Witness"})
    return links


def make_associations(suspects):
    assocs = []
    suspect_ids = [s["suspect_id"] for s in suspects]
    # a few gang clusters
    for _ in range(6):
        gang = random.sample(suspect_ids, random.randint(3, 6))
        for i in range(len(gang)):
            for j in range(i + 1, len(gang)):
                assocs.append({
                    "suspect_id_a": gang[i],
                    "suspect_id_b": gang[j],
                    "relation_type": "Gang",
                    "confidence": round(random.uniform(0.6, 0.95), 2),
                })
    # scattered family/associate ties
    for _ in range(60):
        a, b = random.sample(suspect_ids, 2)
        assocs.append({
            "suspect_id_a": a,
            "suspect_id_b": b,
            "relation_type": random.choice(["Family", "Associate", "Co-accused"]),
            "confidence": round(random.uniform(0.3, 0.9), 2),
        })
    return assocs


SQLITE_DDL = {
    "fir_records": {
        "fir_id": "TEXT PRIMARY KEY", "date_filed": "TEXT", "police_station": "TEXT",
        "district": "TEXT", "crime_type": "TEXT", "area": "TEXT",
        "description": "TEXT", "status": "TEXT", "section_of_law": "TEXT",
    },
    "suspects": {
        "suspect_id": "TEXT PRIMARY KEY", "name": "TEXT", "age": "INTEGER",
        "gender": "TEXT", "known_address": "TEXT", "prior_cases": "INTEGER",
    },
    "fir_suspect_links": {"fir_id": "TEXT", "suspect_id": "TEXT", "role": "TEXT"},
    "suspect_associations": {
        "suspect_id_a": "TEXT", "suspect_id_b": "TEXT",
        "relation_type": "TEXT", "confidence": "REAL",
    },
}


def main():
    store = get_datastore()

    if hasattr(store, "db_path"):
        db_file = Path(store.db_path)
        if db_file.exists():
            db_file.unlink()
        for table, ddl in SQLITE_DDL.items():
            store.create_table(table, ddl)

    suspects = make_suspects()
    firs = make_firs()
    links = make_links(firs, suspects)
    assocs = make_associations(suspects)

    store.bulk_insert("suspects", suspects)
    store.bulk_insert("fir_records", firs)
    store.bulk_insert("fir_suspect_links", links)
    store.bulk_insert("suspect_associations", assocs)

    print(f"Seeded: {len(firs)} FIRs, {len(suspects)} suspects, "
          f"{len(links)} FIR-suspect links, {len(assocs)} associations")


if __name__ == "__main__":
    main()
