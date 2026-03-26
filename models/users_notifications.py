from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from configs.database import Base


class UsersNotifications(Base):
    __tablename__ = "users_notification"
    id                    = Column(Integer, primary_key=True, index=True)
    m_company_master_id   = Column(Integer, nullable=True)
    m_branch_id           = Column(Integer, nullable=True)
    code                  = Column(String(255), nullable=True)
    name                  = Column(String(500), nullable=True)
    description           = Column(String(500), nullable=True)
    status                = Column(String(20),  nullable=True, default="active")
    status_name           = Column(String(100), nullable=True)
    seq                   = Column(Integer, nullable=True)
    created_at            = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_by            = Column(Integer, nullable=True)
    created_by_name       = Column(String(250), nullable=True)
    updated_at            = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by            = Column(Integer, nullable=True)
    updated_by_name       = Column(String(250), nullable=True)
    deleted_at            = Column(DateTime(timezone=True), nullable=True)
    deleted_by            = Column(Integer, nullable=True)
    deleted_by_name       = Column(String(255), nullable=True)
    message_type          = Column(String(255), nullable=True)
    message_title         = Column(String(255), nullable=True)
    message_description   = Column(String(500), nullable=True)
    message_link          = Column(String(500), nullable=True)
    message_json          = Column(Text, nullable=True)
    users_id              = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    read_at               = Column(DateTime(timezone=True), nullable=True)
    message_alert_at      = Column(DateTime(timezone=True), nullable=True)
    message_alert_expired = Column(DateTime(timezone=True), nullable=True)
    users_fullname        = Column(String(500), nullable=True)

    #user = relationship("Users", back_populates="notifications")
