import sys
import os
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

def migrate():
    url = settings.database_url
    if url.startswith("sqlite:///./"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = url.replace("sqlite:///./", "")
        abs_db_path = os.path.join(base_dir, db_path)
        url = f"sqlite:///{abs_db_path}"
        
    print(f"Connecting to database: {url}")
    engine = create_engine(url)
    
    with engine.connect() as conn:
        try:
            print("Adding color to projects...")
            conn.execute(text("ALTER TABLE projects ADD COLUMN color VARCHAR(50)"))
            conn.commit()
            print("Migration complete.")
        except Exception as e:
            print(f"Migration error (column might exist): {e}")

if __name__ == "__main__":
    migrate()
