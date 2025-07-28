from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from config import settings
from api.videos import router as videos_router
from api.search import router as search_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Video Learning Assistant...")
    yield
    print("Shutting down...")

app = FastAPI(
    title="Video Learning Assistant",
    description="AI-powered video learning assistant with scene detection and semantic search",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - FIXED: Remove prefix since it's already defined in the routers
app.include_router(videos_router)
app.include_router(search_router)

@app.get("/", tags=["health"])
async def root():
    return {"message": "Video Learning Assistant API", "version": "1.0.0"}

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )