from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.db import close_client
from api.redis import close_redis
from api.routes import (
    action_packages,
    agent_runs,
    company_profiles,
    healthz,
    opportunities,
    profiles,
    waitlist,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_client()
    await close_redis()


app = FastAPI(title="GovCapture API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(healthz.router)
app.include_router(waitlist.router)
app.include_router(profiles.router)
app.include_router(company_profiles.router)
app.include_router(agent_runs.router)
app.include_router(opportunities.router)
app.include_router(action_packages.router)
