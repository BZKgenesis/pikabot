# Pikabot

Bot Discord développé en **Python** avec [discord.py](https://discordpy.readthedocs.io/)  
Ce bot est utilisé sur le serveur Discord de [**Pikayorld**](https://www.youtube.com/@Pikayorld) pour notifier automatiquement la sortie des nouvelles vidéos YouTube et fournir quelques commandes de gestion.

---

## ✨ Fonctionnalités principales

### 🔔 Notifications YouTube
- Surveille automatiquement les chaînes YouTube configurées (ex. : Pikayorld, Pikayorld2).
- Envoie un message de notification dans le canal Discord associé quand une **nouvelle vidéo** est publiée.
- Ignore :
  - Les shorts (vidéos trop courtes).
  - Les vidéos trop anciennes (au-delà d’un délai configurable).
  - Les doublons récents (évite le spam).

### 🎭 Réactions automatiques
- Ajoute aléatoirement deux émojis standards et un émoji Minecraft personnalisé (si disponible sur le serveur) sous chaque notification.

### ⚙️ Commandes d’administration
Disponibles uniquement pour les utilisateurs autorisés (listés dans le fichier `config.yaml`) :

- **/send_message**  
  Envoie un message dans un canal Discord choisi.

- **/trigger_last_notif**  
  Ré-envoie la notification de la **dernière vidéo** détectée sur une chaîne YouTube donnée.

### 📡 Surveillance continue
- Vérifie régulièrement (toutes les `GLOBAL_CHECK_INTERVAL` secondes) s’il y a de nouvelles vidéos.
- Gère plusieurs chaînes YouTube en parallèle, avec un décallage des requètes.

---

## ⚙️ Configuration

Le fichier `config.yaml` définit les paramètres du bot.  
Exemple :

```yaml
GUILD_ID: 123456789012345678        # ID du serveur Discord
GLOBAL_CHECK_INTERVAL: 120         # Délai entre les vérifications (en secondes)
SHORT_DURATION: 180                # Durée max d’une vidéo considérée comme short
MAX_VIDEO_DELAY: 600               # Vidéos publiées depuis plus longtemps sont ignorées
MIN_MESSAGE_DELAY: 50              # Temps minimum entre deux notifications

ALLOWED_IDS:                       # IDs Discord autorisés à utiliser les commandes
  - 123456789012345678

EMOJIS:                             # Émojis aléatoires pour les réactions
  - "🔥"                            # Par défaut 2 émojis normaux sont ajoutés au message
  - "😎"

MC_EMOJIS:                          # Émojis Custom (ici minecraft)
  - "Creeper"                       # Par défaut 1 émoji custom est ajouté au message
  - "Warden"

channels:
  pikayorld:
    youtube_channel_id: "UC4oqjwA0lPgwd4EH3rk_Www"
    message: "Nouvelle vidéo :\n**{video_title}**\n🎥 {video_link}\n||@everyone||"
    message_short: "Nouvelle vidéo :\n**{video_title}**\n🎥 {video_link}\n||@everyone||"
    discord_channel_id: 987654321098765432
    discord_channel_id_short: 987654321098765432
````

> 🔑 Variables disponibles dans `message` :
> `{video_title}`, `{video_link}`, `{description}`, `{channel_title}`, `{thumbnail_url}`

---

## 🚀 Lancer le bot

1. **Installer les dépendances**

   ```bash
   pip install -r requirements.txt
   ```

   (Prévoir `discord.py`, `google-api-python-client`, `python-dotenv`, `pyyaml`)

2. **Configurer les variables d’environnement** dans un fichier `.env`

   ```
   DISCORD_TOKEN=ton_token_discord
   YOUTUBE_API_KEY=ta_clef_youtube
   ```

3. **Lancer le bot**

   ```bash
   python main.py
   ```

---

## 📦 Structure du projet

```
.
├── main.py          # Script principal du bot
├── utils.py         # Fonctions utilitaires (chargement config, gestion vidéos…)
├── config.yaml      # Configuration du bot
├── .env             # Jetons secrets
└── requirements.txt # Dépendances Python
```

---

## 📝 Notes

* Le bot synchronise automatiquement les commandes slash (`/`) au démarrage.
* Les logs colorés aident au débogage et au suivi de l’activité du bot.
* Prévoir des permissions suffisantes pour que le bot puisse envoyer des messages et réagir avec des émojis personnalisés.

---