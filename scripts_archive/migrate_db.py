"""Migration script to add columns to projects table."""
import sqlite3
import os

DB_PATH = "./data/person_gift.db"

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add is_strategic
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN is_strategic BOOLEAN DEFAULT 0")
        print("✅ Added column: is_strategic")
    except sqlite3.OperationalError as e:
        print(f"ℹ️ Column is_strategic might already exist: {e}")

    # 2. Add next_milestone
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN next_milestone TEXT")
        print("✅ Added column: next_milestone")
    except sqlite3.OperationalError as e:
        print(f"ℹ️ Column next_milestone might already exist: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
