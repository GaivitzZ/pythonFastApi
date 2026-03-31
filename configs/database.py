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

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=True,  # ← เปิด True เพื่อดู SQL query ใน terminal
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


# ✅ สร้าง Table อัตโนมัติตอน startup
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables ready")


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
            print("✅ COMMITTED")
        except Exception as e:
            print("🚨 ERROR:", str(e))
            await db.rollback()
            raise
        finally:
            await db.close()