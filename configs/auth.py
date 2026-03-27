from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import secrets

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs.database import get_db, settings
from models.users import Users

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class AuthService:

    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def create_access_token(data: dict, expires_delta: Optional[int] = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode["exp"] = expire
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    async def save_remember_token(user_id: int | str, db: AsyncSession):
        expires_in_days = 30
        expire_at = datetime.utcnow() + timedelta(days=expires_in_days)
        remember_token = secrets.token_urlsafe(64)

        result = await db.execute(select(Users).where(Users.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        user.remember_token = remember_token
        user.effective_date = datetime.utcnow()
        user.expired_date = expire_at

        await db.flush()
        return remember_token

    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
    ):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ไม่ถูกต้อง หรือหมดอายุ",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        result = await db.execute(
            select(Users).where(
                Users.id == int(user_id),
                Users.deleted_at == None,
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise credentials_exception
        return user