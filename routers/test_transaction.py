from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from configs.database import get_db
from models.test_transaction import TestTransaction

router = APIRouter(prefix="/test_transaction", tags=["TestTransaction"])


class TestTransactionIn(BaseModel):
    test_00: str
    test_01: Optional[str] = None


class TestTransactionOut(BaseModel):
    id: int
    test_00: str
    test_01: Optional[str] = None

    class Config:
        from_attributes = True  # ✅ ต้องมี ไม่งั้น Pydantic แปลง ORM object ไม่ได้ → 500


@router.get("/", response_model=list[TestTransactionOut])
def get_all(db: Session = Depends(get_db)):
    try:
        db.begin()
        return db.query(TestTransaction).all()  
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=TestTransactionOut)  
def create(body: TestTransactionIn, db: Session = Depends(get_db)):
    try:
        db.begin()
        t = TestTransaction(        
            test_00=body.test_00,
            test_01=body.test_01
        )
        db.add(t)
        db.commit()
        db.refresh(t)               
        return t
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/{id}", response_model=TestTransactionOut)
def update(id: int, body: TestTransactionIn, db: Session = Depends(get_db)): 
    try:
        db.begin()
        t = db.query(TestTransaction).filter(TestTransaction.id == id).first()  
        if not t:                   # ✅ เช็คหลัง query ไม่ใช่ก่อน
            raise HTTPException(status_code=404, detail="not found")
        t.test_00 = body.test_00
        t.test_01 = body.test_01
        db.commit()
        db.refresh(t)
        return t
    except HTTPException:
        raise                       # ✅ ต้อง re-raise ไม่งั้น HTTPException ถูก catch โดย except Exception
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))