from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import admin, events, payouts, webhooks


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agri Micro-Insurance Engine",
        description="Parametric insurance trigger engine — satellite + sensor data to UPI payout in 24 hours",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501"],   # Streamlit dashboard
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin.router,    prefix="/api/v1/admin",    tags=["admin"])
    app.include_router(events.router,   prefix="/api/v1/events",   tags=["events"])
    app.include_router(payouts.router,  prefix="/api/v1/payouts",  tags=["payouts"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "agri-insurance-engine"}

    return app


app = create_app()
