import sqlite3
import os

# Database path
DB_PATH = os.path.join("data", "person_gift.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "schedule_policy" not in columns:
            print("Adding 'schedule_policy' column to 'projects' table...")
            # Default to 'LOCKED' as requested
            cursor.execute("ALTER TABLE projects ADD COLUMN schedule_policy TEXT NOT NULL DEFAULT 'LOCKED'")
            conn.commit()
            print("Migration successful.")
        else:
            print("'schedule_policy' column already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
