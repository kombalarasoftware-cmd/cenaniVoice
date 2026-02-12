from app.core.database import SessionLocal
from app.models.models import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"id={u.id} email={u.email} role={u.role} status={u.status}")
db.close()
