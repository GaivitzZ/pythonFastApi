from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db
from models.users import Users
from auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterIn(BaseModel):
    name:      str
    user_name: str
    email:     EmailStr
    password:  str


class TokenOut(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="สมัครสมาชิก")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(Users).filter(Users.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email นี้ถูกใช้งานแล้ว")

    users = Users(
        name=body.name,
        user_name=body.user_name,
        email=body.email,
        password=AuthService.hash_password(body.password),
        status="active",
    )
    db.add(users)
    db.commit()
    db.refresh(users)
    return {"message": "สมัครสมาชิกสำเร็จ", "user_id": users.id}


@router.post("/login", response_model=TokenOut, summary="เข้าสู่ระบบ")
def login(body: LoginIn, db: Session = Depends(get_db)):
    users = db.query(Users).filter(
        Users.user_name == body.username,
        Users.deleted_at == None,
    ).first()
    if not users or not AuthService.verify_password(body.password, users.password):
        raise HTTPException(status_code=401, detail="Username หรือ Password ไม่ถูกต้อง")

    token = AuthService.create_access_token(data={"sub": str(users.id)})
    return {"access_token": token}