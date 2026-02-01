import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

class KRABot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        prefix = os.getenv("PREFIX", "!")
        super().__init__(command_prefix=prefix, intents=intents)
        
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

    async def setup_hook(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ 성공적으로 로드됨: {filename}')
                except Exception as e:
                    print(f'❌ 로드 실패 {filename}: {e}')
        
        await self.tree.sync()

    async def on_ready(self):
        user_name = self.user.name if self.user else "알 수 없음"
        print(f'Logged in as {user_name}')
        
        activity = discord.Game(name="크아는 심심해요..")
        await self.change_presence(status=discord.Status.online, activity=activity)
        print("봇의 상태 표시줄 설정이 완료되었습니다.")

    async def on_message(self, message):
        if message.author.bot:
            return
        
        await self.process_commands(message)

bot = KRABot()

token = os.getenv("TOKEN")
if token is None:
    raise RuntimeError("TOKEN 환경 변수가 설정되어 있지 않습니다. .env 파일을 확인해주세요.")

bot.run(token)