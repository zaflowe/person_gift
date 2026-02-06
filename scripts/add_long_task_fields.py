import sqlite3
import os

db_path = os.path.join("data", "person_gift.db")
print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in cursor.fetchall()]

    if "long_task_template_id" not in columns:
        print("Adding 'long_task_template_id' column to tasks...")
        cursor.execute("ALTER TABLE tasks ADD COLUMN long_task_template_id VARCHAR")
        conn.commit()
        print("Added 'long_task_template_id' column.")
    else:
        print("'long_task_template_id' column already exists.")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
