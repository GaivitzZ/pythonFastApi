from typing import Optional
from datetime import datetime
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from configs.database import get_db
from models.users import Users
from models.users_notifications import UsersNotifications
from configs.auth import AuthService
from sqlalchemy import text

router = APIRouter(prefix="/users_notifications", tags=["UserNotifications"])


class UsersNotificationsOut(BaseModel):
    id:                    int
    users_id:              Optional[int]
    message_type:          Optional[str]
    message_title:         Optional[str]
    message_description:   Optional[str]
    message_link:          Optional[str]
    status:                Optional[str]
    read_at:               Optional[datetime]
    message_alert_at:      Optional[datetime]
    message_alert_expired: Optional[datetime]
    users_fullname:        Optional[str]
    created_at:            datetime

    model_config = {"from_attributes": True}


class UsersNotificationsCreate(BaseModel):
    message_type:          Optional[str]      = "info"
    message_title:         str                = Field(..., min_length=1, max_length=255)
    message_description:   Optional[str]      = None
    message_link:          Optional[str]      = None
    message_json:          Optional[str]      = None
    message_alert_at:      Optional[datetime] = None
    message_alert_expired: Optional[datetime] = None
    users_id:              Optional[int]      = None
    code:                  Optional[str]      = None
    seq:                   Optional[int]      = None


class UsersNotificationsUpdate(BaseModel):
    message_title:         Optional[str]      = None
    message_description:   Optional[str]      = None
    message_link:          Optional[str]      = None
    message_json:          Optional[str]      = None
    message_alert_at:      Optional[datetime] = None
    message_alert_expired: Optional[datetime] = None
    status:                Optional[str]      = None


def generate_notification_code() -> str:
    timestamp   = datetime.now().strftime("%y%m")
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"N{timestamp}-{random_part}"


@router.get("/", response_model=list[UsersNotificationsOut], summary="รายการแจ้งเตือนแบบแบ่งหน้า")
def list_notifications(
    page:      Optional[int] = Query(None, ge=1),
    limit:     Optional[int] = Query(None, ge=1, le=100),
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    query = db.query(UsersNotifications).filter(UsersNotifications.deleted_at == None)
    query = query.order_by(UsersNotifications.id.desc())

    if page is not None and limit is not None:
        query = query.offset((page - 1) * limit).limit(limit)

    return query.all()


@router.get("/{notif_id}", response_model=UsersNotificationsOut, summary="ดึง notification รายการเดียว")
def get_notification(
    notif_id: int,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    notif = db.query(UsersNotifications).filter(
        UsersNotifications.id         == notif_id,
        UsersNotifications.deleted_at == None,
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={notif_id}")

    return notif


@router.post("/", response_model=UsersNotificationsOut, status_code=status.HTTP_201_CREATED, summary="สร้าง notification")
def create_notification(
    body:         UsersNotificationsCreate,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    target_id   = body.users_id or current_user.id
    target_user = current_user if target_id == current_user.id else \
                  db.query(Users).filter(Users.id == target_id).first()

    if not target_user and body.users_id is not None:
        raise HTTPException(status_code=400, detail="ไม่พบผู้ใช้เป้าหมาย (users_id ไม่ถูกต้อง)")

    code = body.code or generate_notification_code()

    notif = UsersNotifications(
        code                  = code,
        m_company_master_id   = None,
        m_branch_id           = None,
        name                  = body.message_title,
        description           = body.message_description or "แจ้งเตือนจากระบบ",
        status                = "active",
        status_name           = "Active",
        seq                   = body.seq,
        users_id              = target_id,
        users_fullname        = target_user.name if target_user else None,
        message_type          = body.message_type,
        message_title         = body.message_title,
        message_description   = body.message_description,
        message_link          = body.message_link,
        message_json          = body.message_json,
        message_alert_at      = body.message_alert_at,
        message_alert_expired = body.message_alert_expired,
        created_at            = datetime.utcnow(),
        created_by            = current_user.id,
        created_by_name       = current_user.name,
        updated_at            = datetime.utcnow(),
    )

    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/{notif_id}", response_model=UsersNotificationsOut, summary="อัปเดต notification แบบเต็ม (PUT)")
def update_notification_full(
    notif_id:     int,
    body:         UsersNotificationsCreate,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    notif = db.query(UsersNotifications).filter(
        UsersNotifications.id         == notif_id,
        UsersNotifications.deleted_at == None,
    ).first()

    if not notif:
        raise HTTPException(404, detail=f"ไม่พบ notification id={notif_id}")

    notif.code                  = body.code or notif.code
    notif.seq                   = body.seq  if body.seq  is not None else notif.seq
    notif.message_type          = body.message_type or notif.message_type
    notif.message_title         = body.message_title
    notif.message_description   = body.message_description
    notif.message_link          = body.message_link
    notif.message_json          = body.message_json
    notif.message_alert_at      = body.message_alert_at
    notif.message_alert_expired = body.message_alert_expired
    notif.status                = "active"
    notif.updated_at            = datetime.utcnow()
    notif.updated_by            = current_user.id
    notif.updated_by_name       = current_user.name

    db.commit()
    db.refresh(notif)
    return notif


@router.patch("/{notif_id}", response_model=UsersNotificationsOut, summary="อัปเดตบางส่วน (PATCH)")
def patch_notification(
    notif_id:     int,
    body:         UsersNotificationsUpdate,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    notif = db.query(UsersNotifications).filter(
        UsersNotifications.id         == notif_id,
        UsersNotifications.deleted_at == None,
    ).first()

    if not notif:
        raise HTTPException(404, detail=f"ไม่พบ notification id={notif_id}")

    updated = False

    if body.message_title       is not None: notif.message_title       = body.message_title;       updated = True
    if body.message_description is not None: notif.message_description = body.message_description; updated = True
    if body.message_link        is not None: notif.message_link        = body.message_link;        updated = True
    if body.message_json        is not None: notif.message_json        = body.message_json;        updated = True
    if body.status              is not None: notif.status              = body.status;              updated = True
    if body.message_alert_at    is not None: notif.message_alert_at    = body.message_alert_at;    updated = True
    if body.message_alert_expired is not None: notif.message_alert_expired = body.message_alert_expired; updated = True

    if updated:
        notif.updated_at      = datetime.utcnow()
        notif.updated_by      = current_user.id
        notif.updated_by_name = current_user.name
        db.commit()
        db.refresh(notif)

    return notif


@router.delete("/{notif_id}", status_code=status.HTTP_200_OK, summary="ลบ notification (hard delete)")
def delete_notification(
    notif_id:     int,
    db:           Session = Depends(get_db),
    current_user: Users   = Depends(AuthService.get_current_user),
):
    notif = db.query(UsersNotifications).filter(
        UsersNotifications.id         == notif_id,
        UsersNotifications.deleted_at == None,
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={notif_id}")

    db.delete(notif)
    db.commit()

    return {"message": f"ลบ notification id={notif_id} สำเร็จ"}
