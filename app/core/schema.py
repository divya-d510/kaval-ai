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
        },
        "description": "One row per known suspect/accused individual.",
    },
    "fir_suspect_links": {
        "columns": {
            "fir_id": "string, foreign key -> fir_records.fir_id",
            "suspect_id": "string, foreign key -> suspects.suspect_id",
            "role": "string, one of 'Accused', 'Witness', 'Victim'",
        },
        "description": "Many-to-many link between FIRs and the people involved in them.",
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
}
