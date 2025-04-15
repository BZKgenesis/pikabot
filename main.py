import discord
import asyncio
from googleapiclient.discovery import build
from isodate import parse_duration  # à installer : pip install isodate

TOKEN = "MTM2MTgxMDExMzczNTY5MjUyMg.GlR5Je.7-gYi8vsDaKODJQT8TAk3et1uuOJmwwEx_OpTY"
CHANNEL_ID = 1361823771559858318  # ID du salon Discord
YOUTUBE_API_KEY = "AIzaSyBVxlQ2-Y6NoRHVVcuifY98PqNSkpiRgpY"
YOUTUBE_CHANNEL_ID = "UC4oqjwA0lPgwd4EH3rk_Www"  # ID de la chaîne YouTube

CHECK_INTERVAL = 300 # 5 minutes

SHORT_DURATION = 180 # 3 minutes

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
# Lecture de l’ID depuis le fichier (ou None si fichier vide/inexistant)
def load_last_video_id():
    try:
        with open("video_id.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    
# Écriture dans le fichier
def save_last_video_id(video_id):
    with open("video_id.txt", "w") as f:
        f.write(video_id)

last_video_id = None

async def check_new_video():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    last_video_id = load_last_video_id()

    while True:
        try:
            req = youtube.activities().list(
                part="contentDetails",
                channelId=YOUTUBE_CHANNEL_ID,
                maxResults=1
            )
            res = req.execute()
            latest_video = res["items"][0]["contentDetails"]["upload"]["videoId"]

            if latest_video != last_video_id:
                last_video_id = latest_video
                video_url = f"https://www.youtube.com/watch?v={latest_video}"
                # Nouvelle requête pour choper les détails de la vidéo
                video_req = youtube.videos().list(
                    part="contentDetails,snippet",
                    id=latest_video
                )
                video_res = video_req.execute()
                video_info = video_res["items"][0]
                #print(video_info)

                duration_str = video_info["contentDetails"]["duration"]
                duration = parse_duration(duration_str).total_seconds()
                title = video_info["snippet"]["title"]  # ← LE TITRE !
                if duration > SHORT_DURATION:
                    await channel.send(f"Nouvelle vidéo en ligne :\n **{title}**\n 🎥 {video_url} \n ||@everyone||")

                    save_last_video_id(latest_video)
                    last_video_id = latest_video
                    print("nouvelle vidéo on envoi un message et on sauvegarde l'id")
                else:
                    print("c'est un short on fait rien")
            else:
                print("pas de nouvelle vidée (id identique)")


        except Exception as e:
            print(f"Erreur : {e}")

        await asyncio.sleep(CHECK_INTERVAL)

class MyClient(discord.Client):
    async def setup_hook(self):
        self.loop.create_task(check_new_video())

bot = MyClient(intents=intents)
bot.run(TOKEN)