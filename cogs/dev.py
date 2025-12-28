import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import os
from database import DB_NAME

class EventView(discord.ui.View):
    def __init__(self, amount):
        super().__init__(timeout=None)
        self.amount = amount
        self.claimed = False

    @discord.ui.button(label="🎁 코인 받기", style=discord.ButtonStyle.success, custom_id="claim_event_coin")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            return await interaction.response.send_message("이미 누군가 받아갔습니다! 😭", ephemeral=True)
        
        self.claimed = True
        button.disabled = True
        button.label = "지급 완료"
        button.style = discord.ButtonStyle.secondary
        
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (interaction.user.id,))
            if not await cursor.fetchone():
                 await db.execute("INSERT INTO users (user_id, coins) VALUES (?, 1000)", (interaction.user.id,))
            
            await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (self.amount, interaction.user.id))
            await db.commit()
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=discord.Embed(title="🎉 당첨!", description=f"{interaction.user.mention}님이 **{self.amount} KC**를 획득했습니다!", color=discord.Color.gold()))

class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dev_id = int(os.getenv("DEV_ID"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dev_id:
            await interaction.response.send_message("🚫 권한이 없습니다.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="dev", description="개발자 전용 도구입니다.")
    @app_commands.choices(command_type=[
        app_commands.Choice(name="코인 얻기 (get)", value="get"),
        app_commands.Choice(name="서버 목록 확인 (servers)", value="servers"),
        app_commands.Choice(name="코인 이벤트 시작 (event)", value="event"),
    ])
    async def dev_command(self, interaction: discord.Interaction, command_type: app_commands.Choice[str], amount: int = None):
        
        cmd = command_type.value

        if cmd == "get":
            if amount is None:
                return await interaction.response.send_message("코인 얻기 명령은 `<amount>`를 입력해야 합니다.", ephemeral=True)
                
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, interaction.user.id))
                await db.commit()
            
            await interaction.response.send_message(embed=discord.Embed(title="Dev Tool", description=f"{amount} KC 생성 완료.", color=discord.Color.purple()), ephemeral=True)

        elif cmd == "servers":
            embed = discord.Embed(title="💻 서버 목록", color=discord.Color.purple())
            for guild in self.bot.guilds:
                invite = "링크 없음"
                try:
                    if guild.text_channels:
                        invite = await guild.text_channels[0].create_invite(max_age=300, max_uses=1)
                except:
                    invite = "권한 부족 또는 오류"
                
                embed.add_field(name=guild.name, value=f"ID: {guild.id}\n인원: {guild.member_count}명\n[초대링크]({invite})", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif cmd == "event":
            channel_id = int(os.getenv("EVENT_CHANNEL_ID"))
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                return await interaction.response.send_message("이벤트 채널을 찾을 수 없습니다. `.env`의 `EVENT_CHANNEL_ID`를 확인하세요.", ephemeral=True)

            event_amount = random.randint(500, 1000)
            view = EventView(event_amount)
            
            embed = discord.Embed(title="🎉 깜짝 코인 이벤트!", description="아래 버튼을 가장 먼저 누르는 분께 코인을 드립니다!", color=discord.Color.magenta())
            embed.add_field(name="상금", value=f"**{event_amount} KC**")
            
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"이벤트 채널 {channel.mention}에 이벤트를 시작했습니다.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Dev(bot))