"""Add time blocking fields to tasks table."""
import sqlite3
import sys

def migrate():
    """Add time blocking fields to existing database."""
    try:
        conn = sqlite3.connect('./data/person_gift.db')
        cursor = conn.cursor()
        
        print("Adding time blocking fields to tasks table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'scheduled_date' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN scheduled_date DATETIME")
            print("✓ Added scheduled_date")
        else:
            print("- scheduled_date already exists")
        
        if 'scheduled_time' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN scheduled_time DATETIME")
            print("✓ Added scheduled_time")
        else:
            print("- scheduled_time already exists")
        
        if 'duration' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN duration INTEGER")
            print("✓ Added duration")
        else:
            print("- duration already exists")
        
        if 'is_time_blocked' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN is_time_blocked BOOLEAN DEFAULT 0 NOT NULL")
            print("✓ Added is_time_blocked")
        else:
            print("- is_time_blocked already exists")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(migrate())
