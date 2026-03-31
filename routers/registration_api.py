from fastapi import FastAPI, Depends, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import logging
from datetime import datetime

# นำเข้าส่วน Database ของคุณ
from configs.database import get_db, create_tables
from models.registration_model import LineUser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LINE_REGISTER")

app = FastAPI(title="LINE Registration API")

# สร้าง Table อัตโนมัติ
@app.on_event("startup")
async def startup():
    await create_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api/line", tags=["LINE"])

LINE_CHANNEL_ACCESS_TOKEN = "h642GUSxanjVQD9Hh72Oa+muoPK4ZDrjMPwRs836ap1MzL39ndZJy/jOrGDuOb3Na8sBbp1ZLuHSqpurd/FF7IPocrM2F/Z5XW4n//hDkuGyAuzifa3vl1PlnRMSuAqPv53lDht4M00Ine7BvgIZhgdB04t89/1O/w1cDnyilFU="

class RegisterIn(BaseModel):
    line_user_id: str
    display_name: str
    picture_url: str | None = None

async def push_welcome_message(user_id: str, name: str, is_new: bool):
    text = (
        f"ยินดีต้อนรับคุณ {name} 🎉\nลงทะเบียนเรียบร้อยแล้วค่ะ"
        if is_new else
        f"อัปเดตข้อมูลของคุณ {name} เรียบร้อยแล้วค่ะ 🔄"
    )
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.line.me/v2/bot/message/push", 
                headers=headers, 
                json=payload
            )
            logger.info(f"Push message status: {res.status_code}")
    except Exception as e:
        logger.error(f"Push message failed: {e}")

@router.post("/register")
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    try:
        # ค้นหาผู้ใช้เก่า
        result = await db.execute(
            select(LineUser).where(LineUser.line_user_id == body.line_user_id)
        )
        user = result.scalar_one_or_none()

        is_new = False
        if user is None:
            user = LineUser(
                line_user_id=body.line_user_id,
                display_name=body.display_name,
                picture_url=body.picture_url
            )
            db.add(user)
            is_new = True
            action = "registered"
        else:
            user.display_name = body.display_name
            user.picture_url = body.picture_url
            action = "updated"

        await db.commit()
        await db.refresh(user)

        # ส่งข้อความต้อนรับ
        try:
            await push_welcome_message(body.line_user_id, body.display_name, is_new)
        except Exception as e:
            logger.error(f"Push message error: {e}")

        logger.info(f"User {body.line_user_id} {action} successfully")
        return {"status": "ok", "action": action, "message": "ลงทะเบียนสำเร็จ"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="ไม่สามารถบันทึกข้อมูลได้ กรุณาลองใหม่อีกครั้ง")

