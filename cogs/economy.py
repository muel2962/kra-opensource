import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import aiohttp
import random
import datetime
from database import DB_NAME, get_user, get_daily_reward_amount
import os

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook_url = os.getenv("WEBHOOK_URL")

    async def send_webhook(self, sender, receiver, amount, tax, server_name):
        if not self.webhook_url: return
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(self.webhook_url, session=session)
            embed = discord.Embed(title="💸 송금 로그", color=discord.Color.orange())
            embed.add_field(name="보낸 사람", value=f"{sender.name} ({sender.id})", inline=True)
            embed.add_field(name="받는 사람", value=f"{receiver.name} ({receiver.id})", inline=True)
            embed.add_field(name="금액", value=f"{amount:,} KC (세금: {tax:,} KC)", inline=False)
            embed.set_footer(text=f"Server: {server_name}")
            await webhook.send(embed=embed)

    @app_commands.command(name="송금", description="다른 유저에게 코인을 송금합니다 (수수료 10%)")
    async def transfer(self, interaction: discord.Interaction, receiver: discord.User, amount: int):
        if amount <= 0:
            return await interaction.response.send_message(embed=discord.Embed(title="⚠️ 오류", description="음수는 송금할 수 없습니다.", color=discord.Color.red()), ephemeral=True)
        
        sender_data = await get_user(interaction.user.id)
        receiver_data = await get_user(receiver.id)

        if not sender_data:
             return await interaction.response.send_message(embed=discord.Embed(title="⚠️ 오류", description="가입 먼저 해주세요 (/가입).", color=discord.Color.red()), ephemeral=True)
        if not receiver_data:
             return await interaction.response.send_message(embed=discord.Embed(title="⚠️ 오류", description="받는 분이 가입되어 있지 않습니다.", color=discord.Color.red()), ephemeral=True)
        
        if sender_data[1] < amount:
             return await interaction.response.send_message(embed=discord.Embed(title="⚠️ 오류", description="잔액이 부족합니다.", color=discord.Color.red()), ephemeral=True)

        tax = int(amount * 0.1)
        final_amount = amount - tax

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET coins = coins - ?, sent = sent + ? WHERE user_id = ?", (amount, amount, interaction.user.id))
            await db.execute("UPDATE users SET coins = coins + ?, received = received + ? WHERE user_id = ?", (final_amount, final_amount, receiver.id))
            await db.commit()

        await self.send_webhook(interaction.user, receiver, amount, tax, interaction.guild.name)
        
        embed = discord.Embed(title="💸 송금 완료", description=f"{receiver.mention}님에게 송금했습니다.", color=discord.Color.green())
        embed.add_field(name="송금액", value=f"{amount:,} KC", inline=True)
        embed.add_field(name="수수료(10%)", value=f"{tax:,} KC", inline=True)
        embed.add_field(name="실제 전달", value=f"{final_amount:,} KC", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="동전돌리기", description="50% 확률로 코인을 배팅합니다.")
    async def coinflip(self, interaction: discord.Interaction, bet: int):
        user_data = await get_user(interaction.user.id)
        if not user_data or user_data[1] < bet:
            return await interaction.response.send_message(embed=discord.Embed(title="⚠️ 잔액 부족", description="코인이 부족하거나 가입하지 않았습니다.", color=discord.Color.red()), ephemeral=True)
        
        level = user_data[2]
        is_success = random.random() < 0.5

        async with aiosqlite.connect(DB_NAME) as db:
            if is_success:
 
                win_base = bet * 2
                bonus = int(win_base * 0.001 * level)
                total_win = win_base + bonus
                profit = total_win - bet 

                await db.execute("UPDATE users SET coins = coins + ?, wins = wins + 1 WHERE user_id = ?", (profit, interaction.user.id))
                
                embed = discord.Embed(title="🎉 성공!", description=f"동전 던지기에 이겼습니다!", color=discord.Color.green())
                embed.add_field(name="획득", value=f"+{profit:,} KC (보너스 {bonus} KC 포함)", inline=False)
            else:
                await db.execute("UPDATE users SET coins = coins - ?, losses = losses + 1 WHERE user_id = ?", (bet, interaction.user.id))
                embed = discord.Embed(title="💀 실패...", description=f"동전 던지기에 졌습니다...", color=discord.Color.red())
                embed.add_field(name="손실", value=f"-{bet:,} KC", inline=False)
            
            await db.commit()
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="출석", description="매일 출석하고 보상을 받습니다.")
    async def daily(self, interaction: discord.Interaction):
        user_data = await get_user(interaction.user.id)
        if not user_data:
             return await interaction.response.send_message(embed=discord.Embed(title="오류", description="가입이 필요합니다.", color=discord.Color.red()), ephemeral=True)

        today_str = datetime.date.today().isoformat()
        
        if user_data[8] == today_str:
             return await interaction.response.send_message(embed=discord.Embed(title="이미 완료", description="오늘은 이미 출석했습니다.", color=discord.Color.red()), ephemeral=True)

        reward = await get_daily_reward_amount()
        
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET coins = coins + ?, last_daily = ? WHERE user_id = ?", (reward, today_str, interaction.user.id))
            await db.commit()
        
        await interaction.response.send_message(embed=discord.Embed(title="📅 출석 완료", description=f"오늘의 출석 보상: **{reward} KC**를 받았습니다!", color=discord.Color.blue()))

    @app_commands.command(name="채광", description="1시간마다 채광하여 코인을 얻습니다.")
    async def mine(self, interaction: discord.Interaction):
        user_data = await get_user(interaction.user.id)
        if not user_data: return await interaction.response.send_message("가입이 필요합니다.", ephemeral=True)

        now = datetime.datetime.now()
        last_mine_str = user_data[9]
        
        if last_mine_str:
            last_mine = datetime.datetime.fromisoformat(last_mine_str)
            diff = now - last_mine
            if diff.total_seconds() < 3600:
                remaining = int((3600 - diff.total_seconds()) // 60)
                return await interaction.response.send_message(embed=discord.Embed(title="⏳ 쿨타임", description=f"{remaining}분 뒤에 다시 채광할 수 있습니다.", color=discord.Color.red()), ephemeral=True)

        reward = 100 + (user_data[2] * 10)
        
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET coins = coins + ?, last_mine = ? WHERE user_id = ?", (reward, now.isoformat(), interaction.user.id))
            await db.commit()
        
        await interaction.response.send_message(embed=discord.Embed(title="⛏️ 채광 성공", description=f"광산에서 **{reward} KC**를 캤습니다!", color=discord.Color.dark_gray()))

async def setup(bot):
    await bot.add_cog(Economy(bot))