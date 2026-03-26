from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from configs.database import Base


class Users(Base):
    __tablename__ = "users"

    id                              = Column(Integer, primary_key=True, index=True)
    name                            = Column(String(255), nullable=True)
    user_name                       = Column(String(255), nullable=True,index=True)
    user_phone                      = Column(String(255), nullable=True)
    email                           = Column(String(350), nullable=True, index=True)
    recovery_email                  = Column(String(255), nullable=True)
    recovery_phone_no               = Column(String(255), nullable=True)
    email_verified_at               = Column(DateTime(timezone=False), nullable=True)
    password                        = Column(String(255), nullable=True)
    expired_date                    = Column(DateTime(timezone=False), nullable=True)
    effective_date                  = Column(DateTime(timezone=False), nullable=True)
    remember_token                  = Column(String(100), nullable=True)
    status                          = Column(String(20), nullable=True, default="active")
    created_at                      = Column(DateTime(timezone=False), default=datetime.utcnow)
    created_by                      = Column(Integer, nullable=True)
    created_by_name                 = Column(String(255), nullable=True)
    updated_at                      = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by                      = Column(Integer, nullable=True)
    updated_by_name                 = Column(String(255), nullable=True)
    deleted_by                      = Column(Integer, nullable=True)
    deleted_by_name                 = Column(String(255), nullable=True)
    deleted_at                      = Column(DateTime(timezone=False), nullable=True)
    avatar                          = Column(String(250), nullable=True)
    m_person_id                     = Column(Integer, nullable=True)
    seq                             = Column(Integer, nullable=True)
    lock_flag                       = Column(String(255), nullable=True)
    next_cycel_change_password_date = Column(DateTime(timezone=True), nullable=True)
    lasted_change_password_date     = Column(DateTime(timezone=True), nullable=True)
    privacy_policies_text           = Column(Text, nullable=True)
    privacy_policies_acknowledge    = Column(DateTime(timezone=True), nullable=True)
    privacy_policies_agree          = Column(String(255), nullable=True)

    #notifications = relationship("UsersNotifications", back_populates="user")
    #test_name = Column()