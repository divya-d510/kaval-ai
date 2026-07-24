"""Catalyst-native frontend: plain server-rendered static app (no WebSocket).

Zoho Catalyst AppSail's gateway does not proxy WebSocket upgrades, which is
fatal to Streamlit's connection model (confirmed: every handshake attempt
gets back a plain HTTP 200 instead of 101 Switching Protocols, so the app
never progresses past its loading skeleton on Catalyst). This app instead
serves a static HTML/CSS/JS page where every interaction is a normal
request/response fetch() call — nothing here needs a persistent connection,
so it works within Catalyst's request-based model.

Browser calls hit /api/* on THIS service (same origin as the page) and are
proxied server-side to ksp-api, rather than the browser calling ksp-api
cross-origin directly. Catalyst's AppSail gateway intercepts CORS preflight
(OPTIONS) requests before they reach the app and returns them without an
Access-Control-Allow-Origin header (confirmed empirically), so a direct
cross-origin fetch() from the browser to ksp-api is permanently blocked
regardless of the CORS middleware configured on the backend. Proxying
server-to-server sidesteps this — CORS is a browser-enforced concept and
does not apply to this hop at all.

The Streamlit app (frontend/streamlit_app.py) is unchanged and still used for
local development and the Streamlit Community Cloud deployment.
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
BACKEND_API = os.getenv("FASTAPI_INTERNAL_URL", "http://localhost:8000") + "/api"

app = FastAPI(title="KAVAL AI — Catalyst frontend")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    html = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
    return html.replace("__API_URL__", "/api")


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def api_proxy(path: str, request: Request):
    headers = {"Content-Type": request.headers.get("content-type", "application/json")}
    role = request.headers.get("x-user-role")
    if role:
        headers["X-User-Role"] = role
    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.request(
            request.method,
            f"{BACKEND_API}/{path}",
            params=request.query_params,
            content=body or None,
            headers=headers,
        )
    response_headers = {}
    if "content-disposition" in upstream.headers:
        response_headers["Content-Disposition"] = upstream.headers["content-disposition"]
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
        headers=response_headers,
    )


@app.get("/healthz")
def health():
    return {"status": "ok"}
