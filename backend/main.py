from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router as api_router

app = FastAPI(title="One Lot AI API")

# CORS configuration
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to One Lot AI API"}
