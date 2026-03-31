from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from configs.database import Base


class LineUser(Base):
    __tablename__ = "line_users"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    line_user_id = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    picture_url  = Column(String(512), nullable=True)
    created_at   = Column(DateTime, server_default=func.now())