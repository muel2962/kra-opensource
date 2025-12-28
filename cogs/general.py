import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DB_NAME, get_user, create_user
import os

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_embed(self, title, description, color=discord.Color.blue()):
        embed = discord.Embed(title=title, description=description, color=color)
        return embed

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        xp_gain = len(message.content.encode('utf-8')) // 10
        if xp_gain == 0: return

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT level, xp FROM users WHERE user_id = ?", (message.author.id,))
            row = await cursor.fetchone()
            
            if row:
                cur_lvl, cur_xp = row
                new_xp = cur_xp + xp_gain
                
                req_xp = cur_lvl * 100
                
                if new_xp >= req_xp:
                    new_lvl = cur_lvl + 1
                    new_xp = new_xp - req_xp
                    await message.channel.send(embed=self.create_embed("🎉 레벨업!", f"{message.author.mention}님이 Lv.{new_lvl}이 되었습니다!", discord.Color.gold()))
                    await db.execute("UPDATE users SET level = ?, xp = ? WHERE user_id = ?", (new_lvl, new_xp, message.author.id))
                else:
                    await db.execute("UPDATE users SET xp = ? WHERE user_id = ?", (new_xp, message.author.id))
                await db.commit()

    @app_commands.command(name="가입", description="1000 KC를 받고 서비스에 가입합니다.")
    async def register(self, interaction: discord.Interaction):
        if await create_user(interaction.user.id):
            await interaction.response.send_message(embed=self.create_embed("✅ 가입 완료", "가입을 환영합니다! **1000 KC**가 지급되었습니다."))
        else:
            await interaction.response.send_message(embed=self.create_embed("⚠️ 오류", "이미 가입되어 있습니다.", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="프로필", description="유저의 정보를 확인합니다.")
    async def profile(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        data = await get_user(target.id)

        if not data:
            await interaction.response.send_message(embed=self.create_embed("⚠️ 오류", "가입되지 않은 유저입니다.", discord.Color.red()), ephemeral=True)
            return

        coins, lvl, xp, wins, losses, sent, received = data[1], data[2], data[3], data[4], data[5], data[6], data[7]
        
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        req_xp = lvl * 100

        embed = discord.Embed(title=f"👤 {target.name}님의 프로필", color=discord.Color.green())
        embed.add_field(name="💰 보유 자산", value=f"{coins:,} KC", inline=True)
        embed.add_field(name="📊 레벨 / XP", value=f"Lv.{lvl} ({xp}/{req_xp})", inline=True)
        embed.add_field(name="🎮 전적", value=f"{wins}승 {losses}패 (승률: {win_rate:.1f}%)", inline=False)
        embed.add_field(name="💸 송금 통계", value=f"보냄: {sent:,} KC\n받음: {received:,} KC", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="순위", description="레벨 또는 코인 순위를 확인합니다.")
    @app_commands.choices(category=[
        app_commands.Choice(name="코인", value="coins"),
        app_commands.Choice(name="레벨", value="level")
    ])
    async def rank(self, interaction: discord.Interaction, category: app_commands.Choice[str], limit: int = 10):
        async with aiosqlite.connect(DB_NAME) as db:
            query = f"SELECT user_id, {category.value} FROM users ORDER BY {category.value} DESC LIMIT ?"
            cursor = await db.execute(query, (limit,))
            rows = await cursor.fetchall()

        embed = discord.Embed(title=f"🏆 {category.name} 순위 TOP {limit}", color=discord.Color.gold())
        desc = ""
        for idx, row in enumerate(rows, 1):
            user = self.bot.get_user(row[0])
            name = user.name if user else "알 수 없는 유저"
            val = row[1]
            unit = "KC" if category.value == "coins" else "Lv"
            desc += f"**{idx}위.** {name} - `{val} {unit}`\n"
        
        embed.description = desc
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="도움", description="봇의 명령어와 지원 서버 정보를 확인합니다.")
    async def help_cmd(self, interaction: discord.Interaction):
        support_url = os.getenv("SUPPORT_SERVER_URL")
        embed = discord.Embed(title="🤖 KRA 봇 도움말", description="KRA 봇의 명령어 목록입니다.", color=discord.Color.blue())
        embed.add_field(name="기본", value="/가입, /프로필, /도움, /순위", inline=False)
        embed.add_field(name="경제", value="/송금, /출석, /채광, /동전돌리기", inline=False)
        embed.add_field(name="📞 지원 서버", value=f"[여기에서 참여하세요]({support_url})", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))