from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from configs.database import get_db
from models.users import Users
from configs.auth import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


class UsersOut(BaseModel):
    id:          int
    name:        Optional[str]
    user_name:   Optional[str]
    user_phone:  Optional[str]
    email:       Optional[str]
    status:      Optional[str]
    avatar:      Optional[str]
    created_at:  datetime

    #model_config = {"from_attributes": True}


class UsersCreate(BaseModel):
    name:       str
    user_name:  str
    email:      EmailStr
    password:   str
    user_phone: Optional[str] = None
    status:     Optional[str] = "active"


class UsersUpdate(BaseModel):
    name:       Optional[str]      = None
    user_name:  Optional[str]      = None
    user_phone: Optional[str]      = None
    email:      Optional[EmailStr] = None
    password:   Optional[str]      = None
    status:     Optional[str]      = None
    avatar:     Optional[str]      = None


@router.get("/", response_model=list[UsersOut], summary="รายการ users")
def list_users(
    page:      Optional[int] = Query(None, ge=1),
    limit:     Optional[int] = Query(None, ge=1, le=100),
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    query = db.query(Users).filter(Users.deleted_at == None)
    
    query = query.order_by(Users.id.desc())

    if page is not None and limit is not None:
        query = query.offset((page - 1) * limit).limit(limit)

    return query.all()


@router.get("/me", response_model=UsersOut, summary="ข้อมูล user ของตัวเอง")
def get_me(current_user: Users = Depends(AuthService.get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UsersOut, summary="ดู user ตาม ID")
def get_user(
    user_id:      int,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    users = db.query(Users).filter(Users.id == user_id, Users.deleted_at == None).first()
    if not users:
        raise HTTPException(status_code=404, detail=f"ไม่พบ user id={user_id}")
    return users


@router.post("/", response_model=UsersOut, status_code=status.HTTP_201_CREATED, summary="สร้าง user ใหม่")
def create_user(
    body:         UsersCreate,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    if db.query(Users).filter(Users.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email นี้ถูกใช้งานแล้ว")

    users = Users(
        name=body.name,
        user_name=body.user_name,
        email=body.email,
        password=AuthService.hash_password(body.password),
        user_phone=body.user_phone,
        status=body.status,
        created_by=current_user.id,
        created_by_name=current_user.name,
    )
    db.add(users)
    db.commit()
    db.refresh(users)
    return users


@router.put("/{user_id}", response_model=UsersOut, summary="อัปเดต user (PUT)")
def replace_user(
    user_id:      int,
    body:         UsersUpdate,
    db:           Session = Depends(get_db),
    current_user: Users    = Depends(AuthService.get_current_user),
):
    users = db.query(Users).filter(Users.id == user_id, Users.deleted_at == None).first()
    if not users:
        raise HTTPException(status_code=404, detail=f"ไม่พบ user id={user_id}")

    if body.name:       users.name       = body.name
    if body.user_name:  users.user_name  = body.user_name
    if body.user_phone: users.user_phone = body.user_phone
    if body.email:      users.email      = body.email
    if body.password:   users.password   = AuthService.hash_password(body.password)
    if body.status:     users.status     = body.status
    if body.avatar:     users.avatar     = body.avatar

    users.updated_by      = current_user.id
    users.updated_by_name = current_user.name
    db.commit()
    db.refresh(users)
    return users


@router.patch("/{user_id}", response_model=UsersOut, summary="อัปเดตบางฟิลด์ (PATCH)")
def update_user(
    user_id:      int,
    body:         UsersUpdate,
    db:           Session = Depends(get_db),
    current_user: Users    = Depends(AuthService.get_current_user),
):
    return replace_user(user_id, body, db, current_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="ลบ user (hard delete)"
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    user = db.query(Users).filter(Users.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"ไม่พบ user id={user_id}"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="ไม่สามารถลบ user ของตัวเองได้"
        )

    db.delete(user)
    db.commit()

    return {"message": f"ลบ user id={user_id} สำเร็จ"}
