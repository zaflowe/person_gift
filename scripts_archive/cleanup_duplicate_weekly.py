import logging
import sys
import os

# Add parent dir to path to import app modules
sys.path.append(os.getcwd())

from collections import defaultdict
from app.database import SessionLocal
from app.models.task import Task
from app.models.user import User
from app.models.conversation import ConversationSession, PlanningSession
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_duplicates():
    db = SessionLocal()
    try:
        # Find all active/open tasks
        # We focus on recent duplicates.
        tasks = db.query(Task).filter(
            Task.status == "OPEN"
        ).order_by(Task.created_at.asc()).all()

        # Group by title
        title_map = defaultdict(list)
        for t in tasks:
            # We assume duplicates have IDENTICAL titles like "Weight + Photo (W2026-06)"
            title_map[t.title].append(t)
        
        duplicates_found = 0
        
        for title, group in title_map.items():
            if len(group) > 1:
                # We have duplicates. Keep the FIRST one (oldest), Excuse the rest.
                # group is already sorted by created_at asc
                original = group[0]
                duplicates = group[1:]
                
                for dup in duplicates:
                    logger.info(f"Marking duplicate as EXCUSED: {dup.title} (ID: {dup.id})")
                    dup.status = "EXCUSED"
                    # We can use description or a 'reason' field if it existed to store note.
                    # Appending to description for audit.
                    if dup.description:
                        dup.description += "\n[SYSTEM] Marked compliant duplicate (SYSTEM_DEDUP)."
                    else:
                        dup.description = "[SYSTEM] Marked compliant duplicate (SYSTEM_DEDUP)."
                    
                    duplicates_found += 1
        
        if duplicates_found > 0:
            db.commit()
            logger.info(f"Successfully cleaned up {duplicates_found} duplicate tasks.")
        else:
            logger.info("No duplicates found to clean.")
            
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting duplicate cleanup (Mark as EXCUSED)...")
    cleanup_duplicates()
    print("Done.")
