from contextlib import asynccontextmanager
from fastapi import FastAPI
import socketio

from configs.database import engine, Base
from configs.socket import socket_manager, sio   # 👈 ใช้ class manager

import models.users
import models.users_notifications
import models.test_transaction

from routers import auth, users, users_notifications, test_transaction, test_line_api


# ==========================
# Lifespan (DB)
# ==========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    print("🛑 Shutting down...")
    await engine.dispose()


# ==========================
# FastAPI App
# ==========================
fastapi_app = FastAPI(
    title="My API",
    description="FastAPI + JWT + CRUD | users & notifications (Async)",
    version="2.0.0",
    lifespan=lifespan,
)


# ==========================
# Register Routers
# ==========================
routers = [
    auth.router,
    users.router,
    users_notifications.router,
    test_transaction.router,
    test_line_api.router
]

for r in routers:
    fastapi_app.include_router(r)


# ==========================
# Register Socket Events
# ==========================
socket_manager.register_events()


# ==========================
# Health Check
# ==========================
@fastapi_app.get("/", tags=["Health"])
async def root():
    return {
        "message": "API is running 🚀",
        "docs": "/docs"
    }


# ==========================
# Combine Socket.IO + FastAPI
# ==========================
app = socketio.ASGIApp(
    sio,
    other_asgi_app=fastapi_app
)