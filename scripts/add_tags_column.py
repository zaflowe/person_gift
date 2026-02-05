
import sqlite3
import os

DB_PATH = "data/person_gift.db"  # As seen in config.py

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Skipping migration: Database not found at {DB_PATH}. It might be created on first run.")
        return

    print(f"Migrating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "tags" in columns:
            print("✅ Column 'tags' already exists in 'tasks'.")
        else:
            print("➕ Adding 'tags' column to 'tasks' table...")
            # Add column as TEXT (for JSON string), default empty JSON array
            cursor.execute("ALTER TABLE tasks ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
            conn.commit()
            print("✅ Migration successful.")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
