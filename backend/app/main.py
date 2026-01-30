from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import auth, users, groups, sync, visibility, progress

app = FastAPI(title="StudyLink", version="1.0.0", description="Canvas assignment sync for study groups")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(sync.router)
app.include_router(visibility.router)
app.include_router(progress.router)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "app": "StudyLink"}


@app.get("/")
async def serve_index():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"detail": "Frontend not found"}


@app.get("/privacy-policy")
async def serve_privacy_policy():
    policy = FRONTEND_DIR / "privacy-policy.html"
    if policy.exists():
        return FileResponse(str(policy), media_type="text/html")
    return {"detail": "Privacy policy not found"}
