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
N_VICTIMS = 320

SOCIO_ECONOMIC_BANDS = ["Low", "Middle", "High"]
EDUCATION_LEVELS = ["Illiterate", "Primary", "Secondary", "Graduate", "Postgraduate"]
MODUS_OPERANDI = ["Opportunistic - unarmed", "Organized - armed", "Cyber-enabled", "Repeat pattern - same MO"]

CRIME_IMPACTS = {
    "Theft": ["Financial loss", "Property damage"],
    "Assault": ["Physical injury", "Emotional distress"],
    "Cybercrime": ["Financial loss", "Emotional distress"],
    "Robbery": ["Financial loss", "Physical injury"],
    "Burglary": ["Property damage", "Financial loss"],
    "Fraud": ["Financial loss", "Emotional distress"],
    "Vehicle Theft": ["Financial loss", "Property damage"],
    "Chain Snatching": ["Financial loss", "Physical injury"],
}

BANKS = ["SBI", "Canara Bank", "HDFC Bank", "ICICI Bank", "Karnataka Bank", "Union Bank"]
ACCOUNT_TYPES = ["Savings", "Current", "Wallet"]


def _modus_for(prior_cases):
    """Repeat offenders skew toward organized/repeat-pattern MOs."""
    if prior_cases >= 5:
        return random.choices(MODUS_OPERANDI, weights=[15, 35, 15, 35])[0]
    if prior_cases >= 2:
        return random.choices(MODUS_OPERANDI, weights=[30, 25, 20, 25])[0]
    return random.choices(MODUS_OPERANDI, weights=[45, 15, 30, 10])[0]


def make_suspects():
    suspects = []
    all_areas = [a for d in DISTRICTS.values() for a in d["areas"]]
    for i in range(1, N_SUSPECTS + 1):
        prior_cases = random.choices([0, 1, 2, 3, 5, 8], weights=[40, 25, 15, 10, 7, 3])[0]
        suspects.append({
            "suspect_id": f"SUS-{i:05d}",
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "age": random.randint(18, 60),
            "gender": random.choices(["Male", "Female"], weights=[0.8, 0.2])[0],
            "known_address": random.choice(all_areas),
            "prior_cases": prior_cases,
            "socio_economic_band": random.choices(SOCIO_ECONOMIC_BANDS, weights=[0.45, 0.4, 0.15])[0],
            "education_level": random.choices(EDUCATION_LEVELS, weights=[0.1, 0.25, 0.35, 0.25, 0.05])[0],
            "modus_operandi": _modus_for(prior_cases),
        })
    return suspects


def make_victims():
    victims = []
    all_areas = [a for d in DISTRICTS.values() for a in d["areas"]]
    for i in range(1, N_VICTIMS + 1):
        victims.append({
            "victim_id": f"VIC-{i:05d}",
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "age": random.randint(18, 75),
            "gender": random.choices(["Male", "Female"], weights=[0.55, 0.45])[0],
            "contact_area": random.choice(all_areas),
        })
    return victims


def make_victim_links(firs, victims):
    links = []
    victim_ids = [v["victim_id"] for v in victims]
    pool = list(victim_ids)
    for fir in firs:
        n_victims = random.choices([0, 1, 2], weights=[0.15, 0.7, 0.15])[0]
        for _ in range(n_victims):
            if not pool:
                pool = list(victim_ids)
            vid = pool.pop(random.randrange(len(pool)))
            impact = random.choice(CRIME_IMPACTS.get(fir["crime_type"], ["Financial loss"]))
            links.append({"fir_id": fir["fir_id"], "victim_id": vid, "impact": impact})
    return links


