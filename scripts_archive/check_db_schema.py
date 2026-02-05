import sqlite3

def check_schema():
    conn = sqlite3.connect('./data/person_gift.db')
    cursor = conn.cursor()
    
    print("Columns in 'tasks' table:")
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    for col in columns:
        print(f" - {col[1]} ({col[2]})")

    print("\nColumns in 'projects' table:")
    cursor.execute("PRAGMA table_info(projects)")
    columns = cursor.fetchall()
    for col in columns:
        print(f" - {col[1]} ({col[2]})")
        
    conn.close()

if __name__ == "__main__":
    check_schema()
