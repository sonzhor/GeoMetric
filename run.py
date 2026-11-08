#!/usr/bin/env python3
"""Entry point for the Geo Intelligence API."""

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("RELOAD", "").lower() in ("1", "true", "yes"),
    )
