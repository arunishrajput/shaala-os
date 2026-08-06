from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, health, people, timetable
from app.ws.routes import router as ws_router

app = FastAPI(title="Shaala OS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(people.router)
app.include_router(timetable.router)
app.include_router(ws_router)
