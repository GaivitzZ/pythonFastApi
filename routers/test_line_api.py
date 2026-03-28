from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from configs.socket import sio
from enum import Enum

router = APIRouter(
    prefix="/test_line_api",
    tags=["TestLineApi"]
)

class MessageType(str, Enum):
    text = "text"
    image = "image"
    video = "video"

class BroadcastRequest(BaseModel):
    message: str


class SendRequest(BaseModel):
    user_id: str = 'U77e6e1be0473ddb1d391238d8ad5c2ff'
    type: MessageType
    message: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None


# ✅ ให้ client join room ด้วย user_id ของตัวเอง
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


@router.post("/broadcast")
async def broadcast(payload: BroadcastRequest):
    try:
        await sio.emit("line_message", {"message": payload.message})
        return {"status": "success", "type": "broadcast", "message": payload.message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
async def send_line(payload: SendRequest):
    try:
        data = {
            "type": payload.type,
            "message": payload.message,
            "image_url": payload.image_url,
            "video_url": payload.video_url,
        }
        await sio.emit("line_message", data, room=payload.user_id)
        return {"status": "success", "to": payload.user_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))