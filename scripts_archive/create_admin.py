"""Create or reset admin user."""
import logging
from app.database import SessionLocal
from app.models.user import User
from app.models.task import Task, PlanTemplate
from app.models.planning import PlanningSession
from app.models.conversation import ConversationSession
from app.services.auth_service import get_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin():
    db = SessionLocal()
    try:
        username = "admin"
        password = "admin123"
        email = "admin@example.com"
        
        # Check if exists
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            logger.info(f"User {username} exists. Updating password...")
            # CORRECT FIELD: password_hash
            user.password_hash = get_password_hash(password)
        else:
            logger.info(f"Creating user {username}...")
            user = User(
                id="41096ac5-bf9d-4005-9641-96fe5069c60e",
                username=username,
                email=email,
                # CORRECT FIELD: password_hash
                password_hash=get_password_hash(password)
            )
            db.add(user)
            
        db.commit()
        logger.info(f"✅ User '{username}' ready with password '{password}'")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
