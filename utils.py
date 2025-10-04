import yaml,os
from isodate import parse_duration
from datetime import datetime, timezone
def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        raw_cfg = yaml.safe_load(f)

    # Séparer les valeurs globales et les chaînes
    defaults_values_ = {
        "YOUTUBE_API_KEY": raw_cfg.get("YOUTUBE_API_KEY"),
        "TOKEN": raw_cfg.get("TOKEN"),
        "GUILD_ID": raw_cfg.get("GUILD_ID"),
        "GLOBAL_CHECK_INTERVAL": raw_cfg.get("GLOBAL_CHECK_INTERVAL"),
        "SHORT_DURATION": raw_cfg.get("SHORT_DURATION"),
        "MAX_VIDEO_DELAY": raw_cfg.get("MAX_VIDEO_DELAY"),
        "ALLOWED_IDS": raw_cfg.get("ALLOWED_IDS"),
        "EMOJIS": raw_cfg.get("EMOJIS"),
        "MC_EMOJIS": raw_cfg.get("MC_EMOJIS"),
    }

    channels_data_ = raw_cfg.get("channels", {})

    # Remplacer les références par les vraies valeurs
    for name, data in channels_data_.items():
        data["id"] = name
        for key, value in data.items():
            if isinstance(value, str) and value in defaults_values_:
                data[key] = defaults_values_[value]

    os.makedirs("videos_id", exist_ok=True)

    for channel_id in channels_data_.keys():
        path = os.path.join("videos_id", f"{channel_id}_video_id.txt")
        if not os.path.exists(path):
            open(path, "w").close()  # crée/écrase un fichier vide

    return defaults_values_, channels_data_


def load_last_video_id(channel_info:dict):
    try:
        path = os.path.join("videos_id", f"{channel_info['id']}_video_id.txt")
        with open(path, "r") as f:
            video_id = f.read().strip()
            if video_id == "":
                return None
            return video_id
    except FileNotFoundError:
        return None

def save_last_video_id(video_id, channel_info:dict):
    path = os.path.join("videos_id", f"{channel_info['id']}_video_id.txt")
    with open(f"{path}_video_id.txt", "w") as f:
        f.write(video_id)


def get_video_detail(youtube_video_id:str, youtube)->tuple[int,str,str,int]: # durée en secondes, titre, lien
        video_url = f"https://www.youtube.com/watch?v={youtube_video_id}"
        # Nouvelle requête pour choper les détails de la vidéo
        video_req = youtube.videos().list(
            part="contentDetails,snippet",
            id=youtube_video_id
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
        return duration,title,video_url,time_since_upload
