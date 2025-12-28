import aiosqlite
import datetime

DB_NAME = "kra_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                sent INTEGER DEFAULT 0,
                received INTEGER DEFAULT 0,
                last_daily TEXT,
                last_mine TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS system (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def create_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("INSERT INTO users (user_id, coins) VALUES (?, 1000)", (user_id,))
            await db.commit()
            return True
        except:
            return False

async def get_daily_reward_amount():
    today = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT value FROM system WHERE key='last_daily_date'")
        row = await cursor.fetchone()
        
        if not row or row[0] != today:
            await db.execute("INSERT OR REPLACE INTO system (key, value) VALUES ('last_daily_date', ?)", (today,))
            await db.execute("INSERT OR REPLACE INTO system (key, value) VALUES ('daily_count', '0')")
            await db.commit()
            count = 0
        else:
            cursor = await db.execute("SELECT value FROM system WHERE key='daily_count'")
            row = await cursor.fetchone()
            count = int(row[0]) if row else 0

        reward = max(100, 1000 - (count * 10))

        await db.execute("INSERT OR REPLACE INTO system (key, value) VALUES ('daily_count', ?)", (str(count + 1),))
        await db.commit()
        
        return reward