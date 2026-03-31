import hashlib
import hmac
import base64
import json
import logging

import httpx
import socketio
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db
from models.message_from_api import  ChatRoom, Message

# ================= LOGGER =================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("LINE-API")

# ================= SOCKET.IO =================
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
app = FastAPI()
app.mount("/socket.io", socketio.ASGIApp(sio))

router = APIRouter(prefix="/api/line", tags=["LINE"])

# ================= CONFIG =================
LINE_CHANNEL_SECRET = "9a80fae9519de72bf480ba4e39e652a7"
LINE_CHANNEL_ACCESS_TOKEN = "h642GUSxanjVQD9Hh72Oa+muoPK4ZDrjMPwRs836ap1MzL39ndZJy/jOrGDuOb3Na8sBbp1ZLuHSqpurd/FF7IPocrM2F/Z5XW4n//hDkuGyAuzifa3vl1PlnRMSuAqPv53lDht4M00Ine7BvgIZhgdB04t89/1O/w1cDnyilFU="

FIXED_USER_ID = "U77e6e1be0473ddb1d391238d8ad5c2ff"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PROFILE_URL = "https://api.line.me/v2/bot/profile/{user_id}"

# ================= MODELS =================
class PushTextIn(BaseModel):
    message: str

# ================= AUTH =================
def _auth_headers():
    return {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

# ================= DB =================
async def get_or_create_user(db: AsyncSession):
    result = await db.execute(
        select(LineUser).where(LineUser.line_user_id == FIXED_USER_ID)
    )
    user = result.scalar_one_or_none()

    if user:
        return user

    user = LineUser(
        line_user_id=FIXED_USER_ID,
        display_name="Test User"
    )
    db.add(user)
    await db.flush()
    return user


async def get_or_create_room(db: AsyncSession):
    result = await db.execute(
        select(ChatRoom).where(ChatRoom.chat_room_no == FIXED_USER_ID)
    )
    room = result.scalar_one_or_none()

    if not room:
        room = ChatRoom(chat_room_no=FIXED_USER_ID)
        db.add(room)
        await db.flush()

    return room


async def save_message(db, user, room, text, mtype, direction):
    msg = Message(
        user_id=user.id,
        chat_room_id=room.id,
        message=text,
        message_type=mtype,
        direction=direction,
        platform="line"
    )
    db.add(msg)

# ================= LINE =================
async def _line_push(messages: list):
    payload = {
        "to": FIXED_USER_ID,
        "messages": messages
    }

    logger.debug(f"[PUSH PAYLOAD] {payload}")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            LINE_PUSH_URL,
            headers=_auth_headers(),
            json=payload
        )

    logger.info(f"[LINE PUSH] {res.status_code} {res.text}")

    if res.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=res.text
        )


async def _line_reply(reply_token: str, messages: list):
    payload = {
        "replyToken": reply_token,
        "messages": messages
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            LINE_REPLY_URL,
            headers=_auth_headers(),
            json=payload
        )

    logger.info(f"[LINE REPLY] {res.status_code} {res.text}")

# ================= WEBHOOK =================
@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    json_data = await request.json()

    logger.info(f"[WEBHOOK] {json_data}")

    events = json_data.get("events", [])

    for event in events:
        if event.get("type") != "message":
            continue

        message = event.get("message", {})
        reply_token = event.get("replyToken")

        user = await get_or_create_user(db)
        room = await get_or_create_room(db)

        if message.get("type") == "text":
            text = message.get("text")

            await save_message(db, user, room, text, "text", "inbound")

            await sio.emit("line_message", {
                "message": text,
                "direction": "inbound"
            })

            # ✅ ใช้ reply ได้ (ของจริงเท่านั้น)
            if reply_token:
                await _line_reply(reply_token, [
                    {"type": "text", "text": f"echo: {text}"}
                ])

    await db.commit()
    return {"status": "ok"}

# ================= PUSH =================
@router.post("/push")
async def push(body: PushTextIn, db: AsyncSession = Depends(get_db)):
    user = await get_or_create_user(db)
    room = await get_or_create_room(db)

    await _line_push([
        {"type": "text", "text": body.message}
    ])

    await save_message(db, user, room, body.message, "text", "outbound")
    await db.commit()

    await sio.emit("line_message", {
        "message": body.message,
        "direction": "outbound"
    })

    return {"status": "sent"}

# ================= SOCKET =================
@sio.event
async def connect(sid, environ):
    logger.info(f"[SOCKET CONNECT] {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"[SOCKET DISCONNECT] {sid}")

# ================= ROUTER =================
app.include_router(router)