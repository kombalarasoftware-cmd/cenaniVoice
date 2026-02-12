from app.core.database import SessionLocal
from app.models.models import Agent
db = SessionLocal()
a = db.query(Agent).filter(Agent.id == 5).first()
if a:
    print(f"provider={a.provider}")
    print(f"model={a.model}")
    print(f"voice={a.voice}")
    print(f"language={a.language}")
    print(f"system_prompt={a.system_prompt[:80] if a.system_prompt else 'None'}")
    print(f"first_message={a.first_message}")
else:
    print("Agent ID 5 not found")
db.close()
