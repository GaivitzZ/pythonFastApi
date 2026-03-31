from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from configs.socket import sio
from enum import Enum

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, ImageMessage, VideoMessage,
    PushMessageRequest,
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent,
    ImageMessageContent, VideoMessageContent
)
from linebot.v3.exceptions import InvalidSignatureError

import asyncio
import requests
import os
import uuid
import requests
import httpx 

# 🔑 LINE CONFIG
CHANNEL_LINE_ACCESS_TOKEN = "h642GUSxanjVQD9Hh72Oa+muoPK4ZDrjMPwRs836ap1MzL39ndZJy/jOrGDuOb3Na8sBbp1ZLuHSqpurd/FF7IPocrM2F/Z5XW4n//hDkuGyAuzifa3vl1PlnRMSuAqPv53lDht4M00Ine7BvgIZhgdB04t89/1O/w1cDnyilFU="
CHANNEL_LINE_SECRET       = '9a80fae9519de72bf480ba4e39e652a7'

configuration = Configuration(access_token=CHANNEL_LINE_ACCESS_TOKEN)
handler       = WebhookHandler(CHANNEL_LINE_SECRET)
LINE_API_URL = "https://api.line.me/v2/bot"

router = APIRouter(prefix="/test_line_api", tags=["TestLineApi"])

# 📁 upload folder
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)



class MessageType(str, Enum):
    text  = "text"
    image = "image"
    video = "video"



class SendRequest(BaseModel):
    user_id:   str
    type:      MessageType
    message:   Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None


# ─── SOCKET ───────────────────────────
@sio.event
async def join(sid, data):
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, user_id)
        await sio.emit("joined", {"room": user_id}, to=sid)
        print(f"✅ {sid} joined room: {user_id}")


@sio.event
async def disconnect(sid):
    print(f"❌ disconnected: {sid}")


# ─── DOWNLOAD FILE FROM LINE ───────────
def download_line_content(message_id: str, ext="jpg"):
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {CHANNEL_LINE_ACCESS_TOKEN}"}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception("Download failed")

    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(res.content)

    return f"http://localhost:8000/static/uploads/{filename}"


# ─── PUSH HELPER ──────────────────────
def _push(user_id: str, messages: list):
    with ApiClient(configuration) as client:
        api = MessagingApi(client)
        api.push_message(
            PushMessageRequest(to=user_id, messages=messages)
        )


# ─── LINE WEBHOOK ─────────────────────
@router.post("/webhook")
async def webhook(request: Request):
    body = await request.body()

    try:
        handler.handle(
            body.decode("utf-8"),
            request.headers.get("x-line-signature", "")
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return {"status": "ok"}


# ─── TEXT ─────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event):
    user_id = event.source.user_id
    text    = event.message.text

    asyncio.ensure_future(
        sio.emit("line_message", {
            "type":    "text",
            "message": text,
            "user_id": user_id,
        }, room=user_id)
    )

    _push(user_id, [TextMessage(text=f"📩 ได้รับ: {text}")])


# ─── IMAGE ────────────────────────────
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    user_id = event.source.user_id

    try:
        image_url = download_line_content(event.message.id, "jpg")

        asyncio.ensure_future(
            sio.emit("line_message", {
                "type":      "image",
                "image_url": image_url,
                "user_id":   user_id,
            }, room=user_id)
        )

        _push(user_id, [TextMessage(text="📷 รับรูปแล้ว")])

    except Exception as e:
        print(f"handle_image error: {e}")


# ─── VIDEO ────────────────────────────
@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video(event):
    user_id = event.source.user_id

    try:
        video_url = download_line_content(event.message.id, "mp4")

        asyncio.ensure_future(
            sio.emit("line_message", {
                "type":      "video",
                "video_url": video_url,
                "user_id":   user_id,
            }, room=user_id)
        )

        _push(user_id, [TextMessage(text="🎬 รับวิดีโอแล้ว")])

    except Exception as e:
        print(f"handle_video error: {e}")


# ─── SEND API ─────────────────────────
@router.post("/send")
async def send_line(payload: SendRequest):
    try:
        # ── 1. ส่งเนื้อหาจริงไป LINE ──
        if payload.type == MessageType.text and payload.message:
            _push(payload.user_id, [TextMessage(text=payload.message)])

        elif payload.type == MessageType.image and payload.image_url:
            _push(payload.user_id, [
                ImageMessage(
                    original_content_url=payload.image_url,
                    preview_image_url=payload.image_url
                )
            ])

        elif payload.type == MessageType.video and payload.video_url:
            _push(payload.user_id, [
                VideoMessage(
                    original_content_url=payload.video_url,
                    preview_image_url=payload.image_url or payload.video_url
                )
            ])

        # ── 2. แจ้งเตือน LINE ตาม type ──
        notify_text = {
            MessageType.text:  f"🔔 มีข้อความใหม่: {payload.message}",
            MessageType.image: "🔔 มีรูปภาพใหม่ส่งมาให้คุณ",
            MessageType.video: "🔔 มีวิดีโอใหม่ส่งมาให้คุณ",
        }

        _push(payload.user_id, [
            TextMessage(text=notify_text[payload.type])
        ])

        # ── 3. emit Socket.IO ──
        await sio.emit("line_message", payload.dict(), room=payload.user_id)

        return {"status": "success", "to": payload.user_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_all_followers")
async def get_all_followers():
    all_user_ids = []
    next_token = None
    
    # Use a single client for all requests
    async with httpx.AsyncClient() as client:
        while True:
            params = {"limit": 1000}
            if next_token:
                params["start"] = next_token

            res = await client.get(
                f"{LINE_API_URL}/followers/ids",
                headers={"Authorization": f"Bearer {CHANNEL_LINE_ACCESS_TOKEN}"},
                params=params
            )

            if res.status_code != 200:
                # Log the actual response to see why it's 403
                print(f"Error Response: {res.text}") 
                return {"error": "API Access Denied", "detail": res.json()}

            data = res.json()
            all_user_ids.extend(data.get("userIds", []))
            next_token = data.get("next")

            if not next_token:
                break

    return {"total": len(all_user_ids), "userIds": all_user_ids}