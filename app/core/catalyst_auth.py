"""Catalyst Authentication wrapper.

In production (AppSail), validates the Catalyst user session from request
cookies/headers via zcatalyst-sdk. Locally (AUTH_ENABLED unset/false) it's a
no-op so the app is fully testable before Catalyst is provisioned.
"""

import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request

load_dotenv()

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"


def get_current_user(request: Request) -> dict:
    if not AUTH_ENABLED:
        return {"user_id": "local-dev", "email": "dev@localhost", "role": "admin"}

    import zcatalyst_sdk

    try:
        app = zcatalyst_sdk.initialize(req=request)
        user = app.authentication().get_current_user()
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {
            "user_id": user.get("user_id"),
            "email": user.get("email_id"),
            "role": user.get("role_details", {}).get("role_name", "user"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
