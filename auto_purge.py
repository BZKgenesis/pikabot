import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("pikabot")


class AutoPurge(commands.Cog):
    """
    Module de suppression automatique.
    Dès qu'un membre envoie un message dans le salon déclencheur,
    tous ses messages des N dernières heures sont supprimés sur tout le serveur.
    """

    def __init__(self, bot: commands.Bot, guild_id: int, allowed_ids: list[int]):
        self.bot = bot
        self.guild_id = guild_id
        self.allowed_ids = allowed_ids

        self.enabled: bool = False
        self.trigger_channel_id: int | None = None
        self.hours: int = 24

        # Lier toutes les app_commands de ce Cog au guild pour une synchro instantanée
        self._guild_object = discord.Object(id=guild_id)
        for cmd in self.__cog_app_commands__:
            cmd.guild_ids = [guild_id]   # synchronisation guild uniquement (instantanée)

    # ─── Vérification de permission ────────────────────────────────────────────

    def _is_allowed(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in self.allowed_ids

    # ─── Commande /autopurge_setup ─────────────────────────────────────────────

    @app_commands.command(
        name="autopurge_setup",
        description="Configure le salon déclencheur et la fenêtre de suppression"
    )
    @app_commands.describe(
        channel="Salon dont les messages déclenchent la purge",
        hours="Supprimer les messages des N dernières heures (défaut : 24)"
    )
    async def autopurge_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        hours: int = 24
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if not self._is_allowed(interaction):
            await interaction.edit_original_response(content=":x: pas les perms")
            return

        self.trigger_channel_id = channel.id
        self.hours = max(1, hours)

        logger.info(
            f"AutoPurge configuré par {interaction.user.id} – "
            f"salon={channel.id} fenêtre={self.hours}h"
        )
        await interaction.edit_original_response(
            content=(
                f":white_check_mark: AutoPurge configuré !\n"
                f"**Salon déclencheur :** {channel.mention}\n"
                f"**Fenêtre :** {self.hours} heure(s)\n"
                f"**État :** {'✅ activé' if self.enabled else '⏸️ désactivé'}"
            )
        )

    # ─── Commande /autopurge_toggle ────────────────────────────────────────────

    @app_commands.command(
        name="autopurge_toggle",
        description="Active ou désactive la suppression automatique"
    )
    async def autopurge_toggle(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if not self._is_allowed(interaction):
            await interaction.edit_original_response(content=":x: pas les perms")
            return

        if self.trigger_channel_id is None:
            await interaction.edit_original_response(
                content=":warning: Configure d'abord le salon avec `/autopurge_setup`."
            )
            return

        self.enabled = not self.enabled
        state = "✅ **activée**" if self.enabled else "⏸️ **désactivée**"
        logger.info(f"AutoPurge {'activé' if self.enabled else 'désactivé'} par {interaction.user.id}")
        await interaction.edit_original_response(
            content=f"Suppression automatique {state}."
        )

    # ─── Commande /autopurge_status ────────────────────────────────────────────

    @app_commands.command(
        name="autopurge_status",
        description="Affiche l'état actuel de la suppression automatique"
    )
    async def autopurge_status(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if not self._is_allowed(interaction):
            await interaction.edit_original_response(content=":x: pas les perms")
            return

        if self.trigger_channel_id is None:
            await interaction.edit_original_response(
                content=":grey_question: Aucun salon déclencheur configuré. Utilise `/autopurge_setup`."
            )
            return

        channel = self.bot.get_channel(self.trigger_channel_id)
        channel_mention = channel.mention if channel else f"ID {self.trigger_channel_id} (introuvable)"
        state = "✅ Activée" if self.enabled else "⏸️ Désactivée"

        await interaction.edit_original_response(
            content=(
                f"**── AutoPurge ──**\n"
                f"**État :** {state}\n"
                f"**Salon déclencheur :** {channel_mention}\n"
                f"**Fenêtre :** {self.hours} heure(s)"
            )
        )

    # ─── Listener on_message ───────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.enabled:
            return
        if message.author.bot:
            return
        if message.guild is None:
            return
        if message.channel.id != self.trigger_channel_id:
            return

        member = message.author
        guild = message.guild
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.hours)

        logger.info(
            f"AutoPurge déclenché par {member} dans #{message.channel.name} "
            f"– suppression sur {self.hours}h"
        )

        total_deleted, errors = await self._purge_member(guild, member, cutoff)

        logger.info(f"AutoPurge terminé – {total_deleted} message(s) supprimé(s) pour {member}")
        if errors:
            for err in errors:
                logger.warning(f"AutoPurge erreur : {err}")

    # ─── Logique de suppression réutilisable ───────────────────────────────────

    async def _purge_member(
        self,
        guild: discord.Guild,
        member: discord.Member | discord.User,
        cutoff: datetime
    ) -> tuple[int, list[str]]:
        """Parcourt tous les salons textuels et supprime les messages de `member` après `cutoff`."""

        total_deleted = 0
        errors: list[str] = []

        for channel in guild.text_channels:
            me = guild.me
            if not channel.permissions_for(me).read_message_history:
                continue
            if not channel.permissions_for(me).manage_messages:
                errors.append(f"#{channel.name} : permission `Gérer les messages` manquante")
                continue

            try:
                to_delete: list[discord.Message] = []
                async for msg in channel.history(limit=None, after=cutoff):
                    if msg.author.id == member.id:
                        to_delete.append(msg)

                # Messages < 14 jours → bulk_delete (max 100 par appel)
                bulk = [
                    m for m in to_delete
                    if (datetime.now(timezone.utc) - m.created_at).days < 14
                ]
                # Messages plus anciens → suppression individuelle
                single = [m for m in to_delete if m not in bulk]

                for i in range(0, len(bulk), 100):
                    batch = bulk[i : i + 100]
                    if len(batch) == 1:
                        await batch[0].delete()
                    else:
                        await channel.delete_messages(batch)
                    total_deleted += len(batch)
                    await asyncio.sleep(1)

                for msg in single:
                    try:
                        await msg.delete()
                        total_deleted += 1
                        await asyncio.sleep(0.5)
                    except discord.errors.NotFound:
                        pass

            except discord.errors.Forbidden:
                errors.append(f"#{channel.name} : accès refusé")
            except Exception as e:
                errors.append(f"#{channel.name} : {e}")

        return total_deleted, errors


async def setup(bot: commands.Bot, guild_id: int, allowed_ids: list[int], trigger_channel_id: int = 0, hours:int = 24, enabled:bool = False):
    """
    Appelé depuis on_ready, AVANT bot.tree.sync().
    Le Cog enregistre ses commandes dans le guild tree ;
    le sync() du script principal les poussera vers Discord.
    """
    cog = AutoPurge(bot, guild_id, allowed_ids)
    guild_obj = discord.Object(id=guild_id)
    if trigger_channel_id != 0:
        cog.trigger_channel_id = trigger_channel_id
    cog.hours = max(hours, 1)
    cog.enabled = enabled

    # Ajoute le Cog et copie ses commandes dans le guild command tree
    await bot.add_cog(cog, guilds=[guild_obj])
    logger.info("Module AutoPurge chargé et commandes enregistrées dans le guild tree")
    return cog