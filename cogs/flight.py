import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
import json
from datetime import datetime

class FlightStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service_key = os.getenv("DATA_GO_KR_KEY")
        self.api_url = "https://api.odcloud.kr/api/FlightStatusListDTL/v1/getFlightStatusListDetail"
        self.json_path = "data/flight.json"
        self.airport_codes = self.load_airport_codes()

    def load_airport_codes(self):
        try:
            if not os.path.exists(self.json_path):
                return {}
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ JSON 로드 에러: {e}")
            return {}

    async def airport_autocomplete(self, interaction: discord.Interaction, current: str):
        self.airport_codes = self.load_airport_codes()
        return [
            app_commands.Choice(name=airport, value=airport)
            for airport in self.airport_codes.keys()
            if current.lower() in airport.lower()
        ][:25]

    async def get_flight_data(self, airport_name, mode):
        sch_line = self.airport_codes.get(airport_name)
        
        if not sch_line:
            return None, f"'{airport_name}'은(는) 지원하지 않는 공항명입니다."

        params = {
            "serviceKey": self.service_key,
            "page": 1,
            "perPage": 15,
            "schLineType": sch_line,
            "schIOType": "O" if mode == "출발" else "I"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params) as response:
                    if response.status == 200:
                        res_json = await response.json()
                        return res_json, None
                    else:
                        return None, f"API 오류 (코드: {response.status})"
        except Exception as e:
            return None, f"연결 실패: {str(e)}"

    def create_flight_embed(self, data, airport_name, mode):
        embed = discord.Embed(
            title=f"✈️ {airport_name}공항 항공 {mode} 현황",
            color=discord.Color.from_rgb(2, 7, 21),
            timestamp=datetime.now()
        )

        flight_list = data.get("data", [])
        
        if not flight_list:
            embed.description = "현재 검색된 실시간 운항 정보가 없습니다."
            return embed

        header = f"`{'편명':<7} | {'시간':<5} | {'상대공항':<10} | {'상태'}`\n"
        content = ""
        count = 0

        now_time_str = datetime.now().strftime("%H%M")

        for item in flight_list:
            time_key = "STD" if mode == "출발" else "STA"
            raw_time = str(item.get(time_key, "0000"))
            
            if raw_time < now_time_str:
                continue

            f_id = str(item.get("AIR_FLN", "N/A"))
            fmt_time = f"{raw_time[:2]}:{raw_time[2:]}" if len(raw_time) >= 4 else raw_time
            
            apt_key = "ARRIVED_KOR" if mode == "출발" else "BOARDING_KOR"
            target_apt = item.get(apt_key, "알수없음").replace(" ", "") 
            status = item.get("RMK_KOR", "정상") or "정상"

            line = f"`{f_id:<8} | {fmt_time:<5} | {target_apt:<12} | {status}`\n"
            
            content += line
            count += 1
            
            if count >= 10:
                break

        if count == 0:
            embed.description = "오늘 남은 운항 정보가 없습니다."
        else:
            embed.add_field(name=f"현재 이후 예정된 정보 ({count}개)", value=header + content, inline=False)
            
        embed.set_footer(text=f"기준 시각: {datetime.now().strftime('%H:%M')} | 출처: 한국공항공사")
        return embed

    @app_commands.command(name="출발항공", description="실시간 출발 정보를 조회합니다.")
    @app_commands.autocomplete(공항이름=airport_autocomplete) # 자동완성 연결
    async def departure(self, interaction: discord.Interaction, 공항이름: str):
        await interaction.response.defer()
        data, error = await self.get_flight_data(공항이름, "출발")
        if error:
            return await interaction.followup.send(f"❌ {error}")
        await interaction.followup.send(embed=self.create_flight_embed(data, 공항이름, "출발"))

    @app_commands.command(name="도착항공", description="실시간 도착 정보를 조회합니다.")
    @app_commands.autocomplete(공항이름=airport_autocomplete)
    async def arrival(self, interaction: discord.Interaction, 공항이름: str):
        await interaction.response.defer()
        data, error = await self.get_flight_data(공항이름, "도착")
        if error:
            return await interaction.followup.send(f"❌ {error}")
        await interaction.followup.send(embed=self.create_flight_embed(data, 공항이름, "도착"))

async def setup(bot):
    await bot.add_cog(FlightStatus(bot))