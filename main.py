"""
Main file for the Chii discord bot.
This bot helps in setting up and managing the Chii community server.
"""
import os
import logging
import time
import asyncio
import discord
from discord.ext import commands
import config
from keep_alive import keep_alive

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('chii_bot')

# Set up intents (permissions)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f"Connecté en tant que {bot.user}")

    # Set bot activity
    activity = discord.Activity(type=discord.ActivityType.listening, 
                               name=f"{config.PREFIX}help")
    await bot.change_presence(activity=activity)

    # Définir une variable globale pour suivre la connexion
    bot.last_heartbeat = time.time()

    # Load all cogs
    for cog in config.COGS:
        try:
            await bot.load_extension(f"cogs.{cog}")
            logger.info(f"Cog '{cog}' chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du cog '{cog}': {e}")

    # Démarrer la tâche de heartbeat pour surveiller la connexion
    if not hasattr(bot, 'heartbeat_task') or bot.heartbeat_task is None:
        bot.heartbeat_task = bot.loop.create_task(check_heartbeat())
        logger.info("Tâche de surveillance de la connexion démarrée")

async def check_heartbeat():
    """Vérifie régulièrement que le bot est toujours connecté à Discord."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            # Vérifier si le bot est toujours connecté
            if bot.is_ws_ratelimited():
                logger.warning("Le bot est rate-limité par le websocket Discord")

            # Ping Discord pour vérifier la connexion
            latency = bot.latency * 1000
            if latency > 1000:  # Latence > 1 seconde
                logger.warning(f"Latence élevée détectée: {latency:.2f}ms")
            else:
                logger.debug(f"Heartbeat Discord OK - Latence: {latency:.2f}ms")

            # Mettre à jour le timestamp du dernier heartbeat
            bot.last_heartbeat = time.time()

            # Attendre 5 minutes avant la prochaine vérification
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Erreur lors du heartbeat: {e}")
            await asyncio.sleep(60)  # Attendre une minute en cas d'erreur

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for command errors."""
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas les permissions requises pour cette commande.")
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cette commande est en cooldown. Réessaie dans {error.retry_after:.2f} secondes.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❓ Argument manquant: {error.param.name}")
        return

    # Log unknown errors
    logger.error(f"Erreur de commande: {error}")
    await ctx.send(f"❌ Une erreur est survenue: {error}")

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        placeholder="Choisissez une catégorie",
        options=[
            discord.SelectOption(label="Admin", emoji="👑", value="admin"),
            discord.SelectOption(label="Modération", emoji="🛡️", value="mod"),
            discord.SelectOption(label="TikTok", emoji="📱", value="tiktok"),
            discord.SelectOption(label="Musique", emoji="🎵", value="music"),
            discord.SelectOption(label="Événements", emoji="🎉", value="events"),
            discord.SelectOption(label="Utilitaires", emoji="🌸", value="utils")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        embeds = {
            "admin": discord.Embed(
                title="👑 Commandes d'administration",
                description="Commandes réservées aux administrateurs",
                color=0xFFC0CB
            ).add_field(name="Configuration", value="\n".join([
                f"`{config.PREFIX}setup_ninis` • Config serveur",
                f"`{config.PREFIX}setup_verification` • Système vérif",
                f"`{config.PREFIX}update_rules` • Règlement",
                f"`{config.PREFIX}add_role_menu` • Menu rôles",
                f"`{config.PREFIX}create_stats_channels` • Crée stats",
                f"`{config.PREFIX}find_stats_channels` • Trouve stats",
                f"`{config.PREFIX}update_stats` • MAJ stats",
                f"`{config.PREFIX}reload_cogs` • Recharge modules"
            ])),
            "mod": discord.Embed(
                title="🛡️ Commandes de modération",
                description="Commandes pour gérer le serveur",
                color=0xFFC0CB
            ).add_field(name="Modération", value="\n".join([
                f"`{config.PREFIX}clear [n]` • Supprime messages",
                f"`{config.PREFIX}kick @user` • Expulse",
                f"`{config.PREFIX}ban @user` • Bannit",
                f"`{config.PREFIX}mute/unmute @user` • Muet",
                f"`{config.PREFIX}warnings` • Avertissements"
            ])),
            "tiktok": discord.Embed(
                title="📱 Commandes TikTok",
                description="Gestion des comptes TikTok",
                color=0xFFC0CB
            ).add_field(name="TikTok", value="\n".join([
                f"`{config.PREFIX}set_tiktok @user` • Associe compte",
                f"`{config.PREFIX}remove_tiktok @user` • Retire compte",
                f"`{config.PREFIX}list_tiktok` • Liste comptes",
                f"`{config.PREFIX}check_tiktok_now` • Vérifie mises à jour"
            ])),
            "music": discord.Embed(
                title="🎵 Commandes musicales",
                description="Système de musique",
                color=0xFFC0CB
            ).add_field(name="Musique", value="\n".join([
                f"`{config.PREFIX}play [recherche]` • Joue musique",
                f"`{config.PREFIX}skip/pause/resume` • Contrôles",
                f"`{config.PREFIX}queue` • Liste d'attente",
                f"`{config.PREFIX}volume [0-100]` • Volume"
            ])),
            "events": discord.Embed(
                title="🎉 Commandes d'événements",
                description="Gestion des événements et giveaways",
                color=0xFFC0CB
            ).add_field(name="Événements", value="\n".join([
                f"`{config.PREFIX}gstart <temps> <nb_gagnants> <prix>` • Lance un giveaway",
                f"`{config.PREFIX}giveaway_reroll [msg_id]` • Retire un gagnant",
                f"`{config.PREFIX}setup_daily_question` • Config question du jour",
                f"`{config.PREFIX}send_question_now` • Envoie une question",
                f"`{config.PREFIX}add_question [texte]` • Ajoute question"
            ])),
            "utils": discord.Embed(
                title="🌸 Commandes utilitaires",
                description="Outils et commandes diverses",
                color=0xFFC0CB
            ).add_field(name="Utilitaires", value="\n".join([
                f"`{config.PREFIX}add_emojis [type] [n]` • Ajoute émojis",
                f"`{config.PREFIX}info/serverinfo` • Infos",
                f"`{config.PREFIX}avatar @user` • Avatar",
                f"`{config.PREFIX}userinfo @user` • Infos membre",
                f"`{config.PREFIX}ask [question]` • ChatGPT"
            ]))
        }

        embed = embeds.get(select.values[0])
        embed.set_footer(text="✧ Bot Chii • Made with 💖")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(name="help")
async def help_command(ctx):
    """Affiche l'aide interactive avec toutes les commandes."""
    is_admin = ctx.author.guild_permissions.administrator
    is_mod = ctx.author.guild_permissions.manage_messages

    class HelpView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)

        @discord.ui.select(
            placeholder="✨ Choisissez une catégorie",
            options=[
                discord.SelectOption(label="🎮 Commandes générales", emoji="🌸", value="general", description="Commandes de base pour tous les membres"),
                discord.SelectOption(label="🎵 Musique", emoji="🎵", value="music", description="Système de musique et lecteur"),
                discord.SelectOption(label="📱 TikTok", emoji="📱", value="tiktok", description="Gestion des notifications TikTok"),
                discord.SelectOption(label="🎉 Événements", emoji="🎊", value="events", description="Giveaways et événements"),
                discord.SelectOption(label="💡 Utilitaires", emoji="⚙️", value="utils", description="Commandes pratiques"),
                *([discord.SelectOption(label="🛡️ Modération", emoji="🔨", value="mod", description="Outils de modération")] if is_mod else []),
                *([discord.SelectOption(label="⚡ Administration", emoji="👑", value="admin", description="Configuration du serveur")] if is_admin else [])
            ]
        )
        async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
            embeds = {
                "general": discord.Embed(
                    title="🎮 Commandes générales",
                    description="Les commandes de base accessibles à tous",
                    color=0xFFC0CB
                ).add_field(name="Profil", value="\n".join([
                    f"`{config.PREFIX}rank` • Voir ton niveau",
                    f"`{config.PREFIX}profile` • Afficher ton profil",
                    f"`{config.PREFIX}avatar [@user]` • Voir un avatar",
                    f"`{config.PREFIX}userinfo [@user]` • Info utilisateur"
                ])).add_field(name="Interaction", value="\n".join([
                    f"`{config.PREFIX}suggest [idée]` • Faire une suggestion",
                    f"`{config.PREFIX}say [texte]` • Faire parler le bot",
                    f"`{config.PREFIX}ping` • Tester la latence"
                ])),

                "music": discord.Embed(
                    title="🎵 Système musical",
                    description="Commandes pour écouter de la musique",
                    color=0x1DB954
                ).add_field(name="Lecture", value="\n".join([
                    f"`{config.PREFIX}play [titre/URL]` • Jouer une musique",
                    f"`{config.PREFIX}pause/resume` • Pause/Reprise",
                    f"`{config.PREFIX}skip` • Passer la musique",
                    f"`{config.PREFIX}stop` • Arrêter la musique"
                ])).add_field(name="File d'attente", value="\n".join([
                    f"`{config.PREFIX}queue` • Voir la file d'attente",
                    f"`{config.PREFIX}clear` • Vider la file",
                    f"`{config.PREFIX}shuffle` • Mélanger la file",
                    f"`{config.PREFIX}volume [0-100]` • Régler le volume"
                ])),

                "tiktok": discord.Embed(
                    title="📱 Système TikTok",
                    description="Gestion des notifications TikTok",
                    color=0xFE2C55
                ).add_field(name="Configuration", value="\n".join([
                    f"`{config.PREFIX}set_tiktok @user [compte]` • Lier un compte",
                    f"`{config.PREFIX}remove_tiktok @user` • Retirer un compte",
                    f"`{config.PREFIX}list_tiktok` • Liste des comptes",
                    f"`{config.PREFIX}check_tiktok_now` • Vérifier manuellement"
                ])),

                "events": discord.Embed(
                    title="🎉 Événements",
                    description="Gestion des événements et giveaways",
                    color=0xFF73FA
                ).add_field(name="Giveaways", value="\n".join([
                    f"`{config.PREFIX}gstart [temps] [gagnants] [prix]` • Lancer",
                    f"`{config.PREFIX}gend [ID]` • Terminer",
                    f"`{config.PREFIX}greroll [ID]` • Retirer"
                ])).add_field(name="Questions", value="\n".join([
                    f"`{config.PREFIX}qotd` • Question du jour",
                    f"`{config.PREFIX}add_question [texte]` • Ajouter"
                ])),

                "utils": discord.Embed(
                    title="💡 Utilitaires",
                    description="Commandes utiles diverses",
                    color=0x58B9FF
                ).add_field(name="Serveur", value="\n".join([
                    f"`{config.PREFIX}serverinfo` • Info serveur",
                    f"`{config.PREFIX}members` • Liste membres",
                    f"`{config.PREFIX}roles` • Liste rôles"
                ])).add_field(name="Autres", value="\n".join([
                    f"`{config.PREFIX}remind [temps] [rappel]` • Rappel",
                    f"`{config.PREFIX}poll [question]` • Sondage",
                    f"`{config.PREFIX}weather [ville]` • Météo"
                ])),

                "mod": discord.Embed(
                    title="🛡️ Modération",
                    description="Outils de modération du serveur",
                    color=0xFF5C5C
                ).add_field(name="Sanctions", value="\n".join([
                    f"`{config.PREFIX}warn @user [raison]` • Avertir",
                    f"`{config.PREFIX}kick @user [raison]` • Expulser",
                    f"`{config.PREFIX}ban @user [raison]` • Bannir",
                    f"`{config.PREFIX}mute @user [durée]` • Rendre muet"
                ])).add_field(name="Gestion", value="\n".join([
                    f"`{config.PREFIX}clear [nombre]` • Supprimer messages",
                    f"`{config.PREFIX}slowmode [secondes]` • Mode lent",
                    f"`{config.PREFIX}lock/unlock` • Verrouiller salon"
                ])) if is_mod else None,

                "admin": discord.Embed(
                    title="⚡ Administration",
                    description="Configuration avancée du serveur",
                    color=0xFFD700
                ).add_field(name="Setup", value="\n".join([
                    f"`{config.PREFIX}setup_ninis` • Config serveur",
                    f"`{config.PREFIX}setup_verification` • Système vérif",
                    f"`{config.PREFIX}create_stats_channels` • Stats serveur"
                ])).add_field(name="Gestion", value="\n".join([
                    f"`{config.PREFIX}add_role_menu` • Menu rôles",
                    f"`{config.PREFIX}update_rules` • Règlement",
                    f"`{config.PREFIX}reload_cogs` • Recharger modules"
                ])) if is_admin else None
            }

            embed = embeds.get(select.values[0])
            if embed:
                embed.set_footer(text="✧ Bot Chii • Made with 💖")
                await interaction.response.edit_message(embed=embed, view=self)

    # Message d'accueil initial
    welcome_embed = discord.Embed(
        title="✦ ꒰ Aide du Bot Chii ꒱",
        description="Bienvenue dans le menu d'aide interactif !\n\n"
                    "Sélectionnez une catégorie dans le menu déroulant ci-dessous pour voir les commandes disponibles.",
        color=0xFFC0CB
    )
    welcome_embed.add_field(
        name="🔥 Nouveautés",
        value="• Système de niveaux\n• Questions du jour\n• Menu de rôles amélioré",
        inline=False
    )
    welcome_embed.set_footer(text="✧ Bot Chii • Made with 💖")
    welcome_embed.set_thumbnail(url=bot.user.display_avatar.url)

    view = HelpView()
    await ctx.send(embed=welcome_embed, view=view)

