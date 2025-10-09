import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from googleapiclient.discovery import build
from random import choice
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
import logging

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logger = logging.getLogger("pikabot")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch.setFormatter(CustomFormatter())

logger.addHandler(ch)


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
MIN_MESSAGE_DELAY = defaults_values["MIN_MESSAGE_DELAY"]

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='$', intents=intents)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


async def check_msg(channel: discord.TextChannel)-> bool:
    now = datetime.now(timezone.utc)
    five_minutes_ago = now - timedelta(seconds=MIN_MESSAGE_DELAY)

    async for msg in channel.history(limit=100, after=five_minutes_ago):
        if msg.author == bot.user:
            return True
    return False

async def send_video_notification(video_title:str,video_link:str, description:str, thumbnail_url:str, channel_title:str,message:str,channel:discord.TextChannel):
    message_ = await channel.send(message.format(video_title=video_title,video_link=video_link,description=description,channel_title=channel_title,thumbnail_url=thumbnail_url))
    await message_.add_reaction(choice(EMOJIS))
    await message_.add_reaction(choice(EMOJIS))
    emoji = discord.utils.get(channel.guild.emojis, name = choice(MC_EMOJIS))
    if emoji:
        await message_.add_reaction(emoji)

async def new_video_available(channel_info,last_saved_video_id,channel):
    req = youtube.activities().list(
        part="contentDetails",
        channelId=channel_info["youtube_channel_id"],
        maxResults=1
    )
    res = req.execute()
    logger.info("Youtube API Call (activities list) 1pts")
    if not res.get("items"):
        logger.warning(f"Aucune vidéo trouvée pour {channel_info['youtube_channel_id']}")
        return None
    latest_video = res["items"][0]["contentDetails"]["upload"]["videoId"]

    if latest_video == last_saved_video_id: # si la video est différentes de celle enregistrée
        logger.info(f"pas de nouvelle vidéo (id identique) (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")
        return None
    duration, title, link, time_since_upload, description, thumbnail_url, channel_title  = get_video_detail(latest_video, youtube, logger)
    if duration < SHORT_DURATION:# si la video fait plus de SHORT_DURATION, on enregistre l'id et on envoie la notif
        logger.info(f"c'est un short on fait rien (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")
        return None
    if time_since_upload > MAX_VIDEO_DELAY:
        logger.info(f"delay depuis la sortie de la vidéo dépassé (delai: {time_since_upload})")
        return None
    if await check_msg(channel):
        logger.info(f"message déjà envoyer il y a {MIN_MESSAGE_DELAY} secondes")
        return None
    return duration, title, link, time_since_upload, description, thumbnail_url, channel_title, latest_video

async def check_new_video(channel_info:dict, task_id:int):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_info["discord_channel_id"])
    last_saved_video_id = load_last_video_id(channel_info)

    await asyncio.sleep(GLOBAL_CHECK_INTERVAL*task_id)

    while not bot.is_closed():
        try:
            result = await new_video_available(channel_info,last_saved_video_id,channel)
            if result:
                duration, title, link, time_since_upload, description, thumbnail_url, channel_title,latest_video = result
                await send_video_notification(title,link,description,thumbnail_url,channel_title,channel_info["message"],channel)
                save_last_video_id(latest_video,channel_info)
                logger.info(f"nouvelle vidéo on envoi un message et on sauvegarde l'id (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")
                last_saved_video_id = latest_video
        except Exception as e:
            logger.error(f"Erreur pour {channel_info['youtube_channel_id']}: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

def is_allowed(interaction: discord.Interaction):
    return interaction.user.id in ALLOWED_IDS

@bot.tree.command(
    name="send_message",
    description="Commande accessible uniquement dans un serveur spécifique",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.check(is_allowed)
async def send_message(interaction:discord.Interaction, message:str,channel:discord.TextChannel):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        if interaction.user.id not in ALLOWED_IDS:
            logger.warning(f"L'utilisateur {interaction.user.id} a essayé d'utiliser la commande send_message (pas les perms)")
            await interaction.edit_original_response(content=":x: pas les perms")
            return
        await channel.send(message)
        logger.info(f"L'utilisateur {interaction.user.id} a utilisé la commande send_message : {message}")
        await interaction.edit_original_response(content=":white_check_mark: c'est bon")
    except Exception as e:
        logger.error(f"Erreur pour de send_message de l'utilisateur {interaction.user.id}: {e}")
        await interaction.edit_original_response(content=":warning: Une erreur interne est survenu (check logs)")

youtube_choices = [app_commands.Choice(name=name, value=name) for name in channels_data.keys()]
@bot.tree.command(
    name="trigger_last_notif",
    description="Commande accessible uniquement dans un serveur spécifique",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.choices(youtube_channel_id=youtube_choices)
@app_commands.check(is_allowed)
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
            _, title, link, _, description, thumbnail_url, channel_title = get_video_detail(last_id, youtube,logger)
            await send_video_notification(title, link,description,thumbnail_url,channel_title,cfg["message"] ,channel)
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
        logger.info('Synced')

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du bot : {e}")
    logger.info(f"Connecté en tant que {bot.user}")
    for i,ytb_channel in enumerate(channels_data.values()):
        bot.loop.create_task(check_new_video(ytb_channel,i))

if __name__ == "__main__":
    bot.run(TOKEN)