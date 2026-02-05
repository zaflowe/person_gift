from app.database import SessionLocal, init_db
from app.models.user import User
import bcrypt
import uuid
from datetime import datetime

# Ensure tables exist
init_db()

db = SessionLocal()

# Standard bcrypt hashing without passlib
pwd = b"admin123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(pwd, salt)
hashed_str = hashed.decode('utf-8')

# Check if exists
admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    print("Creating admin user with direct bcrypt...")
    new_admin = User(
        id=str(uuid.uuid4()),
        username="admin",
        password_hash=hashed_str,
        created_at=datetime.utcnow()
    )
    db.add(new_admin)
    db.commit()
    print("Admin user created successfully.")
else:
    print(f"Admin user already exists. Updating password...")
    admin.password_hash = hashed_str
    db.commit()
    print("Admin password reset (direct bcrypt).")

db.close()
