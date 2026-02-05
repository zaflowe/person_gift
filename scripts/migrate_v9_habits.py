import sqlite3
import os

DB_PATH = "data/person_gift.db"

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Update users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_habit_generation_date DATETIME")
        print("Added last_habit_generation_date to users.")
    except sqlite3.OperationalError as e:
        print(f"Skipped users update: {e}")

    # 2. Update tasks table
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN template_id VARCHAR")
        print("Added template_id to tasks.")
    except sqlite3.OperationalError as e:
        print(f"Skipped tasks update (template_id): {e}")
        
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN generated_for_date DATETIME")
        print("Added generated_for_date to tasks.")
    except sqlite3.OperationalError as e:
        print(f"Skipped tasks update (generated_for_date): {e}")

    # 3. Create new tables? 
    # SQLAlchemy create_all should handle this, but we can verify tables exist?
    # No, let's let SQLAlchemy handle new tables. We fixed the "existing table missing column" blocking issue.

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
