"""Bilingual (English/Kannada) natural-language querying over the KSP datastore.

Flow: user question (any language) -> Claude generates a safe SELECT query
against the known schema -> query runs on the datastore -> Claude turns the
rows into a natural-language answer in the user's language.
"""

import json
import os
import re

from app.core.catalyst_datastore import get_datastore
from app.core.llm_client import ask_json, ask_safe
from app.core.schema import TABLE_SCHEMAS

QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "sql": {
            "type": "string",
            "description": "A single SELECT statement answering the question. "
            "SQLite-compatible syntax. Never modify data.",
        },
        "language": {
            "type": "string",
            "enum": ["en", "kn"],
            "description": "Language the user asked in: en=English, kn=Kannada",
        },
        "explanation": {
            "type": "string",
            "description": "One-line explanation of what the query does, in the user's language",
        },
    },
    "required": ["sql", "language", "explanation"],
    "additionalProperties": False,
}


def _schema_prompt() -> str:
    lines = []
    for table, meta in TABLE_SCHEMAS.items():
        lines.append(f"Table {table}: {meta['description']}")
        for col, desc in meta["columns"].items():
            lines.append(f"  - {col}: {desc}")
    return "\n".join(lines)


NL_TO_SQL_SYSTEM = f"""You are a query generator for the Karnataka State Police (KSP) crime analytics system.
Users ask questions in English or Kannada about FIR records, suspects, and their associations.

Database schema:
{_schema_prompt()}

Rules:
- Generate exactly one SELECT statement. Never INSERT/UPDATE/DELETE/DROP.
- Use only syntax valid in BOTH SQLite and Zoho ZCQL:
  * NEVER use COUNT(*) or any aggregate on * — always name a column, e.g. COUNT(fir_id).
  * Keep LIMIT at 100 or lower (the datastore caps result pages at 300 rows).
  * No subqueries, no UNION, no CTEs — single flat SELECT with WHERE/GROUP BY/ORDER BY only.
- Always add LIMIT 100 unless the question implies an aggregate.
- Kannada questions are understood directly — do not ask for translation.
- If the question mentions a place, crime type, or name, match it against the schema values
  (crime types are English strings like 'Theft', 'Cybercrime'; districts like 'Bengaluru Urban', 'Mysuru').
- NEVER drop a location, date, or crime-type constraint mentioned in the question — every
  constraint the user states must appear in the WHERE clause.
- Kannada place names map to these district values:
  ಬೆಂಗಳೂರು -> 'Bengaluru Urban'; ಮೈಸೂರು -> 'Mysuru'; ಮಂಗಳೂರು -> 'Mangaluru';
  ಹುಬ್ಬಳ್ಳಿ / ಧಾರವಾಡ -> 'Hubballi-Dharwad'.
- Kannada crime terms: ಕಳ್ಳತನ -> 'Theft'; ಸೈಬರ್ ಅಪರಾಧ -> 'Cybercrime'; ದರೋಡೆ -> 'Robbery';
  ಹಲ್ಲೆ -> 'Assault'; ವಂಚನೆ -> 'Fraud'; ಸರಗಳ್ಳತನ -> 'Chain Snatching'.
- A "Conversation so far" block may precede the current question — it is prior turns in this
  same session, most recent last. Use it ONLY to resolve references the current question makes
  to that context (e.g. "what about Mysuru instead?", "and last month?", "same but for Theft").
  Every constraint the CURRENT question states or implies still applies; do not carry forward a
  constraint the current question is clearly replacing.
"""

ANSWER_SYSTEM = """You are a helpful analyst for Karnataka State Police officers.
Given a user's question and query results (JSON rows), write a concise, factual answer.
Reply in the SAME language the user asked in (English or Kannada).
If the results are empty, say no matching records were found. Do not invent data.
Prior conversation turns may be included for context only — answer the CURRENT question."""

HISTORY_TURNS = 4  # how many prior turns to carry as context for follow-ups


def _is_safe_select(sql: str) -> bool:
    lowered = sql.strip().lower()
    if not lowered.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "attach", "pragma", ";--"]
    return not any(word in lowered for word in forbidden)


def _history_block(history: list[dict] | None) -> str:
    if not history:
        return ""
    recent = history[-HISTORY_TURNS:]
    lines = ["Conversation so far:"]
    for turn in recent:
        lines.append(f"  Q: {turn['question']}")
        lines.append(f"  A: {turn['answer']}")
    return "\n".join(lines) + "\n\n"


def run_nl_query(question: str, history: list[dict] | None = None) -> dict:
    context = _history_block(history)
    try:
        plan = ask_json(NL_TO_SQL_SYSTEM, f"{context}Current question: {question}", QUERY_SCHEMA)
    except Exception:
        return {
            "question": question,
            "sql": "",
            "rows": [],
            "answer": "Could not process the question right now — the AI service is temporarily "
            "unavailable or over its rate limit. Please try again shortly.",
            "language": "en",
        }

    # ZCQL rejects aggregates over *; ROWID is valid in both SQLite and ZCQL
    plan["sql"] = re.sub(r"(?i)count\(\s*\*\s*\)", "COUNT(ROWID)", plan["sql"])

    if not _is_safe_select(plan["sql"]):
        return {
            "question": question,
            "sql": plan["sql"],
            "rows": [],
            "answer": "Query rejected: only read-only SELECT queries are allowed.",
            "language": plan["language"],
        }

    try:
        rows = get_datastore().execute_query(plan["sql"])
    except Exception as e:
        return {
            "question": question,
            "sql": plan["sql"],
            "rows": [],
            "answer": f"Query failed to execute: {e}",
            "language": plan["language"],
        }

    answer = ask_safe(
        ANSWER_SYSTEM,
        f"{context}Question: {question}\n\nQuery run: {plan['sql']}\n\n"
        f"Results (JSON):\n{json.dumps(rows[:50], ensure_ascii=False)}",
        fallback=f"Query ran successfully but the AI answer is temporarily unavailable — "
        f"see the {len(rows)} row(s) and generated SQL above.",
    )

    return {
        "question": question,
        "sql": plan["sql"],
        "explanation": plan["explanation"],
        "rows": rows,
        "answer": answer,
        "language": plan["language"],
    }
