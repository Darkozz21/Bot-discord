"""
Module de gestion des niveaux pour le Bot Chii.
Ce module permet aux membres de gagner de l'XP et des niveaux avec un système de rôles automatique.
"""

import json
import logging
import math
import os
import discord
from discord.ext import commands
import config

# Configurer le logger
logger = logging.getLogger('ninis_bot')

# Noms de rôles et niveaux associés
LEVEL_ROLES = {
    1: "Nini Nouveau",
    5: "Nini Curieux",
    10: "Nini Actif",
    20: "Nini Confirmé",
    30: "Nini Légende"
}

def xp_for_level(level):
    """Calcule l'XP nécessaire pour atteindre un niveau spécifique."""
    return 5 * (level ** 2) + 50 * level + 100

def calculate_level(xp):
    """Calcule le niveau à partir de l'XP totale."""
    # Équation quadratique inverse de xp_for_level
    # level = (-50 + sqrt(2500 + 20*(xp - 100))) / 10
    discriminant = 2500 + 20 * (xp - 100)
    if discriminant < 0:
        return 0
    
    level = (-50 + math.sqrt(discriminant)) / 10
    return math.floor(level)

class Levels(commands.Cog):
    """Système de niveaux et d'XP pour les membres du serveur."""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'levels_data.json'
        self.levels_data = {}
        self.xp_cooldowns = {}
        self.load_levels_data()
        logger.info("Module de niveaux initialisé")
    
    def load_levels_data(self):
        """Charge les données de niveaux depuis le fichier JSON."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.levels_data = json.load(f)
                    logger.info(f"Données de niveaux chargées pour {len(self.levels_data)} utilisateurs")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des données de niveaux: {e}")
                self.levels_data = {}
        else:
            logger.info("Aucun fichier de données de niveaux trouvé, création d'un nouveau")
            self.levels_data = {}
            self.save_levels_data()
    
    def save_levels_data(self):
        """Sauvegarde les données de niveaux dans le fichier JSON."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.levels_data, f, indent=4)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données de niveaux: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Gère l'attribution d'XP à chaque message."""
        # Ignore les messages de bots et les commandes
        if message.author.bot or message.content.startswith(config.PREFIX):
            return
        
        # Ignore les messages en DM
        if not message.guild:
            return
        
        # Vérifier le cooldown (60 secondes entre chaque gain d'XP)
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        # Structure de données: {guild_id: {user_id: {"xp": int, "level": int, "last_message": timestamp}}}
        if guild_id not in self.levels_data:
            self.levels_data[guild_id] = {}
        
        if user_id not in self.levels_data[guild_id]:
            self.levels_data[guild_id][user_id] = {"xp": 0, "level": 0}
        
        # Cooldown de 60 secondes pour l'XP
        import time
        current_time = time.time()
        cooldown_key = f"{guild_id}:{user_id}"
        
        if cooldown_key in self.xp_cooldowns:
            if current_time - self.xp_cooldowns[cooldown_key] < 60:
                return
        
        # Ajouter de l'XP (entre 15 et 25 par message)
        import random
        xp_gain = random.randint(15, 25)
        old_xp = self.levels_data[guild_id][user_id].get("xp", 0)
        new_xp = old_xp + xp_gain
        
        # Mettre à jour l'XP de l'utilisateur
        self.levels_data[guild_id][user_id]["xp"] = new_xp
        
        # Calculer le nouveau niveau
        old_level = calculate_level(old_xp)
        new_level = calculate_level(new_xp)
        
        # Mettre à jour le cooldown
        self.xp_cooldowns[cooldown_key] = current_time
        
        # Vérifier si l'utilisateur a gagné un niveau
        if new_level > old_level:
            self.levels_data[guild_id][user_id]["level"] = new_level
            
            # Mettre à jour les rôles et envoyer une notification
            await self.update_level_role(message.author, new_level, message.guild)
            await self.send_level_up_notification(message.author, new_level, message.guild)
        
        # Sauvegarder les données tous les 10 messages (pour éviter les sauvegardes trop fréquentes)
        if random.randint(1, 10) == 1:
            self.save_levels_data()
    
    async def update_level_role(self, member, new_level, guild):
        """Met à jour le rôle du membre en fonction de son niveau."""
        # Trouver le rôle de niveau le plus élevé que le membre devrait avoir
        highest_role_level = 0
        for level, role_name in LEVEL_ROLES.items():
            if new_level >= level and level > highest_role_level:
                highest_role_level = level
        
        if highest_role_level == 0:
            return
        
        target_role_name = LEVEL_ROLES[highest_role_level]
        target_role = discord.utils.get(guild.roles, name=target_role_name)
        
        if not target_role:
            logger.warning(f"Le rôle {target_role_name} n'existe pas sur le serveur {guild.name}")
            return
        
        # Supprimer tous les rôles de niveau précédents
        roles_to_remove = []
        for level_role_name in LEVEL_ROLES.values():
            if level_role_name != target_role_name:  # On garde uniquement le rôle cible
                role = discord.utils.get(guild.roles, name=level_role_name)
                if role and role in member.roles:
                    roles_to_remove.append(role)
        
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Mise à jour du rôle de niveau")
                logger.info(f"Rôles de niveau retirés pour {member.name}: {', '.join(r.name for r in roles_to_remove)}")
            except Exception as e:
                logger.error(f"Erreur lors de la suppression des rôles de niveau pour {member.name}: {e}")
        
        # Ajouter le nouveau rôle si nécessaire
        if target_role not in member.roles:
            try:
                await member.add_roles(target_role, reason="Nouveau niveau atteint")
                logger.info(f"{member.name} a reçu le rôle {target_role.name} pour le niveau {new_level}")
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout du rôle {target_role.name} à {member.name}: {e}")
    
    async def send_level_up_notification(self, member, new_level, guild):
        """Envoie une notification dans le salon approprié quand un membre monte de niveau."""
        # Utiliser le salon spécifié par l'ID
        levels_channel = guild.get_channel(1354525332530659589)
        
        if not levels_channel:
            logger.warning(f"Salon de notifications de niveau introuvable pour {member.name}")
            return
        
        # Créer un embed adapté au niveau
        embed = discord.Embed(
            title="Niveau supérieur ! 🌟",
            description=f"Félicitations {member.mention} ! Tu as atteint le niveau **{new_level}** !",
            color=0xffaadd
        )
        
        # Personnaliser l'embed en fonction du palier de niveau
        if new_level == 1:
            embed.add_field(
                name="Rôle obtenu",
                value="Tu obtiens le rôle **Nini Nouveau** ! Bienvenue dans l'aventure ✨",
                inline=False
            )
        elif new_level == 5:
            embed.add_field(
                name="Rôle obtenu",
                value="Tu obtiens le rôle **Nini Curieux** ! Continue comme ça ! 🌸",
                inline=False
            )
        elif new_level == 10:
            embed.add_field(
                name="Rôle obtenu",
                value="Tu obtiens le rôle **Nini Actif** ! Tu es désormais un membre actif de notre communauté ! 🎀",
                inline=False
            )
        elif new_level == 20:
            embed.add_field(
                name="Rôle obtenu",
                value="Tu obtiens le rôle **Nini Confirmé** ! Quelle progression impressionnante ! 🌈",
                inline=False
            )
        elif new_level == 30:
            embed.add_field(
                name="Rôle obtenu",
                value="Tu obtiens le rôle **Nini Légende** ! Tu es une légende de notre serveur ! 👑",
                inline=False
            )
        
        # Ajouter des informations sur le prochain niveau si ce n'est pas le niveau max
        if new_level < 30:
            next_level = new_level + 1
            next_milestone = next((lvl for lvl in sorted(LEVEL_ROLES.keys()) if lvl > new_level), None)
            
            if next_milestone:
                xp_needed = xp_for_level(next_milestone) - self.levels_data[str(guild.id)][str(member.id)]["xp"]
                embed.add_field(
                    name="Prochain palier",
                    value=f"Il te faut **{xp_needed}** XP pour atteindre le rôle **{LEVEL_ROLES[next_milestone]}** (niveau {next_milestone}) !",
                    inline=False
                )
            else:
                xp_current = self.levels_data[str(guild.id)][str(member.id)]["xp"]
                xp_next = xp_for_level(next_level)
                xp_needed = xp_next - xp_current
                
                embed.add_field(
                    name="Prochain niveau",
                    value=f"Il te faut **{xp_needed}** XP pour atteindre le niveau {next_level} !",
                    inline=False
                )
        
        embed.set_footer(text="✨ Système d'XP de Ninis ✨")
        
        try:
            await levels_channel.send(embed=embed)
            logger.info(f"Notification de niveau envoyée pour {member.name} (niveau {new_level})")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification de niveau pour {member.name}: {e}")
    
    @commands.command(aliases=["niveau", "level"])
    async def rank(self, ctx, member: discord.Member = None):
        """Affiche les informations de niveau d'un membre.
        
        Args:
            member: Le membre dont on veut voir le niveau. Si non spécifié, affiche le niveau de l'auteur de la commande.
        """
        if not member:
            member = ctx.author
        
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id not in self.levels_data or user_id not in self.levels_data[guild_id]:
            embed = discord.Embed(
                title="Niveau",
                description=f"{member.mention} n'a pas encore gagné d'XP sur ce serveur.",
                color=0xffaadd
            )
            await ctx.send(embed=embed)
            return
        
        # Récupérer les données de l'utilisateur
        user_data = self.levels_data[guild_id][user_id]
        xp = user_data.get("xp", 0)
        level = calculate_level(xp)
        
        # Calculer les XP nécessaires pour le prochain niveau
        next_level = level + 1
        xp_for_next = xp_for_level(next_level)
        xp_for_current = xp_for_level(level)
        xp_progress = xp - xp_for_current
        xp_required = xp_for_next - xp_for_current
        progress_percentage = min(100, round((xp_progress / xp_required) * 100, 1))
        
        # Créer la barre de progression
        progress_bar = ""
        filled_blocks = round(progress_percentage / 10)
        for i in range(10):
            if i < filled_blocks:
                progress_bar += "■"
            else:
                progress_bar += "□"
        
        # Déterminer le rang de l'utilisateur dans le classement du serveur
        all_users = self.levels_data[guild_id].items()
        sorted_users = sorted(all_users, key=lambda x: x[1].get("xp", 0), reverse=True)
        user_rank = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), 0)
        
        # Créer l'embed
        embed = discord.Embed(
            title=f"Niveau de {member.display_name}",
            color=0xffaadd
        )
        
        # Avatar de l'utilisateur
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Informations principales
        embed.add_field(
            name="🌟 Niveau",
            value=f"**{level}**",
            inline=True
        )
        
        embed.add_field(
            name="✨ XP totale",
            value=f"**{xp}** points",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Rang",
            value=f"**#{user_rank}**",
            inline=True
        )
        
        # Progression vers le prochain niveau
        embed.add_field(
            name=f"Progression vers le niveau {next_level}",
            value=f"{progress_bar} {progress_percentage}%\n{xp_progress}/{xp_required} XP",
            inline=False
        )
        
        # Rôle actuel et prochain rôle
        current_role_level = max((lvl for lvl in LEVEL_ROLES.keys() if level >= lvl), default=0)
        next_role_level = next((lvl for lvl in sorted(LEVEL_ROLES.keys()) if lvl > level), None)
        
        if current_role_level > 0:
            current_role_name = LEVEL_ROLES[current_role_level]
            embed.add_field(
                name="🏅 Rôle actuel",
                value=f"**{current_role_name}**",
                inline=True
            )
        else:
            embed.add_field(
                name="🏅 Rôle actuel",
                value="Aucun rôle de niveau encore",
                inline=True
            )
        
        if next_role_level:
            next_role_name = LEVEL_ROLES[next_role_level]
            xp_for_next_role = xp_for_level(next_role_level)
            xp_needed = xp_for_next_role - xp
            embed.add_field(
                name="🎯 Prochain rôle",
                value=f"**{next_role_name}** (Niveau {next_role_level})\nPlus que **{xp_needed}** XP !",
                inline=True
            )
        else:
            embed.add_field(
                name="🎯 Prochain rôle",
                value="Tu as atteint le rôle maximum ! 👑",
                inline=True
            )
        
        embed.set_footer(text="💬 Gagne de l'XP en discutant sur le serveur !")
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["top", "classement"])
    async def leaderboard(self, ctx):
        """Affiche le classement des membres les plus actifs."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.levels_data or not self.levels_data[guild_id]:
            await ctx.send("Aucune donnée de niveau n'est disponible pour ce serveur.")
            return
        
        # Trier les utilisateurs par XP
        all_users = self.levels_data[guild_id].items()
        sorted_users = sorted(all_users, key=lambda x: x[1].get("xp", 0), reverse=True)
        
        # Limiter à 10 utilisateurs
        top_users = sorted_users[:10]
        
        # Créer l'embed
        embed = discord.Embed(
            title="🏆 Classement des membres les plus actifs",
            description="Les membres ayant le plus d'expérience sur le serveur",
            color=0xffaadd
        )
        
        # Générer la liste des utilisateurs
        leaderboard_text = ""
        for i, (user_id, user_data) in enumerate(top_users):
            # Obtenir l'utilisateur depuis l'ID
            member = ctx.guild.get_member(int(user_id))
            
            if not member:
                # L'utilisateur n'est plus sur le serveur, l'ignorer
                continue
            
            # Calculer le niveau et obtenir l'XP
            xp = user_data.get("xp", 0)
            level = calculate_level(xp)
            
            # Emoji pour les 3 premiers
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
            
            leaderboard_text += f"{medal} **{member.display_name}** • Niveau {level} • {xp} XP\n"
        
        if not leaderboard_text:
            leaderboard_text = "Aucun membre actif trouvé."
        
        embed.description = leaderboard_text
        
        # Ajouter des informations sur les récompenses
        embed.add_field(
            name="🌟 Rôles de niveau",
            value=(
                "• **Nini Nouveau** — Niveau 1\n"
                "• **Nini Curieux** — Niveau 5\n"
                "• **Nini Actif** — Niveau 10\n"
                "• **Nini Confirmé** — Niveau 20\n"
                "• **Nini Légende** — Niveau 30"
            ),
            inline=False
        )
        
        embed.set_footer(text="✨ Gagne de l'XP en discutant sur le serveur ! ✨")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset_xp(self, ctx, member: discord.Member = None):
        """Réinitialise l'XP d'un membre (Admin uniquement).
        
        Args:
            member: Le membre dont l'XP doit être réinitialisée. Si non spécifié, une confirmation sera demandée.
        """
        if not member:
            await ctx.send("⚠️ Cette commande réinitialise l'XP d'un membre. Spécifiez un membre avec `!reset_xp @membre`.")
            return
        
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id in self.levels_data and user_id in self.levels_data[guild_id]:
            # Retirer tous les rôles de niveau
            roles_to_remove = []
            for role_name in LEVEL_ROLES.values():
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if role and role in member.roles:
                    roles_to_remove.append(role)
            
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="Réinitialisation de l'XP")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression des rôles de niveau pour {member.name}: {e}")
            
            # Réinitialiser l'XP
            self.levels_data[guild_id][user_id] = {"xp": 0, "level": 0}
            self.save_levels_data()
            
            await ctx.send(f"✅ L'XP de {member.mention} a été réinitialisée à 0.")
            logger.info(f"XP réinitialisée pour {member.name} par {ctx.author.name}")
        else:
            await ctx.send(f"{member.mention} n'a pas d'XP enregistrée sur ce serveur.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_levels(self, ctx):
        """Crée ou vérifie les rôles de niveau sur le serveur (Admin uniquement)."""
        guild = ctx.guild
        
        # Message d'initialisation
        status_message = await ctx.send("⏳ Configuration des rôles de niveau...")
        
        # Créer les rôles de niveau
        roles_created = []
        roles_updated = []
        roles_failed = []
        
        for level, role_name in LEVEL_ROLES.items():
            # Couleur en fonction du niveau (du bleu clair au bleu foncé)
            if level == 1:
                color = 0xAED6F1  # Bleu très clair
            elif level == 5:
                color = 0x85C1E9  # Bleu clair
            elif level == 10:
                color = 0x5DADE2  # Bleu moyen
            elif level == 20:
                color = 0x3498DB  # Bleu
            elif level == 30:
                color = 0x2874A6  # Bleu foncé
            else:
                color = 0x3498DB  # Bleu par défaut
            
            # Vérifier si le rôle existe déjà
            existing_role = discord.utils.get(guild.roles, name=role_name)
            
            if existing_role:
                # Mettre à jour le rôle existant
                try:
                    await existing_role.edit(
                        colour=discord.Colour(color),
                        hoist=True,
                        mentionable=False,
                        reason="Mise à jour des rôles de niveau"
                    )
                    roles_updated.append(f"✅ **{role_name}** (Niveau {level}, mis à jour)")
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour du rôle '{role_name}': {e}")
                    roles_failed.append(f"❌ **{role_name}** (Niveau {level}, erreur: {e})")
            else:
                # Créer le nouveau rôle
                try:
                    permissions = discord.Permissions()
                    # Rôle normal avec permissions de base
                    permissions.update(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        add_reactions=True,
                        connect=True,
                        speak=True
                    )
                    
                    new_role = await guild.create_role(
                        name=role_name,
                        colour=discord.Colour(color),
                        permissions=permissions,
                        hoist=True,
                        mentionable=False,
                        reason="Création des rôles de niveau"
                    )
                    roles_created.append(f"✅ **{role_name}** (Niveau {level}, créé)")
                except Exception as e:
                    logger.error(f"Erreur lors de la création du rôle '{role_name}': {e}")
                    roles_failed.append(f"❌ **{role_name}** (Niveau {level}, erreur: {e})")
        
        # Mettre à jour le message de statut
        await status_message.edit(content="✅ Configuration des rôles de niveau terminée !")
        
        # Créer un embed pour afficher les résultats
        embed = discord.Embed(
            title="🔧 Configuration des Rôles de Niveau",
            description="Résultat de la création des rôles de niveau pour le système d'XP",
            color=0xffaadd
        )
        
        if roles_created:
            embed.add_field(
                name="Rôles créés",
                value="\n".join(roles_created),
                inline=False
            )
        
        if roles_updated:
            embed.add_field(
                name="Rôles mis à jour",
                value="\n".join(roles_updated),
                inline=False
            )
        
        if roles_failed:
            embed.add_field(
                name="Erreurs",
                value="\n".join(roles_failed),
                inline=False
            )
        
        # Ajouter des instructions
        embed.add_field(
            name="📋 Système d'XP",
            value=(
                "Les membres gagnent automatiquement de l'XP en discutant sur le serveur.\n"
                "• Le gain d'XP est de 15-25 points par message\n"
                "• Un délai de 60 secondes entre chaque gain d'XP\n"
                "• Les rôles sont attribués automatiquement aux niveaux 1, 5, 10, 20 et 30\n"
                "• Les membres peuvent voir leur niveau avec `!rank`\n"
                "• Le classement est disponible avec `!leaderboard`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["tableau", "stats"])
    async def dashboard(self, ctx):
        """Affiche le top 10 des membres avec le plus d'XP."""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.levels_data:
            await ctx.send("Aucune donnée de niveau n'est disponible pour ce serveur.")
            return
        
        # Trier les membres par XP
        sorted_members = sorted(
            self.levels_data[guild_id].items(),
            key=lambda x: x[1].get("xp", 0),
            reverse=True
        )[:10]  # Prendre les 10 premiers
        
        embed = discord.Embed(
            title="🏆 Top 10 des Membres",
            description="Les membres avec le plus d'XP sur le serveur",
            color=0xffaadd
        )
        
        for rank, (member_id, data) in enumerate(sorted_members, 1):
            member = ctx.guild.get_member(int(member_id))
            if member:
                xp = data.get("xp", 0)
                level = calculate_level(xp)
                
                # Emoji pour les 3 premiers
                rank_emoji = "👑" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"**{rank}.**"
                
                embed.add_field(
                    name=f"{rank_emoji} {member.display_name}",
                    value=f"Niveau: **{level}**\nXP: **{xp:,}**",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(aliases=["aide_niveaux", "aide_xp", "xp_help"])
    async def help_levels(self, ctx):
        """Affiche l'aide pour le système de niveaux."""
        embed = discord.Embed(
            title="🌟 Système de Niveaux et XP",
            description="Guide du système d'expérience et de niveaux sur le serveur",
            color=0xffaadd
        )
        
        embed.add_field(
            name="🔰 Comment gagner de l'XP",
            value=(
                "• Envoyer des messages dans le serveur (15-25 XP par message)\n"
                "• L'XP est attribuée une fois toutes les 60 secondes\n"
                "• Les commandes et les messages de bots ne donnent pas d'XP"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Commandes",
            value=(
                "• `!rank` - Voir ton niveau, XP et progression\n"
                "• `!rank @membre` - Voir le niveau d'un autre membre\n"
                "• `!leaderboard` - Voir le classement des membres les plus actifs"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏅 Rôles de niveau",
            value=(
                "Les rôles sont automatiquement attribués quand tu atteins certains niveaux:\n"
                "• **Nini Nouveau** — Niveau 1\n"
                "• **Nini Curieux** — Niveau 5\n"
                "• **Nini Actif** — Niveau 10\n"
                "• **Nini Confirmé** — Niveau 20\n"
                "• **Nini Légende** — Niveau 30"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📈 Progression",
            value=(
                "• Chaque niveau demande de plus en plus d'XP\n"
                "• La formule est: `XP = 5 × (niveau²) + 50 × niveau + 100`\n"
                "• Exemple: Niveau 5 = 425 XP, Niveau 10 = 1100 XP"
            ),
            inline=False
        )
        
        embed.set_footer(text="✨ Reste actif et monte en niveau ! ✨")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Fonction d'installation du cog."""
    await bot.add_cog(Levels(bot))