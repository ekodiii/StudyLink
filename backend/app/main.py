from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health():
    return {"status": "ok", "app": "StudyLink"}
