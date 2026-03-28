import socketio


class SocketManager:
    def __init__(self):
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*"
        )

    # ==========================
    # event register
    # ==========================
    def register_events(self):

        @self.sio.event
        async def connect(sid, environ):
            print("✅ connected:", sid)

        @self.sio.event
        async def disconnect(sid):
            print("❌ disconnected:", sid)

        @self.sio.event
        async def join(sid, data):
            user_id = data.get("user_id")
            if user_id:
                await self.sio.enter_room(sid, user_id)
                print(f"🔗 {sid} join room {user_id}")

    # ==========================
    # helper methods
    # ==========================
    async def emit_all(self, event: str, data: dict):
        await self.sio.emit(event, data)

    async def emit_to_user(self, user_id: str, event: str, data: dict):
        await self.sio.emit(event, data, room=user_id)


# ✅ สร้าง instance กลาง
socket_manager = SocketManager()
sio = socket_manager.sio