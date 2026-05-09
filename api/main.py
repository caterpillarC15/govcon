from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import close_db, init_db
from api.redis import close_redis
from api.routes import action_packages, agent_runs, company_profiles, healthz, opportunities


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()
    await close_redis()


app = FastAPI(title="GovCapture API", version="0.1.0", lifespan=lifespan)

# CORS: Dev 2's frontend on Vite/Next dev + Vercel prod (PRD §17 Q5: no auth in MVP).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(healthz.router)
app.include_router(company_profiles.router)
app.include_router(agent_runs.router)
app.include_router(opportunities.router)
app.include_router(action_packages.router)
