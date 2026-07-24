from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel

from app.core.catalyst_auth import get_current_user
from app.core.rbac import log_action, recent_audit_log, require_role
from app.services import (
    analytics,
    decision_support,
    financial,
    forecasting,
    graph_builder,
    pdf_export,
    profiling,
    query_engine,
    sociological,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


class ConversationTurn(BaseModel):
    question: str
    answer: str
    sql: str | None = None


class NLQuery(BaseModel):
    question: str
    history: list[ConversationTurn] | None = None


@router.post("/query")
def nl_query(body: NLQuery, role: str = Depends(require_role("query"))):
    history = [t.model_dump() for t in body.history] if body.history else None
    result = query_engine.run_nl_query(body.question, history=history)
    log_action(role, "/api/query", body.question)
    return result


class ExportPdfRequest(BaseModel):
    conversation: list[ConversationTurn]


@router.post("/export-pdf")
def export_pdf(body: ExportPdfRequest, role: str = Depends(require_role("query"))):
    pdf_bytes = pdf_export.build_conversation_pdf([t.model_dump() for t in body.conversation])
    log_action(role, "/api/export-pdf", f"{len(body.conversation)} turns")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=kaval_ai_conversation.pdf"},
    )


@router.get("/graph")
def suspect_graph(include_victims: bool = False, role: str = Depends(require_role("graph"))):
    log_action(role, "/api/graph", f"include_victims={include_victims}")
    return graph_builder.graph_summary(include_victims=include_victims)


@router.get("/analytics")
def analytics_stats(
    language: str = Query("en", pattern="^(en|kn)$"),
    summary: bool = False,
    role: str = Depends(require_role("analytics")),
):
    log_action(role, "/api/analytics", f"language={language} summary={summary}")
    if summary:
        return analytics.stats_with_summary(language)
    return analytics.compute_stats()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/profiling/top")
def profiling_top(limit: int = 15, role: str = Depends(require_role("profiling"))):
    log_action(role, "/api/profiling/top", f"limit={limit}")
    return {"suspects": profiling.top_risk_suspects(limit=limit)}


@router.get("/profiling/{suspect_id}")
def profiling_detail(suspect_id: str, role: str = Depends(require_role("profiling"))):
    log_action(role, "/api/profiling/{suspect_id}", suspect_id)
    return profiling.profile_suspect(suspect_id)


@router.get("/sociological")
def sociological_view(
    language: str = Query("en", pattern="^(en|kn)$"),
    role: str = Depends(require_role("sociological")),
):
    log_action(role, "/api/sociological", f"language={language}")
    return sociological.sociological_insights(language)


@router.get("/financial")
def financial_view(role: str = Depends(require_role("financial"))):
    log_action(role, "/api/financial", "viewed financial network")
    return financial.financial_network()


@router.get("/forecast")
def forecast_view(role: str = Depends(require_role("forecast"))):
    log_action(role, "/api/forecast", "viewed forecast")
    return forecasting.compute_forecast()


@router.get("/case-summary/{fir_id}")
def case_summary_view(fir_id: str, role: str = Depends(require_role("decision_support"))):
    log_action(role, "/api/case-summary/{fir_id}", fir_id)
    return decision_support.case_summary(fir_id)


@router.get("/audit-log")
def audit_log_view(limit: int = 100, role: str = Depends(require_role("audit_log"))):
    return {"entries": recent_audit_log(limit=limit)}


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
