import discord
import os
import asyncio
from discord.ext import commands, tasks
from dotenv import load_dotenv
from database import init_db

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

GUILD_ID = os.getenv('GUILD_ID')
guild_ids = [discord.Object(id=int(GUILD_ID))] if GUILD_ID else None

bot = commands.Bot(command_prefix="!", intents=intents, tree_cls=discord.app_commands.CommandTree) 
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and filename != "__init__.py":
            await bot.load_extension(f'cogs.{filename[:-3]}')

@tasks.loop(seconds=10.0) 
async def change_presence():
    guild_count = len(bot.guilds)
    member_count = sum(guild.member_count for guild in bot.guilds)

    messages = [
        f"{guild_count}개의 서버와 함께",
        f"{member_count}명의 유저 지원 중"
    ]
    
    current_index = change_presence.current_loop % len(messages)
    current_message = messages[current_index]

    await bot.change_presence(activity=discord.Game(name=current_message))

@bot.event
async def on_ready():
    await init_db()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:

        synced = await bot.tree.sync(guild=guild_ids[0] if guild_ids else None)
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(e)
    
    if not change_presence.is_running():
        change_presence.start()

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv('BOT_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())