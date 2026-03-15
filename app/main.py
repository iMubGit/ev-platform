from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.interfaces.api.routes import chargers, sessions, telemetry
from app.domain.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
)

app = FastAPI(title="EV Platform API")

# Global exception handlers
@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleViolationError)
async def business_rule_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# Routers
app.include_router(chargers.router)
app.include_router(sessions.router)
app.include_router(telemetry.router)


@app.get("/health")
async def health():
    return {"status": "ok"}