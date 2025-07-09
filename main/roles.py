"""
Module de gestion des rôles pour le Bot Ninis.
Ce module permet de configurer et gérer les rôles-réaction.
"""

import discord
import logging
import asyncio
import json
import os
from discord.ext import commands

# Configuration du logger
logger = logging.getLogger('ninis_bot')

# Structure des rôles-réaction
REACTION_ROLES = {
    "Sexe": {
        "👦": {"name": "Garçon", "color": 0x3498DB},  # Bleu
        "👧": {"name": "Fille", "color": 0xFF69B4},   # Rose
    },
    "Âge": {
        "🔞": {"name": "Majeur", "color": 0x9B59B6},  # Violet
        "🧸": {"name": "Mineur", "color": 0x2ECC71},  # Vert
    }
}

class Roles(commands.Cog):
    """Commandes pour la gestion des rôles et des rôles-réaction."""

    def __init__(self, bot):
        self.bot = bot
        self.role_message_ids = {}
        # Charger les IDs des messages de rôle s'ils existent
        self.load_role_messages()

    def load_role_messages(self):
        """Charge les IDs des messages de rôle-réaction depuis un fichier."""
        try:
            if os.path.exists('role_messages.json'):
                with open('role_messages.json', 'r') as f:
                    self.role_message_ids = json.load(f)
                    logger.info(f"Données de rôles-réaction chargées: {len(self.role_message_ids)} catégories")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données de rôles-réaction: {e}")
            self.role_message_ids = {}

    def save_role_messages(self):
        """Sauvegarde les IDs des messages de rôle-réaction dans un fichier."""
        try:
            with open('role_messages.json', 'w') as f:
                json.dump(self.role_message_ids, f, indent=4)
                logger.info(f"Données de rôles-réaction sauvegardées: {len(self.role_message_ids)} catégories")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données de rôles-réaction: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gère l'ajout de réactions pour attribuer des rôles."""
        # Ignore les réactions du bot
        if payload.user_id == self.bot.user.id:
            return

        # Vérifie si le message est un message de rôle-réaction
        message_id_str = str(payload.message_id)
        
        # Recherche la catégorie correspondant au message
        target_category = None
        for cat, data in self.role_message_ids.items():
            if data.get('message_id') == message_id_str:
                target_category = cat
                break
                
        if not target_category:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji = str(payload.emoji)
        
        # Correction pour Unicode: Si la catégorie a un caractère accentué
        if target_category == "\u00c2ge":
            target_category = "Âge"
        
        # Vérifie si l'emoji correspond à un rôle dans cette catégorie
        if emoji in REACTION_ROLES.get(target_category, {}):
            role_info = REACTION_ROLES[target_category][emoji]
            role_name = role_info["name"]
            
            # Vérifie si le rôle existe
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                # Crée le rôle s'il n'existe pas
                role = await guild.create_role(
                    name=role_name,
                    color=discord.Colour(role_info["color"]),
                    mentionable=True,
                    reason=f"Rôle-réaction créé pour la catégorie {target_category}"
                )
                logger.info(f"Rôle '{role_name}' créé pour la catégorie {target_category}")
            
            # Si le membre a déjà le rôle, on ne fait rien
            if role in member.roles:
                logger.info(f"{member.name} a déjà le rôle {role_name}")
            else:
                # Enlève tous les autres rôles de la même catégorie d'abord
                for other_emoji, other_role_info in REACTION_ROLES[target_category].items():
                    other_role_name = other_role_info["name"]
                    other_role = discord.utils.get(guild.roles, name=other_role_name)
                    
                    if other_role and other_role in member.roles:
                        await member.remove_roles(other_role, reason=f"Changement de rôle dans la catégorie {target_category}")
                        logger.info(f"Rôle '{other_role_name}' retiré de {member.name}")
                
                # Attribue le nouveau rôle
                await member.add_roles(role, reason=f"Rôle-réaction ({target_category})")
                logger.info(f"Rôle '{role_name}' attribué à {member.name}")
                
                # Envoie un message privé de confirmation
                try:
                    await member.send(f"✅ Tu as reçu le rôle **{role_name}** dans la catégorie **{target_category}**")
                except discord.Forbidden:
                    logger.error(f"Impossible d'envoyer un DM à {member.name}: Messages privés désactivés")
        
        # Retire la réaction de l'utilisateur pour garder le message propre
        channel = guild.get_channel(payload.channel_id)
        if channel:
            try:
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, member)
                logger.info(f"Réaction retirée dans le canal: {channel.name}, emoji: {emoji}")
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de la réaction: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Gère la suppression de réactions pour retirer des rôles.
        Cette méthode n'est pas utilisée car on retire automatiquement la réaction de l'utilisateur."""
        pass

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_role_reactions(self, ctx):
        """Configure le système de rôles-réaction avec les catégories Sexe et Âge."""
        # Trouver le salon de rôles
        roles_channel = discord.utils.get(ctx.guild.text_channels, name="✨・rôles")
        
        if not roles_channel:
            # Si le salon n'existe pas, demander à l'utilisateur s'il veut le créer
            await ctx.send("❓ Le salon '✨・rôles' n'existe pas. Voulez-vous le créer ? (oui/non)")
            
            try:
                def check(message):
                    return message.author == ctx.author and message.channel == ctx.channel and \
                           message.content.lower() in ["oui", "non", "yes", "no"]
                
                response = await self.bot.wait_for('message', check=check, timeout=60.0)
                
                if response.content.lower() in ["oui", "yes"]:
                    # Créer le salon
                    overwrites = {
                        ctx.guild.default_role: discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=False,
                            add_reactions=True
                        ),
                        ctx.guild.me: discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=True,
                            manage_messages=True,
                            add_reactions=True
                        )
                    }
                    
                    # Chercher la catégorie Bienvenue ou similaire
                    welcome_category = None
                    for category in ctx.guild.categories:
                        if "bienvenue" in category.name.lower() or "welcome" in category.name.lower():
                            welcome_category = category
                            break
                    
                    if not welcome_category:
                        welcome_category = await ctx.guild.create_category(name="୨୧・Bienvenue")
                        
                    roles_channel = await ctx.guild.create_text_channel(
                        name="✨・rôles",
                        category=welcome_category,
                        overwrites=overwrites,
                        topic="Choisis tes rôles en cliquant sur les réactions"
                    )
                    
                    await ctx.send(f"✅ Salon {roles_channel.mention} créé avec succès.")
                else:
                    return await ctx.send("❌ Configuration annulée. Veuillez créer un salon '✨・rôles' manuellement.")
            except asyncio.TimeoutError:
                return await ctx.send("⏱️ Délai d'attente expiré. Configuration annulée.")
        
        # Vérifier si les rôles existent déjà, sinon les créer
        for category, roles in REACTION_ROLES.items():
            for emoji, role_info in roles.items():
                role_name = role_info["name"]
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                
                if not role:
                    await ctx.guild.create_role(
                        name=role_name,
                        color=discord.Colour(role_info["color"]),
                        mentionable=True,
                        reason=f"Rôle pour la catégorie {category}"
                    )
                    logger.info(f"Rôle '{role_name}' créé pour la catégorie {category}")
        
        await ctx.send("⏳ Configuration des messages de rôles-réaction en cours...")
        
        # Créer ou mettre à jour les messages de rôles-réaction par catégorie
        for category, roles in REACTION_ROLES.items():
            # Créer l'embed pour cette catégorie
            embed = discord.Embed(
                title=f"🏷️ Choisis ton rôle : {category}",
                description=f"Clique sur une réaction ci-dessous pour choisir ton rôle dans la catégorie **{category}**.\n\n"
                            f"**IMPORTANT :** Tu ne peux choisir qu'un SEUL rôle dans cette catégorie. "
                            f"Ton choix précédent sera automatiquement remplacé.\n\n",
                color=discord.Colour.gold()
            )
            
            # Ajouter les descriptions de rôles
            for emoji, role_info in roles.items():
                embed.description += f"{emoji} : **{role_info['name']}**\n"
            
            embed.set_footer(text="Ton choix est exclusif : un seul rôle par catégorie.")
            
            # Vérifier si un message existe déjà pour cette catégorie
            message_id = self.role_message_ids.get(category, {}).get('message_id')
            message = None
            
            if message_id:
                try:
                    message = await roles_channel.fetch_message(int(message_id))
                    # Mettre à jour le message existant
                    await message.edit(embed=embed)
                    await message.clear_reactions()
                    logger.info(f"Message de rôles-réaction existant mis à jour pour la catégorie {category}")
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    message = None
            
            # Si aucun message n'existe ou n'a pu être récupéré, en créer un nouveau
            if not message:
                message = await roles_channel.send(embed=embed)
                logger.info(f"Nouveau message de rôles-réaction créé pour la catégorie {category}")
                
                # Sauvegarder l'ID du message
                if category not in self.role_message_ids:
                    self.role_message_ids[category] = {}
                self.role_message_ids[category]['message_id'] = str(message.id)
                self.save_role_messages()
            
            # Ajouter les réactions
            for emoji in roles.keys():
                await message.add_reaction(emoji)
                await asyncio.sleep(0.5)  # Petite pause pour éviter le rate limiting
        
        await ctx.send("✅ Configuration des rôles-réaction terminée !")
        await ctx.send(f"👉 Les membres peuvent désormais choisir leurs rôles dans {roles_channel.mention}")

async def setup(bot):
    """Installation du cog de gestion des rôles."""
    await bot.add_cog(Roles(bot))
    logger.info("Cog 'roles' chargé avec succès")