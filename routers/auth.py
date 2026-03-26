from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from configs.database import get_db
from models.users import Users
from configs.auth import AuthService   # ตรงนี้ต้อง import ให้ถูก

router = APIRouter(prefix="/auth", tags=["Auth"])


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
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(Users).filter(Users.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email หรือ Username นี้ถูกใช้งานแล้ว")

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
    user = db.query(Users).filter(
        Users.user_name  == body.username,
        Users.deleted_at == None,
    ).first()
    
    if not user or not AuthService.verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Username หรือ Password ไม่ถูกต้อง")

    access_token = AuthService.create_access_token(data={'sub': str(user.id)})
    remember_token = AuthService.save_remember_token(user.id, db)

    return TokenOut(
        access_token   = access_token,
        remember_token = remember_token,
        token_type     = "bearer"
    )