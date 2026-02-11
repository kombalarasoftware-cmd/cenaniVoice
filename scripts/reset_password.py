"""Reset user password to test123"""
import asyncio
import asyncpg
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def main():
    new_hash = pwd.hash("test123")
    conn = await asyncpg.connect(
        host="postgres", port=5432,
        user="postgres", password="postgres",
        database="voiceai"
    )
    await conn.execute(
        "UPDATE users SET hashed_password = $1 WHERE id = 1",
        new_hash
    )
    row = await conn.fetchrow("SELECT hashed_password FROM users WHERE id=1")
    print("Updated hash:", row["hashed_password"])
    print("Verify:", pwd.verify("test123", row["hashed_password"]))
    await conn.close()

asyncio.run(main())
