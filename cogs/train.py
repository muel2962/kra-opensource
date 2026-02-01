import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
import os
from datetime import datetime, timedelta

class Train(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("SEOUL_SUBWAY_KEY")
        try:
            with open('data/train.json', 'r', encoding='utf-8') as f:
                self.subway_data = json.load(f)
        except FileNotFoundError:
            self.subway_data = {}

    async def station_autocomplete(self, interaction: discord.Interaction, current: str):
        line = interaction.namespace.호선
        stations = self.subway_data.get(line, [])
        return [
            app_commands.Choice(name=station, value=station)
            for station in stations if current.lower() in station.lower()
        ][:25]

    @app_commands.command(name="지하철역도착정보", description="지하철 실시간 도착 정보를 확인합니다.")
    @app_commands.describe(호선="조회할 지하철 호선", 역이름="조회할 역 이름")
    @app_commands.choices(호선=[
        app_commands.Choice(name="1호선", value="1호선")
    ])
    @app_commands.autocomplete(역이름=station_autocomplete)
    async def train_arrival(self, interaction: discord.Interaction, 호선: str, 역이름: str):
        await interaction.response.defer()
        
        search_station = 역이름[:-1] if 역이름.endswith("역") else 역이름
        url = f"http://swopenapi.seoul.go.kr/api/subway/{self.api_key}/json/realtimeStationArrival/0/20/{search_station}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return await interaction.followup.send("❌ API 서버 응답 오류가 발생했습니다.")
                
                data = await response.json()
                if "realtimeArrivalList" not in data:
                    return await interaction.followup.send(f"❓ **{역이름}**의 실시간 도착 정보가 없습니다.")

                up_line, down_line = [], []
                now = datetime.now()

                for info in data["realtimeArrivalList"]:
                    if info['subwayId'] == "1001":
                        recptn_dt_str = info.get('recptnDt', now.strftime('%Y-%m-%d %H:%M:%S'))
                        try:
                            recptn_dt = datetime.strptime(recptn_dt_str, '%Y-%m-%d %H:%M:%S')
                            time_diff = (now - recptn_dt).total_seconds() 
                        except:
                            time_diff = 0

                        remain_sec = int(info.get('barvlDt', 0)) - int(time_diff)
                        remain_sec = max(0, remain_sec)
                        m, s = divmod(remain_sec, 60)
                        time_info = f"({m}분 {s}초 남음)" if remain_sec > 0 else ""
                        
                        msg = f"**{info['trainLineNm']}**\n└ {info['arvlMsg2']} {time_info}"
                        
                        if "상행" in info['updnLine'] or "내선" in info['updnLine']:
                            up_line.append(msg)
                        else:
                            down_line.append(msg)

                embed = discord.Embed(
                    title=f"🚉 {역이름} 실시간 도착 정보",
                    description=f"조회 시각: {now.strftime('%H:%M:%S')}",
                    color=discord.Color.blue(),
                    timestamp=now
                )
                embed.add_field(name="▲ 상행 (의정부/소요산 방면)", value="\n".join(up_line[:3]) if up_line else "정보 없음", inline=True)
                embed.add_field(name="▼ 하행 (인천/서동탄/신창 방면)", value="\n".join(down_line[:3]) if down_line else "정보 없음", inline=True)
                await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Train(bot))