import sqlite3
import os

db_path = os.path.join("data", "person_gift.db")
print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check columns
    cursor.execute("PRAGMA table_info(projects)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    if 'color' not in columns:
        print("Adding 'color' column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN color VARCHAR")
        conn.commit()
        print("Added 'color' column.")
    else:
        print("'color' column already exists.")

    if 'is_strategic' not in columns:
         print("Adding 'is_strategic' column...")
         cursor.execute("ALTER TABLE projects ADD COLUMN is_strategic BOOLEAN DEFAULT 0")
         conn.commit()
         print("Added 'is_strategic' column.")
    else:
        print("'is_strategic' column already exists.")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
