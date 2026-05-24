import asyncio
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.notifications import router as notifications_router
from api.override import router as override_router
from api.ws import router as ws_router
from api.rooms import router as rooms_router
from api.schedules import router as schedules_router
from api.sensors import router as sensors_router
from api.holidays import router as holidays_router
from api.bookings import router as bookings_router
from core.config import settings
from core.sqlite import init_db
from mqtt.subscriber import start_subscriber

db_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool

    await init_db()

    db_pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    app.state.db_pool = db_pool

    app.state.mqtt_client = None

    subscriber_task = asyncio.create_task(
        start_subscriber(settings.mqtt_host, settings.mqtt_port, app)
    )

    yield

    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass

    if db_pool:
        await db_pool.close()


app = FastAPI(
    title="Intelligent Smart Classroom System",
    description="Real-Time Energy Monitoring and Environmental Safety",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors_router)
app.include_router(rooms_router)
app.include_router(schedules_router)
app.include_router(notifications_router)
app.include_router(override_router)
app.include_router(ws_router)
app.include_router(holidays_router)
app.include_router(bookings_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "mqtt": app.state.mqtt_client is not None,
        "database": db_pool is not None,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
