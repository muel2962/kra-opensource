import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import urllib.parse
import os

class MenuRecommendation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        json_path = os.path.join(os.getcwd(), 'data', 'menu.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.menu_list = data['menus']

    @app_commands.command(name="메뉴추천", description="오늘의 식사 메뉴를 추천합니다.")
    async def menu_recommend(self, interaction: discord.Interaction):
        selected_menu = random.choice(self.menu_list)
        
        search_query = selected_menu.replace(" ", "")
        encoded_query = urllib.parse.quote(search_query)
        map_url = f"https://map.naver.com/p/search/{encoded_query}"

        embed = discord.Embed(
            title="🍴추천 메뉴",
            description=f"오늘은 **{selected_menu}** 어때요?",
            color=discord.Color.blue()
        )

        view = discord.ui.View()
        button = discord.ui.Button(
            label=f"주변에 {selected_menu} 맛집 찾기",
            style=discord.ButtonStyle.gray,
            url=map_url
        )
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(MenuRecommendation(bot))