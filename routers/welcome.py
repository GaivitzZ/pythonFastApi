from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from configs.database import get_db
from models.test_transaction import TestTransaction

router = APIRouter(prefix="/api", tags=[""])

@router.get("/")
async def welcome_function():
    print("hello")
    return {
        "status": 200,
        "message": "welcome api"
    }