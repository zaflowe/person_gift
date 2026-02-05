"""Quick script to create admin user."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine, Base
from app.models.user import User
import uuid
from datetime import datetime

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

# Check if user exists
existing = db.query(User).filter(User.username == "admin").first()
if existing:
    print(f"✅ 用户 'admin' 已存在 (ID: {existing.id[:8]}...)")
else:
    # Hash password manually
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        id=str(uuid.uuid4()),
        username="admin",
        password_hash=pwd_context.hash("admin123"),
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"✅ 用户创建成功!")
    print(f"   用户名: {user.username}")
    print(f"   密码: admin123")
    print(f"   ID: {user.id[:8]}...")

db.close()
