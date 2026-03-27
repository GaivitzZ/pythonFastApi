from contextlib import asynccontextmanager
from fastapi import FastAPI
from configs.database import engine, Base

import models.users
import models.users_notifications
import models.test_transaction

from routers import auth, users, users_notifications, test_transaction


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="My API",
    description="FastAPI + JWT + CRUD | users & notifications (Async)",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(users_notifications.router)
app.include_router(test_transaction.router)


@app.get("/", tags=["Health"])
async def root():
    return {"message": "API is running 🚀", "docs": "/docs"}