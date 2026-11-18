from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.interfaces.api.routes import (
    auth,
    chargers,
    sessions,
    staging_diagnostics,
    telemetry,
)
from app.domain.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
)

app = FastAPI(
    title="EV Platform API",
    description="Prototype API for EV charger and charging-session management.",
    version="0.1.0",
)


# Keep FastAPI's standard 422 response shape without calling Starlette's
# deprecated HTTP_422_UNPROCESSABLE_ENTITY alias.
@app.exception_handler(RequestValidationError)
async def request_validation_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


# Global exception handlers
@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleViolationError)
async def business_rule_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# Routers
app.include_router(auth.router)
app.include_router(chargers.router)
app.include_router(sessions.router)
app.include_router(telemetry.router)
app.include_router(staging_diagnostics.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
