from fastapi import FastAPI
from configs.database import engine, Base

import models.users
import models.users_notifications

from routers import auth, users, users_notifications

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="My API",
    description="FastAPI + JWT + CRUD | users & notifications",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(users_notifications.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "API is running 🚀", "docs": "/docs"}