@discord.ui.select(placeholder="Choisissez une catégorie")
async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
    embeds = {
        "basic": discord.Embed(
            title="🌸 Commandes basiques",
            description="Commandes accessibles à tous",
            color=0xFFC0CB
        ).add_field(name="Général", value="\n".join([
            f"`{config.PREFIX}help` • Affiche l'aide",
            f"`{config.PREFIX}ping` • Vérifie la latence",
            f"`{config.PREFIX}avatar [@user]` • Montre l'avatar",
            f"`{config.PREFIX}userinfo [@user]` • Infos utilisateur",
            f"`{config.PREFIX}suggest [idée]` • Suggère une idée"
        ])),

        "tiktok": discord.Embed(
            title="📱 Commandes TikTok",
            description="Gestion des notifications TikTok",
            color=0xFFC0CB
        ).add_field(name="TikTok", value="\n".join([
            f"`{config.PREFIX}list_tiktok` • Liste les comptes"
        ])),

        "music": discord.Embed(
            title="🎵 Commandes musicales",
            description="Système de musique",
            color=0xFFC0CB
        ).add_field(name="Musique", value="\n".join([
            f"`{config.PREFIX}play [recherche]` • Joue musique",
            f"`{config.PREFIX}skip/pause/resume` • Contrôles",
            f"`{config.PREFIX}queue` • Liste d'attente"
        ])),

        "mod": discord.Embed(
            title="🛡️ Commandes de modération",
            description="Modération du serveur",
            color=0xFFC0CB
        ).add_field(name="Modération", value="\n".join([
            f"`{config.PREFIX}clear [n]` • Supprime messages",
            f"`{config.PREFIX}warn @user` • Avertit",
            f"`{config.PREFIX}mute/unmute @user` • Rend muet"
        ])) if is_mod else None,

        "admin": discord.Embed(
            title="👑 Commandes d'administration",
            description="Administration du serveur",
            color=0xFFC0CB
        ).add_field(name="Administration", value="\n".join([
            f"`{config.PREFIX}setup_ninis` • Config serveur",
            f"`{config.PREFIX}update_rules` • Règlement",
            f"`{config.PREFIX}set_tiktok @user` • Config TikTok"
        ])) if is_admin else None
    }

    embed = embeds.get(select.values[0])
    if embed:
        embed.set_footer(text="✧ Bot Chii • Made with 💖")
        await interaction.response.edit_message(embed=embed, view=self)

    # Message d'accueil initial
    embed = discord.Embed(
        title="✦ ꒰ Aide du Bot Chii ꒱",
        description="Sélectionnez une catégorie dans le menu déroulant ci-dessous ♡",
        color=0xFFC0CB
    )
    embed.set_footer(text="✧ Bot Chii • Made with 💖")
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    view = HelpView()
    await ctx.send(embed=embed, view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def reload_cogs(ctx):
    """Reload all cogs (admin only)."""
    reloaded = []
    failed = []

    for cog in config.COGS:
        try:
            await bot.reload_extension(f"cogs.{cog}")
            reloaded.append(cog)
        except Exception as e:
            failed.append(f"{cog}: {e}")
            logger.error(f"Erreur lors du rechargement du cog '{cog}': {e}")

    # Create response message
    response = "✅ **Modules rechargés:**\n"
    response += "\n".join([f"- {cog}" for cog in reloaded])

    if failed:
        response += "\n\n❌ **Échecs:**\n"
        response += "\n".join([f"- {failure}" for failure in failed])

    await ctx.send(response)

@bot.command()
async def info(ctx):
    """Display information about the bot."""
    embed = discord.Embed(
        title="✦ ꒰ Bot Chii ꒱",
        description="Je suis le bot officiel du serveur, conçu pour vous aider à gérer et profiter de votre communauté !",
        color=discord.Colour.pink()
    )

    # Bot info
    embed.add_field(name="Préfixe", value=f"`{config.PREFIX}`", inline=True)
    embed.add_field(name="Version", value=config.VERSION, inline=True)
    embed.add_field(name="Serveurs", value=str(len(bot.guilds)), inline=True)

    # Add stats
    embed.add_field(name="Latence", value=f"{round(bot.latency * 1000)}ms", inline=True)

    # Add website link
    embed.add_field(name="Site Web", value=f"[Visiter le site](http://ninis.replit.app)", inline=True)

    # Set footer
    embed.set_footer(text="✧ Bot Chii • Made with 💖")

    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    """Display information about the server."""
    guild = ctx.guild

    # Get role counts
    role_count = len(guild.roles)

    # Get channel counts
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)

    # Create embed
    embed = discord.Embed(
        title=f"✦ ꒰ {guild.name} ꒱",
        description="Informations sur le serveur",
        color=discord.Colour.pink()
    )

    # Add basic info
    embed.add_field(name="ID", value=guild.id, inline=True)
    embed.add_field(name="Propriétaire", value=guild.owner.mention, inline=True)
    embed.add_field(name="Membres", value=guild.member_count, inline=True)

    # Add channel info
    embed.add_field(name="Catégories", value=categories, inline=True)
    embed.add_field(name="Salons textuels", value=text_channels, inline=True)
    embed.add_field(name="Salons vocaux", value=voice_channels, inline=True)

    # Add role info
    embed.add_field(name="Rôles", value=role_count, inline=True)
    embed.add_field(name="Création", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)

    # Set server icon if available
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Set footer
    embed.set_footer(text="✧ Bot Chii • Made with 💖")

    await ctx.send(embed=embed)

