import os

from dotenv import load_dotenv
from fastapi import FastAPI

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


@app.on_event("startup")
def on_startup():
    init_constraints()


@app.on_event("shutdown")
def on_shutdown():
    close_driver()
