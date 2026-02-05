"""Authentication service."""
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.dependencies import verify_password, get_password_hash, create_access_token
from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """Register a new user."""
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Create user
        user = User(
            username=user_data.username,
            password_hash=get_password_hash(user_data.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"User {user.username} registered successfully")
        return user
    
    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> str:
        """
        Authenticate user and return JWT token.
        
        Returns JWT token string (V1: stateless, not stored in database).
        """
        # Find user
        user = db.query(User).filter(User.username == login_data.username).first()
        
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=timedelta(hours=settings.jwt_expiration_hours)
        )
        
        logger.info(f"User {user.username} logged in")
        return access_token
