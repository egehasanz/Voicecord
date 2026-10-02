import discord
from discord.ext import commands
import subprocess
import os

# Railway Environment Variables (Ortam Değişkenleri) üzerinden otomatik çeker
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("[-] HATA: BOT_TOKEN ortam değişkeni bulunamadı! Lütfen Railway Variables kısmına ekleyin.")
    exit(1)

ALLOWED_USER_ID = 1507395734163689583

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_sessions = {}
authorized_panel_users = {ALLOWED_USER_ID}

class RoleManageModal(discord.ui.Modal, title="Panel Yetkili Yönetimi"):
    target_id_input = discord.ui.TextInput(
        label="Yetkilendirilecek Kullanıcı ID",
        placeholder="Örn: 123456789012345678",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message("❌ Bu işlemi yapmaya yetkin yok!", ephemeral=True)
            return

        try:
            new_admin_id = int(self.target_id_input.value.strip())
            authorized_panel_users.add(new_admin_id)
            await interaction.response.send_message(f"✅ Başarılı! `<@{new_admin_id}>` ID'li kullanıcı panele yetkili olarak eklendi.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Geçersiz ID girdin, lütfen sadece sayı yaz.", ephemeral=True)

class VoiceConfigModal(discord.ui.Modal, title="Ses Kasma & Rich Presence Paneli"):
    token_input = discord.ui.TextInput(
        label="Discord Self-Bot Token",
        placeholder="Tokenini buraya yapıştır...",
        style=discord.TextStyle.short,
        required=True
    )
    guild_id_input = discord.ui.TextInput(
        label="Sunucu ID (Guild ID)",
        placeholder="Örn: 1357465064499712163",
        style=discord.TextStyle.short,
        required=True
    )
    channel_id_input = discord.ui.TextInput(
        label="Ses Kanalı ID (Voice Channel ID)",
        placeholder="Örn: 1486461566554472579",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        token = self.token_input.value.strip()
        guild_id = self.guild_id_input.value.strip()
        channel_id = self.channel_id_input.value.strip()

        if user_id in active_sessions:
            try:
                active_sessions[user_id].terminate()
            except:
                pass

        script_filename = f"user_bot_{user_id}.py"
        
        script_content = f"""
import asyncio
import json
import time
import requests
import websockets

TOKEN = "{token}"
GUILD_ID = "{guild_id}"
CHANNEL_ID = "{channel_id}"

RPC_DETAILS = "Owner 8jza / kamigawa"
RPC_STATE = "discord.gg/aslanlar"

STATUS = "online"
SELF_MUTE = True
SELF_DEAF = False

API = "https://discord.com/api/v10"

res = requests.get(f"{{API}}/users/@me", headers={{ "Authorization": TOKEN }})
if res.status_code != 200:
    exit()

async def heartbeat(ws, interval):
    while True:
        await asyncio.sleep(interval / 1000)
        try:
            await ws.send(json.dumps({{"op": 1, "d": None}}))
        except:
            break

async def main():
    uri = "wss://gateway.discord.gg/?v=10&encoding=json"
    async with websockets.connect(uri, max_size=10 * 1024 * 1024) as ws:
        hello = json.loads(await ws.recv())
        heartbeat_interval = hello["d"]["heartbeat_interval"]
        asyncio.create_task(heartbeat(ws, heartbeat_interval))

        await ws.send(json.dumps({{
            "op": 2,
            "d": {{
                "token": TOKEN,
                "properties": {{"$os": "windows", "$browser": "chrome", "$device": "pc"}},
                "presence": {{
                    "status": STATUS,
                    "afk": False,
                    "since": int(time.time() * 1000),
                    "activities": [
                        {{
                            "name": "/aslanler Voice System,
                            "type": 0,
                            "details": RPC_DETAILS,
                            "state": RPC_STATE,
                            "timestamps": {{
                                "start": int(time.time())
                            }}
                        }}
                    ]
                }}
            }}
        }}))

        while True:
            event = json.loads(await ws.recv())
            if event.get("t") == "READY":
                break

        await ws.send(json.dumps({{
            "op": 4,
            "d": {{
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "self_mute": SELF_MUTE,
                "self_deaf": SELF_DEAF,
            }}
        }}))

        while True:
            try:
                await ws.recv()
            except:
                break

async def run():
    while True:
        try:
            await main()
        except:
            await asyncio.sleep(5)

asyncio.run(run())
"""

        with open(script_filename, "w", encoding="utf-8") as f:
            f.write(script_content)

        process = subprocess.Popen(["python", script_filename])
        active_sessions[user_id] = process

        await interaction.response.send_message(
            "✅ **Başarılı!** Self-botun arka planda çalıştırıldı, ses kanalına bağlandı ve Rich Presence profiline uygulandı!",
            ephemeral=True
        )

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ses & RP Paneli Aç", style=discord.ButtonStyle.green, custom_id="open_voice_panel")
    async def open_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VoiceConfigModal())

    @discord.ui.button(label="Botumu Kapat / Durdur", style=discord.ButtonStyle.red, custom_id="stop_voice_bot")
    async def stop_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if user_id in active_sessions:
            try:
                active_sessions[user_id].terminate()
                del active_sessions[user_id]
                await interaction.response.send_message("🛑 Çalışan ses ve RP botun durduruldu.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Hata oluştu: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aktif çalışan bir botun bulunmuyor.", ephemeral=True)

    @discord.ui.button(label="⚙️ Yetkili Ata", style=discord.ButtonStyle.blurple, custom_id="assign_admin_panel")
    async def assign_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in authorized_panel_users:
            await interaction.response.send_message("❌ Bu paneli yönetmek için yetkin yok!", ephemeral=True)
            return
        await interaction.response.send_modal(RoleManageModal())

@bot.event
async def on_ready():
    print(f"Panel Botu Aktif: {bot.user.name}")

@bot.command(name="ses")
async def setup_panel(ctx):
    if ctx.author.id != ALLOWED_USER_ID:
        try:
            await ctx.message.delete()
        except:
            pass
        return

    embed = discord.Embed(
        title="🎙️ Ses Kasma & Rich Presence Paneli",
        description="Aşağıdaki butona tıklayarak **Self-Token**, **Sunucu ID** ve **Ses Kanalı ID** bilgilerini gir; botun hem sese bağlansın hem de profilinde **Owner 8jza / kamigawa** görünümü aktif olsun!",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="discord.gg/aslanlar • Güvenli Altyapı")
    
    await ctx.send(embed=embed, view=PanelView())
    try:
        await ctx.message.delete()
    except:
        pass

bot.run(BOT_TOKEN)