def make_financial(suspects, firs):
    """A subset of suspects (biased toward repeat offenders and financial-crime
    types) hold accounts. Transaction structure is deliberately non-random so
    the mule-account heuristic (3+ distinct counterparties) means something:
    most accounts only ever transact within a small, persistent cluster of
    2-3 regular counterparties, while a handful of designated 'hub' accounts
    fan out widely — those are the ones that should get flagged."""
    candidates = [s for s in suspects if s["prior_cases"] >= 1]
    if len(candidates) < 50:
        candidates = suspects
    holders = random.sample(candidates, min(55, len(candidates)))

    accounts = []
    acc_no = 1
    for s in holders:
        n_acc = random.choices([1, 2], weights=[0.7, 0.3])[0]
        for _ in range(n_acc):
            acc_id = f"ACC-{acc_no:05d}"
            acc_no += 1
            accounts.append({
                "account_id": acc_id,
                "suspect_id": s["suspect_id"],
                "bank_name": random.choice(BANKS),
                "account_number_masked": f"XXXX-XXXX-{random.randint(1000, 9999)}",
                "account_type": random.choices(ACCOUNT_TYPES, weights=[0.55, 0.25, 0.2])[0],
            })
    account_ids = [a["account_id"] for a in accounts]

    hub_accounts = random.sample(account_ids, min(4, len(account_ids)))
    remaining = [a for a in account_ids if a not in hub_accounts]
    random.shuffle(remaining)
    clusters = []
    i = 0
    while i < len(remaining):
        size = random.choice([2, 2, 3])
        clusters.append(remaining[i:i + size])
        i += size
    clusters = [c for c in clusters if len(c) >= 2]

    fraud_firs = [f["fir_id"] for f in firs if f["crime_type"] in ("Cybercrime", "Fraud")]
    start = date(2025, 1, 1)
    transactions = []
    txn_no = 1

    def add_txn(from_acc, to_acc):
        nonlocal txn_no
        amount = random.choice([500, 2000, 5000, 15000, 40000, 90000, 200000, 450000])
        linked_fir = random.choice(fraud_firs) if fraud_firs and random.random() < 0.08 else None
        flagged = amount >= 200000 or linked_fir is not None
        reason = None
        if linked_fir is not None:
            reason = "Linked to an open Cybercrime/Fraud FIR"
        elif amount >= 200000:
            reason = "High-value transfer above Rs. 2,00,000"
        transactions.append({
            "transaction_id": f"TXN-{txn_no:06d}",
            "from_account_id": from_acc,
            "to_account_id": to_acc,
            "amount": amount,
            "txn_date": (start + timedelta(days=random.randint(0, 540))).isoformat(),
            "fir_id": linked_fir or "",
            "flagged_suspicious": 1 if flagged else 0,
            "flag_reason": reason or "",
        })
        txn_no += 1

    # Normal activity: repeated transfers within each small persistent cluster
    for cluster in clusters:
        for _ in range(random.randint(2, 5)):
            a, b = random.sample(cluster, 2)
            add_txn(a, b)

    # Hub accounts: fan out to many distinct counterparties (the mule pattern)
    for hub in hub_accounts:
        others = random.sample([a for a in account_ids if a != hub], min(8, len(account_ids) - 1))
        for other in others:
            add_txn(hub, other)

    # Top up toward a healthy transaction count with more ordinary cluster activity
    while len(transactions) < 240 and clusters:
        cluster = random.choice(clusters)
        a, b = random.sample(cluster, 2)
        add_txn(a, b)

    return accounts, transactions


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
        "socio_economic_band": "TEXT", "education_level": "TEXT", "modus_operandi": "TEXT",
    },
    "fir_suspect_links": {"fir_id": "TEXT", "suspect_id": "TEXT", "role": "TEXT"},
    "suspect_associations": {
        "suspect_id_a": "TEXT", "suspect_id_b": "TEXT",
        "relation_type": "TEXT", "confidence": "REAL",
    },
    "victims": {
        "victim_id": "TEXT PRIMARY KEY", "name": "TEXT", "age": "INTEGER",
        "gender": "TEXT", "contact_area": "TEXT",
    },
    "fir_victim_links": {"fir_id": "TEXT", "victim_id": "TEXT", "impact": "TEXT"},
    "financial_accounts": {
        "account_id": "TEXT PRIMARY KEY", "suspect_id": "TEXT", "bank_name": "TEXT",
        "account_number_masked": "TEXT", "account_type": "TEXT",
    },
    "financial_transactions": {
        "transaction_id": "TEXT PRIMARY KEY", "from_account_id": "TEXT", "to_account_id": "TEXT",
        "amount": "REAL", "txn_date": "TEXT", "fir_id": "TEXT",
        "flagged_suspicious": "INTEGER", "flag_reason": "TEXT",
    },
    "audit_log": {
        "log_id": "TEXT PRIMARY KEY", "logged_at": "TEXT", "role": "TEXT",
        "endpoint": "TEXT", "summary": "TEXT",
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
    victims = make_victims()
    victim_links = make_victim_links(firs, victims)
    accounts, transactions = make_financial(suspects, firs)

    store.bulk_insert("suspects", suspects)
    store.bulk_insert("fir_records", firs)
    store.bulk_insert("fir_suspect_links", links)
    store.bulk_insert("suspect_associations", assocs)
    store.bulk_insert("victims", victims)
    store.bulk_insert("fir_victim_links", victim_links)
    store.bulk_insert("financial_accounts", accounts)
    store.bulk_insert("financial_transactions", transactions)

    print(f"Seeded: {len(firs)} FIRs, {len(suspects)} suspects, "
          f"{len(links)} FIR-suspect links, {len(assocs)} associations, "
          f"{len(victims)} victims, {len(victim_links)} FIR-victim links, "
          f"{len(accounts)} financial accounts, {len(transactions)} transactions")


if __name__ == "__main__":
    main()
