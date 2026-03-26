from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from configs.database import Base


class TestTransaction(Base):
    __tablename__ = "test_transaction"

    id                            = Column(Integer, primary_key=True, index=True,autoincrement=True)
    test_00                       = Column(String(255), nullable=False)
    test_01                       = Column(String(255), nullable=True)
   

    #notifications = relationship("UsersNotifications", back_populates="user")
    #test_name = Column()