from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://pylab01:P%40ssw0rd%401@10.0.20.34:5432/python_labdb"
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CHANNEL_LINE_ACCESS_TOKEN: str = 'HPa3arT8FOe8gZGeQ9ih73lRXw/OUxV35E3XWOVulGkTHnoH50oCZKNffqyMGKsJ//eim3OicEScuLJdveZtXcDzYLteh/hhta2tukNEDzrZOALCX9uLX/rbHVNp25SzkRd84U/LWSBPmPOepoVGPgdB04t89/1O/w1cDnyilFU='
    CHANNEL_LINE_SECRET: str = 'e724521304c09c3e1b4dadfd9a88ae2b'

    class Config:
        env_file = ".env"


settings = Settings()

# ✅ 1. ASYNC DATABASE ENGINE
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,          # จำนวน connection หลัก
    max_overflow=20,       # connection ที่เพิ่มได้ชั่วคราว
    pool_timeout=30,       # รอ connection (วินาที)
    pool_recycle=1800,     # reset connection ทุก 30 นาที
    pool_pre_ping=True,    # เช็ค connection ก่อนใช้ (กัน connection ตาย)
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# ✅ 2. ASYNC TRANSACTION MANAGEMENT
async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            print("⏳ Waiting for transaction...")
            yield db
            print("💾 Trying COMMIT...")
            await db.commit()
            print("✅ COMMITTED")
        except Exception as e:
            print("🚨 ERROR OCCURRED:", str(e))
            print("↩️ Rolling back...")
            await db.rollback()
            raise
        finally:
            print("🔚 Closing DB session")
            await db.close()