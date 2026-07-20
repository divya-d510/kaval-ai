from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.catalyst_auth import get_current_user
from app.services import analytics, graph_builder, query_engine

router = APIRouter(dependencies=[Depends(get_current_user)])


class NLQuery(BaseModel):
    question: str


@router.post("/query")
def nl_query(body: NLQuery):
    return query_engine.run_nl_query(body.question)


@router.get("/graph")
def suspect_graph():
    return graph_builder.graph_summary()


@router.get("/analytics")
def analytics_stats(language: str = Query("en", pattern="^(en|kn)$"), summary: bool = False):
    if summary:
        return analytics.stats_with_summary(language)
    return analytics.compute_stats()


@router.get("/health")
def health():
    return {"status": "ok"}


class SeedRows(BaseModel):
    table: str
    rows: list[dict]


@router.post("/debug/seed")
def debug_seed(body: SeedRows):
    """Temporary diagnostics: bulk-insert rows into the active datastore."""
    import os

    if os.getenv("DEBUG_ERRORS", "true").lower() != "true":
        return {"error": "disabled"}
    from app.core.catalyst_datastore import get_datastore

    get_datastore().bulk_insert(body.table, body.rows)
    return {"inserted": len(body.rows), "table": body.table}


@router.get("/debug/zcql")
def debug_zcql(q: str):
    """Temporary diagnostics: run raw ZCQL/SQL against the active datastore."""
    import os

    if os.getenv("DEBUG_ERRORS", "true").lower() != "true":
        return {"error": "disabled"}
    from app.core.catalyst_datastore import get_datastore

    return {"rows": get_datastore().execute_query(q)[:50]}
