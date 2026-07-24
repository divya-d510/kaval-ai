import os
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.catalyst_datastore import request_headers_var

app = FastAPI(
    title="KSP Crime Analytics API",
    description="Bilingual (English/Kannada) NL querying, suspect-network graphs, "
    "and analytics over Karnataka State Police FIR data.",
    version="0.1.0",
)

# The Catalyst-native frontend (catalyst_frontend/) calls this API directly from
# browser JS rather than a server-side process, so it's a cross-origin request —
# unlike the Streamlit frontend, which calls it server-side and never needed CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-User-Role"],
)

app.include_router(router, prefix="/api")


@app.middleware("http")
async def capture_catalyst_headers(request: Request, call_next):
    request_headers_var.set(dict(request.headers))
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    detail = {"error": type(exc).__name__, "message": str(exc)}
    if os.getenv("DEBUG_ERRORS", "true").lower() == "true":
        detail["trace"] = traceback.format_exc(limit=8)
    return JSONResponse(status_code=500, content=detail)
