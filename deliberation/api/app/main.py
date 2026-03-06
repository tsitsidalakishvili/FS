import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(
    dotenv_path=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    ),
    override=True,
)

from .db import close_driver, init_constraints
from .routes import router

app = FastAPI(title="Polis-style Deliberation API")
app.include_router(router)

APP_DIR = Path(__file__).resolve().parent
PARTICIPATE_STATIC_DIR = APP_DIR / "static" / "participate"
app.mount(
    "/participate/assets",
    StaticFiles(directory=str(PARTICIPATE_STATIC_DIR)),
    name="participate-assets",
)


@app.get("/")
def root():
    return {
        "service": "fs-deliberation-api",
        "status": "ok",
        "docs": "/docs",
        "health": "/healthz",
        "participate": "/participate",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/participate")
def participate():
    return FileResponse(PARTICIPATE_STATIC_DIR / "index.html")


@app.get("/participate/manifest.webmanifest")
def participate_manifest():
    return FileResponse(
        PARTICIPATE_STATIC_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@app.get("/participate/sw.js")
def participate_service_worker():
    return FileResponse(
        PARTICIPATE_STATIC_DIR / "sw.js",
        media_type="application/javascript",
    )


@app.on_event("startup")
def on_startup():
    init_constraints()


@app.on_event("shutdown")
def on_shutdown():
    close_driver()
