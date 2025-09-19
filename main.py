import discord
from discord.ext import commands, tasks
import asyncio
from googleapiclient.discovery import build
from isodate import parse_duration  # à installer : pip install isodate
from random import choice
from datetime import datetime, timezone, timedelta

#TOKEN = "MTM2MTgxMDExMzczNTY5MjUyMg.GlR5Je.7-gYi8vsDaKODJQT8TAk3et1uuOJmwwEx_OpTY"
TOKEN = "MTM2OTAxOTg2Nzk2MDcwOTE2MQ.Gpaans.V9Sr3DpoPwJAEVwHVoX9OR3c6k3vuc6zx8Vm0k"
#GUILD_ID = 925320149190459412 # ID du server Discord
GUILD_ID = 1239690915560554608 # ID du server Discord
#CHANNEL_ID = 925329891577196564  # ID du salon Discord
CHANNEL_ID = 1239690916114075671  # ID du salon Discord
YOUTUBE_API_KEY = "AIzaSyBVxlQ2-Y6NoRHVVcuifY98PqNSkpiRgpY" # Clé d'API YouTube
YOUTUBE_CHANNEL_ID = "UC4oqjwA0lPgwd4EH3rk_Www"  # ID de la chaîne YouTube

CHECK_INTERVAL = 300 # 5 minutes

SHORT_DURATION = 180 # 3 minutes

MAX_VIDEO_DELAY = 600 # 10 minutes

EMOJIES = ["🔥","👍","😎","🤣","😝","❤️","🥳","😋","😂","🤯","😳","🫣","🙌","👀"]

MC_EMOJIES = ["Coffre","Creeper","EnderMan","EnderDragon","Fleches","Bee","Gardien","Longuevue","HappyGhast","Perroquet","Piocheendiamant","Poissoncuit","Pomme","Poulet","Pouletrti","Renard","Squelette","Tortue","Warden","Wither","Zombie"]


ALLOWED_ID = [595569462900424707,716306778874314782]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='$', intents=intents)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
# Lecture de l’ID depuis le fichier (ou None si fichier vide/inexistant)
def load_last_video_id():
    try:
        with open("video_id.txt", "r") as f:
            id = f.read().strip()
            if id == "":
                return None
            return id
    except FileNotFoundError:
        return None
    
# Écriture dans le fichier
def save_last_video_id(video_id):
    with open("video_id.txt", "w") as f:
        f.write(video_id)

last_video_id = None


async def checkmsg(channel: discord.TextChannel)-> bool:
    now = datetime.now(timezone.utc)
    five_minutes_ago = now - timedelta(minutes=5)

    async for msg in channel.history(limit=100, after=five_minutes_ago):
        if msg.author == bot.user:
            return True

    return False

def get_video_detail(id:str)->tuple[int,str,str,int]: # durée en secondes, titre, lien
        video_url = f"https://www.youtube.com/watch?v={id}"
        # Nouvelle requête pour choper les détails de la vidéo
        video_req = youtube.videos().list(
            part="contentDetails,snippet",
            id=id
        )
        video_res = video_req.execute()
        video_info = video_res["items"][0]

        duration_str = video_info["contentDetails"]["duration"]
        duration = parse_duration(duration_str).total_seconds()

        title = video_info["snippet"]["title"]  # ← LE TITRE !
        published_at = video_info["snippet"]["publishedAt"]  # format ISO 8601
        published_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_since_upload = int((now - published_time).total_seconds())
        return (duration,title,video_url,time_since_upload)

async def send_video_notification(video_title:str,video_link:str,channel:discord.TextChannel):
    message_ = await channel.send(f"Nouvelle vidéo en ligne :\n **{video_title}**\n 🎥 {video_link} \n ||@everyone||")
    await message_.add_reaction(choice(EMOJIES))
    await message_.add_reaction(choice(EMOJIES))
    emoji = discord.utils.get(channel.guild.emojis, name = choice(MC_EMOJIES[:6]))
    print(emoji)
    if emoji:
        await message_.add_reaction(emoji)
    

async def check_new_video():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    last_saved_video_id = load_last_video_id()

    while True:
        try:
            req = youtube.activities().list(
                part="contentDetails",
                channelId=YOUTUBE_CHANNEL_ID,
                maxResults=1
            )
            res = req.execute()
            latest_video = res["items"][0]["contentDetails"]["upload"]["videoId"]

            if latest_video != last_saved_video_id: # si la video est différentes de celle enregistré
                duration, title, link, time_since_upload = get_video_detail(latest_video)

                if duration > SHORT_DURATION :
                    if time_since_upload < MAX_VIDEO_DELAY: # si la video fait plus de SHORT_DURATION on enregistre l'id et on envoie la notif
                        if not await checkmsg(bot.get_channel(CHANNEL_ID)):
                            await send_video_notification(title,link,channel)
                            save_last_video_id(latest_video)
                            print(f"nouvelle vidéo on envoi un message et on sauvegarde l'id (latest_video: {latest_video}, last_saved_video_id: {last_saved_video_id})")
                            last_saved_video_id = latest_video
                        else:
                            print(f"message déjà envoyer il y a 5 min")
                    else:
                        print(f"delay depuis l'upload dépasser (delai: {time_since_upload})")
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
        if interaction.user.id not in ALLOWED_ID:
            await interaction.edit_original_response(content=":x: pas les perms")
            return
        await channel.send(message)
        await interaction.edit_original_response(content=":white_check_mark: c'est bon")
    except Exception as e:
        await interaction.edit_original_response(content=":warning: Une erreur interne est survenu (check logs)")
        raise e 

@bot.tree.command(
    name="trigger_last_notif",
    description="Commande accessible uniquement dans un serveur spécifique",
    guild=discord.Object(id=GUILD_ID)
)
async def trigger_last_notif(interaction:discord.Interaction, channel:discord.TextChannel = None):
    await interaction.response.defer(thinking=True, ephemeral=True)
    channel = bot.get_channel(CHANNEL_ID)
    try:
        if channel == None:
            channel = interaction.guild.get_channel(CHANNEL_ID)
        if interaction.user.id not in ALLOWED_ID:
            await interaction.edit_original_response(content=":x: pas les perms")
            return
        last_id = load_last_video_id()
        if (last_id):
            _, title, link, _ = get_video_detail(last_id)
            await send_video_notification(title, link, channel)
            print("trigger_last_notif envoyé")
            await interaction.edit_original_response(content=":white_check_mark: c'est bon")
        else:
            await interaction.edit_original_response(content=":x: le lien de la derniere vidéo n'est pas valide ")
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
    bot.loop.create_task(check_new_video())


bot.run(TOKEN)