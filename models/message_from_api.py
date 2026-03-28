from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from configs.database import Base


class MessageFromAPI(Base):
    __tablename__ = "message_from_api"

    id                            = Column(Integer, primary_key=True, index=True,autoincrement=True)

    #sender
    user_id                       = Column(Integer,nullable=False)

    platform                      = Column(String(255),nullable=False)
    message_type                  = Column(String(255),nullable=False)
    message                       = Column(String(255),nullable=False)
    log_level                     = Column(String(255),default='info')
    to                            = Column(String(255),nullable=True)
    chat_room_no                  = Column(String(255),nullable=True) #autoGenerateRandomWithoutRepeat
    created_at                    = Column(DateTime(timezone=True),default=datetime.utcnow)
    updated_at                    = Column(DateTime(timezone=True),default=datetime.utcnow,onupdate=datetime.utcnow)
