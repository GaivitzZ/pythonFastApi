from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from configs.database import Base


# class LineUser(Base):
#     __tablename__ = "line_users"

#     id = Column(Integer, primary_key=True)
#     line_user_id = Column(String(255), unique=True)
#     display_name = Column(String(255))
#     picture_url = Column(String(512))
#     created_at = Column(DateTime, server_default=func.now())


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True)
    chat_room_no = Column(String(255), unique=True)
    room_type = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("line_users.id"))
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"))

    platform = Column(String(50))
    message_type = Column(String(50))
    message = Column(Text)
    direction = Column(String(20))

    created_at = Column(DateTime, server_default=func.now())