from app.core.database import SessionLocal
from app.models.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

# Reset password for existing admin user
admin = db.query(User).filter(User.email == "cmutlu2006@hotmail.com").first()
if admin:
    admin.hashed_password = pwd_context.hash("Speakmaxi2026!")
    admin.is_active = True
    admin.is_verified = True
    admin.is_approved = True
    db.commit()
    print(f"Password reset for {admin.email} (role={admin.role})")
else:
    print("User not found!")

db.close()
