"""Role-based access control and audit logging.

This simulates authentication/authorization for the prototype: the frontend
lets the user pick a role (Investigator/Analyst/Supervisor/Policymaker) and
sends it as the X-User-Role header on every request. There is no real login
yet — AUTH_ENABLED gates a separate, session-level check (see catalyst_auth.py)
for validating the request actually came through Catalyst. Wiring role
selection to a real identity provider is tracked as follow-up work; see the
README's Security Notes.
"""

import uuid
from datetime import datetime, timezone

from fastapi import Header, HTTPException

from app.core.catalyst_datastore import get_datastore

ROLES = ["Investigator", "Analyst", "Supervisor", "Policymaker"]

# Endpoint group -> roles allowed to call it.
PERMISSIONS = {
    "query": {"Investigator", "Analyst", "Supervisor"},
    "analytics": {"Investigator", "Analyst", "Supervisor", "Policymaker"},
    "graph": {"Investigator", "Analyst", "Supervisor"},
    "profiling": {"Investigator", "Analyst", "Supervisor"},
    "sociological": {"Investigator", "Analyst", "Supervisor", "Policymaker"},
    "financial": {"Supervisor"},
    "forecast": {"Investigator", "Analyst", "Supervisor", "Policymaker"},
    "decision_support": {"Investigator", "Analyst", "Supervisor"},
    "audit_log": {"Supervisor"},
}


def require_role(group: str):
    allowed = PERMISSIONS[group]

    def dependency(x_user_role: str = Header(default="Investigator")) -> str:
        if x_user_role not in ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role '{x_user_role}'. Valid roles: {ROLES}")
        if x_user_role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{x_user_role}' is not permitted to access this resource. Allowed: {sorted(allowed)}",
            )
        return x_user_role

    return dependency


def log_action(role: str, endpoint: str, summary: str) -> None:
    """Best-effort audit log write — never lets a logging failure break the request."""
    try:
        get_datastore().bulk_insert("audit_log", [{
            "log_id": f"LOG-{uuid.uuid4().hex[:12]}",
            "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "role": role,
            "endpoint": endpoint,
            "summary": summary[:300],
        }])
    except Exception:
        pass


def recent_audit_log(limit: int = 100) -> list[dict]:
    rows = get_datastore().query("audit_log", limit=limit)
    return sorted(rows, key=lambda r: r.get("logged_at", ""), reverse=True)
