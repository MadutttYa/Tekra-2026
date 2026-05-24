import asyncio
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI

from api.notifications import router as notifications_router
from api.override import router as override_router
from api.ws import router as ws_router
from api.rooms import router as rooms_router
from api.schedules import router as schedules_router
from api.sensors import router as sensors_router
from core.config import settings
from core.sqlite import init_db
from mqtt.subscriber import start_subscriber

# -----------------------------------------------------------------------------
# Shared state — holds live connections so the rest of the app can use them
# -----------------------------------------------------------------------------
db_pool: asyncpg.Pool | None = None


# -----------------------------------------------------------------------------
# Lifespan — runs on startup and shutdown
# Everything before "yield" = startup
# Everything after  "yield" = shutdown
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool

    # --- Startup ---
    print("Starting TEKRA backend...")

    # Initialise SQLite (creates tables if they don't exist)
    await init_db()
    print("SQLite ready.")

    # Connect to QuestDB
    print(f"Connecting to QuestDB at {settings.db_host}:{settings.db_port}...")
    db_pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    app.state.db_pool = db_pool   # store so endpoints can access via Depends
    print("QuestDB connected.")

    # Pre-set mqtt_client to None — the subscriber task will populate it once connected
    app.state.mqtt_client = None

    # Launch the subscriber as a background task.
    # It manages its own MQTT connection and reconnects automatically on drops.
    print(f"Starting MQTT subscriber → {settings.mqtt_host}:{settings.mqtt_port}...")
    subscriber_task = asyncio.create_task(
        start_subscriber(settings.mqtt_host, settings.mqtt_port, app)
    )
    print("TEKRA backend ready.")

    yield  # App is running — handle requests here

    # --- Shutdown ---
    # Cancel the subscriber loop cleanly
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass  # Expected — task was cancelled on purpose

    print("Shutting down TEKRA backend...")
    if db_pool:
        await db_pool.close()
    print("Shutdown complete.")


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="TEKRA Backend",
    description="Smart classroom monitoring and control system",
    version="0.1.0",
    lifespan=lifespan,
)


# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------
app.include_router(sensors_router)
app.include_router(rooms_router)
app.include_router(schedules_router)
app.include_router(notifications_router)
app.include_router(override_router)
app.include_router(ws_router)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Check that the backend, MQTT broker, and database are all reachable."""
    return {
        "status": "ok",
        "mqtt": app.state.mqtt_client is not None,
        "database": db_pool is not None,
    }


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,  # Auto-restart when you save a file (dev only)
    )
