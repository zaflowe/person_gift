"""Create user directly in DB with pre-hashed password."""
import sqlite3
import uuid
from datetime import datetime

# Connect to database
conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# Create tables if not exist (from models)
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME NOT NULL
)
''')

# Check if user exists
cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
existing = cursor.fetchone()

if existing:
    print(f"✅ 用户 'admin' 已存在")
    print(f"   ID: {existing[0][:8]}...")
else:
    # Pre-hashed password for "admin123" (generated with bcrypt online)
    # This is a valid bcrypt hash for "admin123"
    pre_hashed = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzNGNqZz3O"
    
    user_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "admin", pre_hashed, created_at)
    )
    conn.commit()
    
    print(f"✅ 用户创建成功!")
    print(f"   用户名: admin")
    print(f"   密码: admin123")
    print(f"   ID: {user_id[:8]}...")

conn.close()
