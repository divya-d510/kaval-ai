"""Table schemas shared by the seeder (data/seed.py) and the NL->SQL query engine.

Single source of truth so Claude's prompt context and the actual Data Store
tables never drift apart.
"""

TABLE_SCHEMAS = {
    "fir_records": {
        "columns": {
            "fir_id": "string, primary key, e.g. 'FIR-2026-00123'",
            "date_filed": "string, ISO date 'YYYY-MM-DD'",
            "police_station": "string, e.g. 'Cubbon Park PS'",
            "district": "string, e.g. 'Bengaluru Urban'",
            "crime_type": "string, e.g. 'Theft', 'Assault', 'Cybercrime', 'Robbery'",
            "area": "string, locality name within the district",
            "description": "string, free-text incident summary",
            "status": "string, one of 'Open', 'Under Investigation', 'Closed'",
            "section_of_law": "string, e.g. 'IPC 379'",
        },
        "description": "One row per First Information Report filed at a police station.",
    },
    "suspects": {
        "columns": {
            "suspect_id": "string, primary key, e.g. 'SUS-00045'",
            "name": "string",
            "age": "integer",
            "gender": "string",
            "known_address": "string, locality/area",
            "prior_cases": "integer, count of prior FIRs linked to this suspect",
            "socio_economic_band": "string, one of 'Low', 'Middle', 'High'",
            "education_level": "string, one of 'Illiterate', 'Primary', 'Secondary', 'Graduate', 'Postgraduate'",
            "modus_operandi": "string, short descriptor of typical offending pattern, "
            "e.g. 'Opportunistic - unarmed', 'Organized - armed', 'Cyber-enabled', 'Repeat pattern'",
        },
        "description": "One row per known suspect/accused individual.",
    },
    "fir_suspect_links": {
        "columns": {
            "fir_id": "string, foreign key -> fir_records.fir_id",
            "suspect_id": "string, foreign key -> suspects.suspect_id",
            "role": "string, one of 'Accused', 'Witness'",
        },
        "description": "Many-to-many link between FIRs and the accused/witnesses involved. "
        "Victims are tracked separately in victims / fir_victim_links.",
    },
    "suspect_associations": {
        "columns": {
            "suspect_id_a": "string, foreign key -> suspects.suspect_id",
            "suspect_id_b": "string, foreign key -> suspects.suspect_id",
            "relation_type": "string, one of 'Co-accused', 'Family', 'Gang', 'Associate'",
            "confidence": "number between 0 and 1, how confident this link is",
        },
        "description": "Direct associations between suspects, used as graph edges "
        "alongside co-occurrence in the same FIR.",
    },
    "victims": {
        "columns": {
            "victim_id": "string, primary key, e.g. 'VIC-00012'",
            "name": "string",
            "age": "integer",
            "gender": "string",
            "contact_area": "string, locality/area",
        },
        "description": "One row per victim of a crime, kept separate from suspects/accused.",
    },
    "fir_victim_links": {
        "columns": {
            "fir_id": "string, foreign key -> fir_records.fir_id",
            "victim_id": "string, foreign key -> victims.victim_id",
            "impact": "string, one of 'Financial loss', 'Physical injury', "
            "'Property damage', 'Emotional distress'",
        },
        "description": "Many-to-many link between FIRs and the victims involved.",
    },
}

# Tables intentionally excluded from TABLE_SCHEMAS (and therefore from the
# open-ended NL->SQL prompt): financial_accounts, financial_transactions,
# audit_log. Financial data is sensitive and role-restricted, and the audit
# log itself shouldn't be a query target — both are served by their own
# dedicated, code-controlled endpoints instead of LLM-generated SQL.
FINANCIAL_TABLE_SCHEMAS = {
    "financial_accounts": {
        "columns": {
            "account_id": "string, primary key, e.g. 'ACC-00031'",
            "suspect_id": "string, foreign key -> suspects.suspect_id (account holder)",
            "bank_name": "string",
            "account_number_masked": "string, e.g. 'XXXX-XXXX-4821'",
            "account_type": "string, one of 'Savings', 'Current', 'Wallet'",
        },
        "description": "One row per financial account linked to a known suspect.",
    },
    "financial_transactions": {
        "columns": {
            "transaction_id": "string, primary key, e.g. 'TXN-000142'",
            "from_account_id": "string, foreign key -> financial_accounts.account_id",
            "to_account_id": "string, foreign key -> financial_accounts.account_id",
            "amount": "number, INR",
            "txn_date": "string, ISO date",
            "fir_id": "string, nullable, foreign key -> fir_records.fir_id if linked to a case",
            "flagged_suspicious": "boolean (0/1)",
            "flag_reason": "string, nullable",
        },
        "description": "Transactions between known suspects' financial accounts.",
    },
}

AUDIT_LOG_SCHEMA = {
    "audit_log": {
        "columns": {
            "log_id": "string, primary key, e.g. 'LOG-000001'",
            "logged_at": "string, ISO datetime",
            "role": "string, the acting role (Investigator/Analyst/Supervisor/Policymaker)",
            "endpoint": "string, API path accessed",
            "summary": "string, short description of the action taken",
        },
        "description": "Append-only record of who accessed what, for governance/traceability.",
    },
}
