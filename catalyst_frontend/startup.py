"""AppSail entrypoint: launches uvicorn on the port Catalyst injects at runtime."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
