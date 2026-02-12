from app.core.database import SessionLocal
from app.models.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

# List users
users = db.query(User).all()
print("=== Current Users ===")
for u in users:
    print(f"  id={u.id} email={u.email} role={u.role} active={u.is_active} verified={u.is_verified} approved={u.is_approved}")

# Reset admin password
admin = db.query(User).filter(User.email == "admin@speakmaxi.com").first()
if admin:
    admin.hashed_password = pwd_context.hash("Speakmaxi2026!")
    admin.is_active = True
    admin.is_verified = True
    admin.is_approved = True
    db.commit()
    print("\nAdmin password reset successfully!")
else:
    print("\nAdmin user not found!")

db.close()
