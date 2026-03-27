from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from configs.database import get_db
from models.test_transaction import TestTransaction

router = APIRouter(prefix="/test_transaction", tags=["TestTransaction"])


class TestTransactionIn(BaseModel):
    test_00: str
    test_01: Optional[str] = None


class TestTransactionOut(BaseModel):
    id: Optional[int] = None
    test_00: Optional[str] = None
    test_01: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[TestTransactionOut])
async def get_all(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestTransaction))
    return result.scalars().all()


@router.post("/create", response_model=TestTransactionOut)
async def create(body: TestTransactionIn, db: AsyncSession = Depends(get_db)):
    t = TestTransaction(
        test_00=body.test_00,
        test_01=body.test_01,
    )
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


@router.put("/update/{id}", response_model=TestTransactionOut)
async def update(id: int, body: TestTransactionIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestTransaction).where(TestTransaction.id == id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="not found")
    t.test_00 = body.test_00
    t.test_01 = body.test_01
    await db.flush()
    await db.refresh(t)
    return t