if __name__ == "__main__":
    # Start the keep_alive web server in a background thread
    keep_thread = keep_alive()

    # Get token from environment variables with fallback to config
    token = os.getenv("DISCORD_TOKEN", config.TOKEN)

    # Anti-crash system with automatic restart
    restart_count = 0
    max_restarts = 5
    retry_interval = 60  # secondes

    while True:
        try:
            logger.info(f"Démarrage du bot (tentative #{restart_count + 1})")
            # Run the bot (this will block until the bot is closed/crashes)
            bot.run(token)

            # If we get here, the bot was closed gracefully
            logger.info("Le bot s'est arrêté proprement.")
            break

        except Exception as e:
            restart_count += 1
            logger.error(f"Erreur critique: {str(e)}")

            # Note: Les redémarrages sont gérés par le nouveau système keep_alive

            if restart_count >= max_restarts:
                logger.critical(f"Trop de redémarrages ({max_restarts}). Arrêt du bot.")
                break

            logger.warning(f"Redémarrage du bot dans {retry_interval} secondes... (tentative {restart_count}/{max_restarts})")
            import time
            time.sleep(retry_interval)

            # Reconnect to Discord's gateway
            bot._ready.clear()

            # Increase retry interval for next attempt (exponential backoff)
            retry_interval = min(retry_interval * 2, 900)  # Max 15 minutes

# Cette section permet à ce fichier d'être utilisé par Gunicorn pour le serveur web
# Importer l'application Flask depuis app.py
from app import app

# Cette variable est utilisée par Gunicorn
# Nécessaire pour le workflow "Start application"