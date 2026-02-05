import sqlite3
import os

db_path = './data/person_gift.db'
print(f"Checking DB at: {os.path.abspath(db_path)}")

if not os.path.exists(db_path):
    print("❌ Database file not found!")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\nColumns in 'tasks' table:")
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    found_cols = []
    for col in columns:
        # cid, name, type, notnull, dflt_value, pk
        print(f"  - {col[1]} ({col[2]})")
        found_cols.append(col[1])
    
    expected = ['scheduled_date', 'scheduled_time', 'duration', 'is_time_blocked']
    missing = [c for c in expected if c not in found_cols]
    
    if missing:
        print(f"\n❌ MISSING COLUMNS: {missing}")
    else:
        print("\n✅ All time blocking columns found.")
        
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
