import sys
import os
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

def migrate():
    url = settings.database_url
    # Ensure absolute path for sqlite if relative
    if url.startswith("sqlite:///./"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = url.replace("sqlite:///./", "")
        # Construct absolute path
        abs_db_path = os.path.join(base_dir, db_path)
        url = f"sqlite:///{abs_db_path}"
        
    print(f"Connecting to database: {url}")
    engine = create_engine(url)
    
    with engine.connect() as conn:
        try:
            print("Adding default_start_time...")
            conn.execute(text("ALTER TABLE habit_templates ADD COLUMN default_start_time VARCHAR(10)"))
        except Exception as e:
            print(f"Skipping default_start_time (probably exists): {e}")

        try:
            print("Adding default_end_time...")
            conn.execute(text("ALTER TABLE habit_templates ADD COLUMN default_end_time VARCHAR(10)"))
        except Exception as e:
            print(f"Skipping default_end_time (probably exists): {e}")
            
        conn.commit()
    
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
