import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from googleapiclient.discovery import build
from random import choice
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

from utils import load_config, save_last_video_id, load_last_video_id, get_video_detail

defaults_values, channels_data = load_config("config.yaml")
GUILD_ID = defaults_values["GUILD_ID"]
GLOBAL_CHECK_INTERVAL = defaults_values["GLOBAL_CHECK_INTERVAL"]
CHECK_INTERVAL = GLOBAL_CHECK_INTERVAL * len(channels_data)
SHORT_DURATION = defaults_values["SHORT_DURATION"]
MAX_VIDEO_DELAY = defaults_values["MAX_VIDEO_DELAY"]
ALLOWED_IDS = defaults_values["ALLOWED_IDS"]
EMOJIS = defaults_values["EMOJIS"]
MC_EMOJIS = defaults_values["MC_EMOJIS"]

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='$', intents=intents)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


async def check_msg(channel: discord.TextChannel)-> bool:
    now = datetime.now(timezone.utc)
    five_minutes_ago = now - timedelta(minutes=5)

    async for msg in channel.history(limit=100, after=five_minutes_ago):
        if msg.author == bot.user:
            return True
    return False

async def send_video_notification(video_title:str,video_link:str,message:str,channel:discord.TextChannel):
    message_ = await channel.send(message.format(video_title=video_title,video_link=video_link))
    await message_.add_reaction(choice(EMOJIS))
    await message_.add_reaction(choice(EMOJIS))
    emoji = discord.utils.get(channel.guild.emojis, name = choice(MC_EMOJIS))
    if emoji:
        await message_.add_reaction(emoji)

async def check_new_video(channel_info:dict):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_info["discord_channel_id"])
    last_saved_video_id = load_last_video_id(channel_info)

    while True:
        try:
            req = youtube.activities().list(
                part="contentDetails",
                channelId=channel_info["youtube_channel_id"],
                maxResults=1
            )
            res = req.execute()
            latest_video = res["items"][0]["contentDetails"]["upload"]["videoId"]

            if latest_video != last_saved_video_id: # si la video est différentes de celle enregistrée
                duration, title, link, time_since_upload = get_video_detail(latest_video, youtube)

                if duration > SHORT_DURATION :
                    if time_since_upload < MAX_VIDEO_DELAY: # si la video fait plus de SHORT_DURATION, on enregistre l'id et on envoie la notif
                        if not await check_msg(channel):
                            await send_video_notification(title,link,channel_info["message"],channel)
                            save_last_video_id(latest_video,channel_info)
                            print(f"nouvelle vidéo on envoi un message et on sauvegarde l'id (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")
                            last_saved_video_id = latest_video
                        else:
                            print(f"message déjà envoyer il y a 5 min")
                    else:
                        print(f"delay depuis la sortie de la vidéo dépassé (delai: {time_since_upload})")
                else:
                    print(f"c'est un short on fait rien (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")
            else:
                print(f"pas de nouvelle vidéo (id identique) (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")


        except Exception as e:
            print(f"Erreur : {e}")

        await asyncio.sleep(CHECK_INTERVAL)

@bot.tree.command(
    name="send_message",
    description="Commande accessible uniquement dans un serveur spécifique",
    guild=discord.Object(id=GUILD_ID)
)
async def send_message(interaction:discord.Interaction, message:str,channel:discord.TextChannel):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        if interaction.user.id not in ALLOWED_IDS:
            await interaction.edit_original_response(content=":x: pas les perms")
            return
        await channel.send(message)
        await interaction.edit_original_response(content=":white_check_mark: c'est bon")
    except Exception as e:
        await interaction.edit_original_response(content=":warning: Une erreur interne est survenu (check logs)")
        raise e 

youtube_choices = [app_commands.Choice(name=name, value=name) for name in channels_data.keys()]
@bot.tree.command(
    name="trigger_last_notif",
    description="Commande accessible uniquement dans un serveur spécifique",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.choices(youtube_channel_id=youtube_choices)
async def trigger_last_notif(interaction:discord.Interaction,youtube_channel_id: app_commands.Choice[str], channel:discord.TextChannel = None):
    await interaction.response.defer(thinking=True, ephemeral=True)
    cfg = channels_data[youtube_channel_id.value]
    try:
        if interaction.user.id not in ALLOWED_IDS:
            await interaction.edit_original_response(content=":x: pas les perms")
            return
        if channel is None:
            channel = bot.get_channel(cfg["discord_channel_id"])
        last_id = load_last_video_id(cfg)
        if last_id:
            _, title, link, _ = get_video_detail(last_id, youtube)
            await send_video_notification(title, link,cfg["message"] ,channel)
            await interaction.edit_original_response(content=":white_check_mark: c'est bon")
        else:
            await interaction.edit_original_response(content=":x: le lien de la dernière vidéo n'est pas valide ")
    except Exception as e:
        await interaction.edit_original_response(content=":warning: Une erreur interne est survenu (check logs)")
        raise e 

@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print('Synced')

    except Exception as e:
        print(e)
    print(f"Connecté en tant que {bot.user}")
    for ytb_channel in channels_data.values():
        bot.loop.create_task(check_new_video(ytb_channel))
        await asyncio.sleep(GLOBAL_CHECK_INTERVAL)

if __name__ == "__main__":
    bot.run(TOKEN)