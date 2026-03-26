from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from configs.database import get_db, settings
from models.users import Users
import secrets

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

    def save_remember_token(user_id: int | str, db: Session):
        expires_in_days = 30
        expire_at = datetime.utcnow() + timedelta(days=expires_in_days)
        remember_token = secrets.token_urlsafe(64)
        user = db.query(Users).filter(Users.id == int(user_id)).first()

        if not user:
            raise ValueError("User not found")

        user.remember_token = remember_token
        user.effective_date = datetime.utcnow()
        user.expired_date = expire_at

        db.commit()
        return remember_token

    def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
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

        user = db.query(Users).filter(
            Users.id == int(user_id),
            Users.deleted_at == None,
        ).first()
        if not user:
            raise credentials_exception
        return user