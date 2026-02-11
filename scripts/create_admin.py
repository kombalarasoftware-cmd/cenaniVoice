"""Create admin user for production deployment."""
from app.core.database import SessionLocal
from app.models.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

existing = db.query(User).filter(User.email == "admin@speakmaxi.com").first()
if existing:
    print(f"Admin already exists: {existing.email}")
else:
    user = User(
        email="admin@speakmaxi.com",
        full_name="Admin User",
        hashed_password=pwd_context.hash("Speakmaxi2026!"),
        is_active=True,
        role="admin",
    )
    db.add(user)
    db.commit()
    print("Admin user created successfully")

db.close()
