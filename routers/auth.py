from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from configs.database import get_db
from models.users import Users
from configs.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterIn(BaseModel):
    name:      str
    user_name: str
    email:     EmailStr
    password:  str


class TokenOut(BaseModel):
    access_token:   str
    remember_token: str
    token_type:     str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="สมัครสมาชิก")
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Users).where(Users.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email หรือ Username นี้ถูกใช้งานแล้ว")

    user = Users(
        name=body.name,
        user_name=body.user_name,
        email=body.email,
        password=AuthService.hash_password(body.password),
        status="active",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return {"message": "สมัครสมาชิกสำเร็จ", "user_id": user.id}


@router.post("/login", response_model=TokenOut, summary="เข้าสู่ระบบ")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Users).where(
            Users.user_name == body.username,
            Users.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if not user or not AuthService.verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Username หรือ Password ไม่ถูกต้อง")

    access_token = AuthService.create_access_token(data={"sub": str(user.id)})
    remember_token = await AuthService.save_remember_token(user.id, db)

    return TokenOut(
        access_token=access_token,
        remember_token=remember_token,
        token_type="bearer",
    )