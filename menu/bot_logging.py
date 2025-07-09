"""
Module de logging avancé pour le Bot Ninis.
Ce module enregistre les événements importants du serveur dans un canal dédié.
"""
import discord
import logging
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from discord.ext import commands

# Configuration du logger
logger = logging.getLogger('ninis_bot')

class Logging(commands.Cog):
    """Module de logging avancé pour le serveur."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logs_channels = {}  # {guild_id: channel_id}
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_logs(self, ctx):
        """Configure un système de logs avancé pour le serveur."""
        guild = ctx.guild
        
        # Vérifier si un canal de logs existe déjà
        existing_logs = discord.utils.get(guild.text_channels, name="logs-serveur")
        
        if existing_logs:
            self.logs_channels[guild.id] = existing_logs.id
            await ctx.send(f"✅ Le canal de logs existe déjà : {existing_logs.mention}")
            return
        
        # Créer une catégorie pour les logs si elle n'existe pas
        logs_category = discord.utils.get(guild.categories, name="⚙️・ADMINISTRATION")
        
        if not logs_category:
            try:
                # Définir les permissions pour la catégorie
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # Ajouter des permissions pour les rôles d'administration
                for role_name in ["Owner", "Administrateur", "Admin", "Modérateur", "Modo", "Staff"]:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                logs_category = await guild.create_category(
                    name="⚙️・ADMINISTRATION",
                    overwrites=overwrites,
                    reason="Création de la catégorie d'administration pour les logs"
                )
                
                await ctx.send(f"✅ Catégorie `{logs_category.name}` créée.")
                
            except Exception as e:
                logger.error(f"Erreur lors de la création de la catégorie de logs: {e}")
                await ctx.send(f"❌ Erreur lors de la création de la catégorie: {e}")
                return
        
        # Créer le canal de logs
        try:
            logs_channel = await guild.create_text_channel(
                name="logs-serveur",
                category=logs_category,
                topic="Journal des événements importants du serveur",
                reason="Configuration du système de logs"
            )
            
            # Enregistrer le canal
            self.logs_channels[guild.id] = logs_channel.id
            
            # Message de confirmation
            embed = discord.Embed(
                title="✅ Système de logs configuré",
                description=f"Le canal {logs_channel.mention} a été créé pour les logs du serveur.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Événements enregistrés",
                value=(
                    "• Arrivée et départ de membres\n"
                    "• Création et suppression de canaux\n"
                    "• Modification de rôles\n"
                    "• Messages supprimés\n"
                    "• Messages modifiés\n"
                    "• Événements de modération"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Message initial dans le canal de logs
            initial_embed = discord.Embed(
                title="📝 Logs Serveur Activés",
                description="Ce canal enregistrera les événements importants du serveur.",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            
            initial_embed.set_footer(text=f"Ninis Bot • Logs")
            await logs_channel.send(embed=initial_embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du canal de logs: {e}")
            await ctx.send(f"❌ Erreur lors de la création du canal de logs: {e}")
    
    async def get_logs_channel(self, guild):
        """Récupère le canal de logs pour un serveur."""
        # Vérifier si on connaît déjà le canal
        if guild.id in self.logs_channels:
            channel = guild.get_channel(self.logs_channels[guild.id])
            if channel:
                return channel
        
        # Sinon, chercher le canal par son nom
        channel = discord.utils.get(guild.text_channels, name="logs-serveur")
        if channel:
            self.logs_channels[guild.id] = channel.id
            return channel
        
        return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Enregistre des informations détaillées quand un membre rejoint."""
        guild = member.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="👋 Membre Rejoint",
            description=f"{member.mention} a rejoint le serveur.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Informations de base
        embed.add_field(name="Nom", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        
        # Date de création du compte
        created_at = member.created_at
        created_ago = (datetime.now(timezone.utc) - created_at).days
        created_text = f"<t:{int(created_at.timestamp())}:F> ({created_ago} jours)"
        embed.add_field(name="Compte créé", value=created_text, inline=False)
        
        # Alerte pour les comptes récents (moins de 7 jours)
        if created_ago < 7:
            embed.add_field(
                name="⚠️ Compte Récent",
                value=f"Ce compte a été créé il y a seulement {created_ago} jours.",
                inline=False
            )
            embed.color = discord.Color.orange()
        
        # Photo de profil
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID Membre: {member.id}")
        
        # Récupération avancée des noms précédents via API
        try:
            previous_usernames = []
            # Cette commande récupère les 5 derniers pseudos de l'utilisateur
            user_info = await self.bot.http.request(
                discord.http.Route("GET", f"/users/{member.id}/profile"), 
                {"with_mutual_guilds": False, "with_mutual_friends_count": False}
            )
            
            if "user_profile" in user_info and "previous_usernames" in user_info["user_profile"]:
                previous_usernames = user_info["user_profile"]["previous_usernames"]
                
            if previous_usernames:
                embed.add_field(
                    name="📝 Anciens pseudos",
                    value="\n".join(previous_usernames[:10]),  # Limiter à 10 pseudos max
                    inline=False
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des pseudos précédents: {e}")
            
            # Fallback sur la méthode par cache si l'API échoue
            previous_names = []
            for u in self.bot.users:
                if u.id == member.id and u.name != member.name:
                    previous_names.append(u.name)
            
            if previous_names:
                embed.add_field(
                    name="📝 Anciens pseudos (cache)",
                    value="\n".join(previous_names),
                    inline=False
                )
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Enregistre quand un membre quitte."""
        guild = member.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="👋 Membre Parti",
            description=f"{member.mention} a quitté le serveur.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Informations de base
        embed.add_field(name="Nom", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        
        # Durée dans le serveur
        joined_at = member.joined_at
        if joined_at:
            duration = (datetime.now(timezone.utc) - joined_at)
            days = duration.days
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            duration_text = f"{days} jours, {hours} heures, {minutes} minutes"
            joined_text = f"<t:{int(joined_at.timestamp())}:F> ({duration_text})"
            embed.add_field(name="Durée sur le serveur", value=joined_text, inline=False)
        
        # Rôles du membre
        if len(member.roles) > 1:  # Ignorer @everyone
            roles_str = " ".join([role.mention for role in member.roles if role != guild.default_role])
            if roles_str:
                embed.add_field(name="Rôles", value=roles_str, inline=False)
        
        # Photo de profil
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID Membre: {member.id}")
        
        # Récupération avancée des noms précédents via API
        try:
            previous_usernames = []
            # Cette commande récupère les 5 derniers pseudos de l'utilisateur
            user_info = await self.bot.http.request(
                discord.http.Route("GET", f"/users/{member.id}/profile"), 
                {"with_mutual_guilds": False, "with_mutual_friends_count": False}
            )
            
            if "user_profile" in user_info and "previous_usernames" in user_info["user_profile"]:
                previous_usernames = user_info["user_profile"]["previous_usernames"]
                
            if previous_usernames:
                embed.add_field(
                    name="📝 Anciens pseudos",
                    value="\n".join(previous_usernames[:10]),  # Limiter à 10 pseudos max
                    inline=False
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des pseudos précédents: {e}")
            
            # Fallback sur la méthode par cache si l'API échoue
            previous_names = []
            for u in self.bot.users:
                if u.id == member.id and u.name != member.name:
                    previous_names.append(u.name)
            
            if previous_names:
                embed.add_field(
                    name="📝 Anciens pseudos (cache)",
                    value="\n".join(previous_names),
                    inline=False
                )
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Enregistre les messages supprimés."""
        # Ignorer les messages du bot
        if message.author.bot:
            return
            
        guild = message.guild
        if not guild:
            return
            
        logs_channel = await self.get_logs_channel(guild)
        if not logs_channel:
            return
            
        # Ignorer les suppressions dans le canal de logs lui-même
        if message.channel.id == logs_channel.id:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="🗑️ Message Supprimé",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Informations de base
        embed.add_field(name="Auteur", value=message.author.mention, inline=True)
        embed.add_field(name="Canal", value=message.channel.mention, inline=True)
        
        # Contenu du message
        if message.content:
            # Tronquer le contenu s'il est trop long
            content = message.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(name="Contenu", value=content, inline=False)
        
        # Pièces jointes
        if message.attachments:
            files_text = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
            embed.add_field(name="Pièces jointes", value=files_text, inline=False)
        
        # Ajouter une miniature de l'avatar de l'auteur
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"ID Message: {message.id} | ID Auteur: {message.author.id}")
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Enregistre les messages modifiés."""
        # Ignorer les messages du bot
        if before.author.bot:
            return
            
        # Ignorer si le contenu est le même (ex: intégration mise à jour)
        if before.content == after.content:
            return
            
        guild = before.guild
        if not guild:
            return
            
        logs_channel = await self.get_logs_channel(guild)
        if not logs_channel:
            return
            
        # Ignorer les modifications dans le canal de logs lui-même
        if before.channel.id == logs_channel.id:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="✏️ Message Modifié",
            description=f"Message modifié dans {before.channel.mention}",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Informations de base
        embed.add_field(name="Auteur", value=before.author.mention, inline=True)
        embed.add_field(name="Lien", value=f"[Aller au message]({after.jump_url})", inline=True)
        
        # Contenu du message
        if before.content:
            # Tronquer le contenu s'il est trop long
            content_before = before.content
            if len(content_before) > 1024:
                content_before = content_before[:1021] + "..."
            embed.add_field(name="Avant", value=content_before, inline=False)
        
        if after.content:
            # Tronquer le contenu s'il est trop long
            content_after = after.content
            if len(content_after) > 1024:
                content_after = content_after[:1021] + "..."
            embed.add_field(name="Après", value=content_after, inline=False)
        
        # Ajouter une miniature de l'avatar de l'auteur
        embed.set_thumbnail(url=before.author.display_avatar.url)
        embed.set_footer(text=f"ID Message: {before.id} | ID Auteur: {before.author.id}")
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Enregistre la création de canaux."""
        guild = channel.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel or channel.id == logs_channel.id:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="📝 Canal Créé",
            description=f"Le canal {channel.mention} a été créé.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Détails du canal
        embed.add_field(name="Nom", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        
        if isinstance(channel, discord.TextChannel) and channel.topic:
            embed.add_field(name="Sujet", value=channel.topic, inline=False)
        
        if channel.category:
            embed.add_field(name="Catégorie", value=channel.category.name, inline=True)
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Enregistre la suppression de canaux."""
        guild = channel.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel or channel.id == logs_channel.id:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="🗑️ Canal Supprimé",
            description=f"Le canal **{channel.name}** a été supprimé.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Détails du canal
        embed.add_field(name="ID", value=channel.id, inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        
        if channel.category:
            embed.add_field(name="Catégorie", value=channel.category.name, inline=True)
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Enregistre la création de rôles."""
        guild = role.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="👑 Rôle Créé",
            description=f"Le rôle {role.mention} a été créé.",
            color=role.color,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Détails du rôle
        embed.add_field(name="Nom", value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        
        if role.permissions.value > 0:
            perms = []
            for perm, value in role.permissions:
                if value:
                    perms.append(perm.replace("_", " ").title())
            
            if perms:
                # Tronquer la liste si elle est trop longue
                perms_str = ", ".join(perms)
                if len(perms_str) > 1024:
                    perms_str = perms_str[:1021] + "..."
                embed.add_field(name="Permissions", value=perms_str, inline=False)
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Enregistre la suppression de rôles."""
        guild = role.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel:
            return
        
        # Créer un embed pour le log
        embed = discord.Embed(
            title="🗑️ Rôle Supprimé",
            description=f"Le rôle **{role.name}** a été supprimé.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Détails du rôle
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Couleur", value=str(role.color), inline=True)
        
        # Envoyer l'embed
        await logs_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Enregistre les changements de rôles et de surnom des membres."""
        # Ignorer les mises à jour du bot
        if before.bot:
            return
            
        guild = before.guild
        logs_channel = await self.get_logs_channel(guild)
        
        if not logs_channel:
            return
        
        # Vérifier si les rôles ont changé
        if before.roles != after.roles:
            # Déterminer les rôles ajoutés
            added_roles = [role for role in after.roles if role not in before.roles]
            
            # Déterminer les rôles retirés
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                # Créer un embed pour le log
                embed = discord.Embed(
                    title="🔄 Rôles Modifiés",
                    description=f"Les rôles de {after.mention} ont été modifiés.",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
                
                # Ajouter les détails des modifications
                if added_roles:
                    roles_str = " ".join([role.mention for role in added_roles])
                    embed.add_field(name="✅ Rôles Ajoutés", value=roles_str, inline=False)
                
                if removed_roles:
                    roles_str = " ".join([role.mention for role in removed_roles])
                    embed.add_field(name="❌ Rôles Retirés", value=roles_str, inline=False)
                
                # Ajouter une miniature de l'avatar du membre
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"ID Membre: {after.id}")
                
                # Envoyer l'embed
                await logs_channel.send(embed=embed)
        
        # Vérifier si le surnom a changé
        if before.nick != after.nick:
            # Créer un embed pour le log
            embed = discord.Embed(
                title="📝 Surnom Modifié",
                description=f"Le surnom de {after.mention} a été modifié.",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Ajouter les détails des modifications
            embed.add_field(name="Avant", value=before.nick or "Aucun surnom", inline=True)
            embed.add_field(name="Après", value=after.nick or "Aucun surnom", inline=True)
            
            # Ajouter une miniature de l'avatar du membre
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"ID Membre: {after.id}")
            
            # Envoyer l'embed
            await logs_channel.send(embed=embed)

async def setup(bot):
    """Fonction d'installation du cog."""
    await bot.add_cog(Logging(bot))
    logger.info("Cog 'logging' chargé avec succès")