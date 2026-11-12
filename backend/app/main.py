from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.kyc import router as kyc_router
from backend.app.api.ai import router as ai_router

app = FastAPI(
    title="KYC Compliance AI System",
    description="Customer KYC compliance, risk, anomaly detection and AI Copilot",
    version="1.0.0"
)

# Enable frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kyc_router)
app.include_router(ai_router)


@app.get("/")
def home():
    return {
        "message": "KYC Compliance AI System API is running",
        "status": "ONLINE"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}