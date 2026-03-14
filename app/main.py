from fastapi import FastAPI
from app.interfaces.api.routes import chargers, sessions, telemetry

app = FastAPI(title="EV Platform API")

app.include_router(chargers.router)
app.include_router(sessions.router)
app.include_router(telemetry.router)


@app.get("/health")
async def health():
    return {"status": "ok"}