"""
Setup cog for configuring the Ninis server.
"""
import asyncio
import logging
import discord
from discord.ext import commands
import config
import random
import string
import json
import os
from datetime import datetime

# Set up logging
logger = logging.getLogger('ninis_bot')

class Setup(commands.Cog):
    """Commands for setting up and managing server structure."""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Attribue automatiquement le rôle 'Non vérifié' aux nouveaux membres."""
        guild = member.guild
        
        # Trouver le rôle "Non vérifié"
        unverified_role = discord.utils.get(guild.roles, name="Non vérifié")
        
        if unverified_role:
            try:
                await member.add_roles(unverified_role)
                logger.info(f"Rôle 'Non vérifié' attribué automatiquement à {member.name}")
                
                # Envoyer un message de bienvenue au nouveau membre
                try:
                    welcome_dm = discord.Embed(
                        title="✨ Bienvenue sur Ninis ! ✨",
                        description=f"Bonjour {member.mention} !\n\n"
                                   f"Pour accéder à tous les salons du serveur, tu dois d'abord accepter le règlement en cliquant sur la réaction ✅ dans le salon <#📖・règlement>.",
                        color=discord.Colour.pink()
                    )
                    welcome_dm.set_footer(text="✧ Ninis • Made with 💖")
                    
                    await member.send(embed=welcome_dm)
                except Exception as e:
                    logger.error(f"Impossible d'envoyer un DM à {member.name}: {e}")
            except Exception as e:
                logger.error(f"Erreur lors de l'attribution du rôle 'Non vérifié' à {member.name}: {e}")
        
        # Chargement des données des règles
        try:
            import json
            import os
            
            if os.path.exists('rules_data.json'):
                with open('rules_data.json', 'r') as f:
                    rules_data = json.load(f)
                    
                    # Mise à jour des variables globales
                    config.RULES_MESSAGE_ID = rules_data.get("rules_message_id")
                    config.RULES_CHANNEL_ID = rules_data.get("rules_channel_id")
                    
                    logger.info(f"Données de règlement chargées: Message ID: {config.RULES_MESSAGE_ID}, Canal ID: {config.RULES_CHANNEL_ID}")
            else:
                logger.info("Aucun fichier rules_data.json trouvé, les IDs de règlement seront définis lors de la première utilisation")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données de règlement: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_ninis(self, ctx):
        """Set up the Ninis server with predefined roles, categories and channels."""
        guild = ctx.guild
        
        # Show setup confirmation message
        confirm_embed = discord.Embed(
            title="Configuration du serveur Ninis",
            description="Ce processus va créer tous les rôles, catégories et salons nécessaires pour le serveur Ninis.\n"
                        "**Attention:** Cette action va potentiellement créer de nombreux éléments sur ton serveur.",
            color=discord.Colour.yellow()
        )
        confirm_embed.add_field(name="Continuer ?", value="Réponds avec `oui` pour continuer ou `non` pour annuler.")
        
        await ctx.send(embed=confirm_embed)
        
        # Wait for confirmation
        try:
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel and \
                       message.content.lower() in ["oui", "non"]
            
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if response.content.lower() == "non":
                await ctx.send("❌ Configuration annulée.")
                return
            
        except asyncio.TimeoutError:
            await ctx.send("⏱️ Délai d'attente expiré. Configuration annulée.")
            return
        
        # Start setup with progress message
        progress_message = await ctx.send("⏳ Configuration en cours...")
        
        # Setup progress tracking
        total_steps = len(config.ROLES) + len(config.CHANNELS)
        current_step = 0
        
        async def update_progress():
            nonlocal current_step
            current_step += 1
            progress = int((current_step / total_steps) * 100)
            await progress_message.edit(content=f"⏳ Configuration en cours... ({progress}% terminé)")
        
        # Create roles
        try:
            await self._create_roles(guild, update_progress)
        except Exception as e:
            logger.error(f"Erreur lors de la création des rôles: {e}")
            await ctx.send(f"❌ Erreur lors de la création des rôles: {e}")
            return
        
        # Create channels
        try:
            await self._create_channels(guild, update_progress)
        except Exception as e:
            logger.error(f"Erreur lors de la création des salons: {e}")
            await ctx.send(f"❌ Erreur lors de la création des salons: {e}")
            return
        
        # Finish setup
        await progress_message.edit(content="✅ Configuration terminée avec succès !")
        
        # Send success embed with details
        success_embed = discord.Embed(
            title="✨ Serveur Ninis configuré !",
            description="Tous les éléments du serveur ont été créés avec succès.",
            color=discord.Colour.green()
        )
        success_embed.add_field(
            name="Éléments créés",
            value=f"• {len(config.ROLES)} rôles\n• {sum(1 for cat in config.CHANNELS for _ in config.CHANNELS[cat])} salons\n• {len(config.CHANNELS)} catégories",
            inline=False
        )
        success_embed.add_field(
            name="Prochaines étapes",
            value="1. Vérifiez que tous les salons sont correctement configurés\n"
                 "2. Personnalisez les permissions des rôles si nécessaire\n"
                 "3. Ajoutez des emojis personnalisés pour améliorer l'expérience",
            inline=False
        )
        success_embed.set_footer(text="✧ Merci d'utiliser le bot Ninis !")
        
        await ctx.send(embed=success_embed)
    
    async def _create_roles(self, guild, update_callback):
        """Create all the roles defined in the config."""
        # Check for existing roles to avoid duplicates
        existing_roles = {role.name: role for role in guild.roles}
        
        for role_name, role_data in config.ROLES.items():
            # Skip if role already exists
            if role_name in existing_roles:
                logger.info(f"Le rôle '{role_name}' existe déjà, passage au suivant.")
                await update_callback()
                continue
            
            # Create role with proper permissions
            try:
                permissions = discord.Permissions()
                if role_data["permissions"]:
                    # Staff-level permissions
                    permissions.update(
                        kick_members=True,
                        ban_members=True,
                        manage_messages=True,
                        mute_members=True,
                        deafen_members=True,
                        move_members=True,
                        manage_nicknames=True,
                        manage_channels=True if role_name == "✦ ꒰ Nini Queen ꒱" else False,
                        administrator=True if role_name == "✦ ꒰ Nini Queen ꒱" else False
                    )
                
                await guild.create_role(
                    name=role_name,
                    colour=discord.Colour(role_data["color"]),
                    permissions=permissions,
                    hoist=True,  # Separate role in member list
                    mentionable=True,
                    reason="Ninis server setup"
                )
                logger.info(f"Rôle '{role_name}' créé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la création du rôle '{role_name}': {e}")
                raise
            
            # Update progress
            await update_callback()
            
            # Add a small delay to avoid rate limits
            await asyncio.sleep(0.5)
    
    async def _create_channels(self, guild, update_callback):
        """Create all categories and channels defined in the config."""
        # Get existing categories and channels to avoid duplicates
        existing_categories = {category.name: category for category in guild.categories}
        
        # Get roles for permissions
        roles = {role.name: role for role in guild.roles}
        
        # Create each category and its channels
        for category_name, channels in config.CHANNELS.items():
            # Create or get category
            if category_name in existing_categories:
                category = existing_categories[category_name]
                logger.info(f"La catégorie '{category_name}' existe déjà, utilisation de celle-ci.")
            else:
                # Set up permissions for categories
                overwrites = {}
                everyone_role = guild.default_role
                
                # Pour la catégorie Staff, seuls les membres du staff peuvent voir
                if "Staff" in category_name:
                    # Make staff-only channels private
                    overwrites[everyone_role] = discord.PermissionOverwrite(read_messages=False)
                    
                    if "✦ ꒰ Nini Queen ꒱" in roles:
                        overwrites[roles["✦ ꒰ Nini Queen ꒱"]] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True)
                    
                    if "♡ Staff" in roles:
                        overwrites[roles["♡ Staff"]] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True)
                # Pour toutes les autres catégories, seuls les membres (vérifiés) peuvent voir
                else:
                    # Par défaut, tout le monde ne peut pas voir
                    overwrites[everyone_role] = discord.PermissionOverwrite(read_messages=False)
                    
                    # Les admins et staff peuvent tout voir
                    if "✦ ꒰ Nini Queen ꒱" in roles:
                        overwrites[roles["✦ ꒰ Nini Queen ꒱"]] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True)
                    
                    if "♡ Staff" in roles:
                        overwrites[roles["♡ Staff"]] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True)
                    
                    # Les membres vérifiés peuvent voir
                    if "Membre" in roles:
                        overwrites[roles["Membre"]] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True)
                        
                    # Ceux qui ont le rôle "Non vérifié" ne peuvent pas voir
                    if "Non vérifié" in roles:
                        overwrites[roles["Non vérifié"]] = discord.PermissionOverwrite(
                            read_messages=False)
                
                category = await guild.create_category(name=category_name, overwrites=overwrites)
                logger.info(f"Catégorie '{category_name}' créée avec succès")
            
            # Create channels in this category
            for channel_name, channel_data in channels.items():
                # Check if channel already exists in this category
                existing_channel = discord.utils.get(
                    category.channels, 
                    name=channel_name.replace("・", "-")  # Discord normalizes the dot
                )
                
                if existing_channel:
                    logger.info(f"Le salon '{channel_name}' existe déjà dans '{category_name}', passage au suivant")
                    continue
                
                try:
                    # Create the channel based on its type
                    channel = None
                    # Configuration personnalisée pour le canal des règles
                    if channel_name == "📖・règlement":
                        # Pour le salon des règles, tout le monde peut le voir (y compris les membres non vérifiés)
                        rules_overwrites = {}
                        everyone_role = guild.default_role
                        
                        # Tout le monde peut voir le règlement
                        rules_overwrites[everyone_role] = discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=False,  # Mais personne ne peut écrire
                            read_message_history=True,
                            add_reactions=True
                        )
                        
                        # Staff avec permissions complètes
                        if "✦ ꒰ Nini Queen ꒱" in roles:
                            rules_overwrites[roles["✦ ꒰ Nini Queen ꒱"]] = discord.PermissionOverwrite(
                                read_messages=True, 
                                send_messages=True,
                                manage_messages=True
                            )
                        
                        if "♡ Staff" in roles:
                            rules_overwrites[roles["♡ Staff"]] = discord.PermissionOverwrite(
                                read_messages=True, 
                                send_messages=True,
                                manage_messages=True
                            )
                        
                        # Création du salon
                        channel = await guild.create_text_channel(
                            name=channel_name,
                            category=category,
                            overwrites=rules_overwrites
                        )
                        logger.info(f"Salon des règles '{channel_name}' créé avec permissions spéciales")
                    
                    elif channel_data.get("type") == "voice":
                        channel = await guild.create_voice_channel(
                            name=channel_name,
                            category=category
                        )
                    else:  # Default to text channel
                        channel = await guild.create_text_channel(
                            name=channel_name,
                            category=category
                        )
                    
                    # Send default content if specified
                    if "content" in channel_data and channel_data["content"] and isinstance(channel, discord.TextChannel):
                        await channel.send(channel_data["content"])
                    
                    logger.info(f"Salon '{channel_name}' créé avec succès dans '{category_name}'")
                except Exception as e:
                    logger.error(f"Erreur lors de la création du salon '{channel_name}': {e}")
                    raise
                
                # Add a small delay to avoid rate limits
                await asyncio.sleep(0.5)
            
            # Update progress after each category is done
            await update_callback()
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_role_menu(self, ctx, channel_id=None):
        """Create or update a role selection menu in the specified channel."""
        # If no channel specified, use the current one or try to find the roles channel
        if channel_id is None:
            # Try to find the roles channel by name
            roles_channel = discord.utils.get(ctx.guild.text_channels, name="✨・rôles")
            if roles_channel:
                channel = roles_channel
                logger.info(f"Canal de rôles trouvé automatiquement: {channel.name}")
            else:
                channel = ctx.channel
                logger.info(f"Utilisation du canal actuel pour les rôles: {channel.name}")
        else:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                logger.info(f"Canal de rôles spécifié manuellement: {channel.name}")
            except (ValueError, discord.NotFound, discord.Forbidden):
                await ctx.send("❌ Salon introuvable. Vérifie l'ID et mes permissions.")
                return
        
        try:
            # Purge existing messages
            await channel.purge(limit=10)
            logger.info(f"Canal '{channel.name}' nettoyé pour le nouveau menu de rôles")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du canal '{channel.name}': {e}")
            await ctx.send(f"⚠️ Je n'ai pas pu nettoyer le canal. Erreur: {e}")
        
        # Create the role menu embed
        embed = discord.Embed(
            title="✨ Sélection de rôles",
            description="Réagis à ce message pour obtenir les rôles correspondants:",
            color=discord.Colour.pink()
        )
        
        # Add role descriptions
        role_descriptions = [
            ("🌸", "Créatif.ve", "Pour les artistes et créateurs de tout type"),
            ("✨", "Gamer", "Pour les passionnés de jeux vidéo"),
            ("☁", "Chillax", "Pour les amoureux de la détente et du calme"),
            ("⋆", "Baby Nini", "Pour les nouveaux membres de la communauté")
        ]
        
        for emoji, role_name, description in role_descriptions:
            embed.add_field(
                name=f"{emoji} {role_name}",
                value=description,
                inline=False
            )
        
        # Send the embed
        menu_message = await channel.send(embed=embed)
        
        # Store the menu message ID in the bot's session data for future reference
        if not hasattr(self, 'role_menu_message_ids'):
            self.role_menu_message_ids = {}
        self.role_menu_message_ids[channel.id] = menu_message.id
        logger.info(f"ID du message du menu de rôles enregistré: {menu_message.id} dans le canal {channel.id}")
        
        # Add reactions
        for emoji, _, _ in role_descriptions:
            await menu_message.add_reaction(emoji)
            logger.info(f"Réaction {emoji} ajoutée au menu de rôles")
        
        await ctx.send(f"✅ Menu de rôles créé dans <#{channel.id}>")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle adding roles based on reactions."""
        # Skip if it's the bot's own reaction
        if payload.user_id == self.bot.user.id:
            return
        
        # Get the guild
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        # Get the channel
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return
            
        # Check if it's the rules channel
        if channel.name == "📖・règlement" and str(payload.emoji) == "✅":
            # Handle rules acceptance
            member = guild.get_member(payload.user_id)
            if not member:
                return
                
            # Get unverified role (to remove)
            unverified_role = discord.utils.get(guild.roles, name="Non vérifié")
                
            # Get or create member role (to add)
            member_role = discord.utils.get(guild.roles, name="Membre")
            if not member_role:
                # Role doesn't exist, create it
                try:
                    permissions = discord.Permissions()
                    permissions.update(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        add_reactions=True,
                        connect=True,
                        speak=True
                    )
                    
                    member_role = await guild.create_role(
                        name="Membre",
                        colour=discord.Colour(0x3498DB),  # Bleu
                        permissions=permissions,
                        hoist=True,
                        mentionable=True,
                        reason="Rôle pour les membres ayant accepté le règlement"
                    )
                    logger.info(f"Rôle 'Membre' créé pour les membres vérifiés")
                except Exception as e:
                    logger.error(f"Erreur lors de la création du rôle 'Membre': {e}")
                    return
            
            # Process roles
            try:
                # Remove unverified role
                if unverified_role and unverified_role in member.roles:
                    await member.remove_roles(unverified_role)
                    logger.info(f"Rôle 'Non vérifié' retiré de {member.name}")
                
                # Assign member role
                await member.add_roles(member_role)
                logger.info(f"Rôle 'Membre' assigné à {member.name} après acceptation du règlement")
                
                # Send welcome DM to the member
                try:
                    welcome_dm = discord.Embed(
                        title="✨ Bienvenue sur Ninis ! ✨",
                        description=f"Merci d'avoir accepté le règlement, {member.name} !\n\n"
                                    f"Tu as maintenant accès à tous les salons du serveur.\n"
                                    f"N'hésite pas à choisir tes rôles dans le salon des rôles pour personnaliser ton expérience !",
                        color=discord.Colour.pink()
                    )
                    welcome_dm.set_footer(text="✧ Ninis • Made with 💖")
                    
                    await member.send(embed=welcome_dm)
                except Exception as e:
                    logger.error(f"Impossible d'envoyer un DM à {member.name}: {e}")
                
            except discord.Forbidden:
                logger.error(f"Permissions insuffisantes pour gérer les rôles")
            except Exception as e:
                logger.error(f"Erreur lors de la gestion des rôles: {e}")
            
            return
        
        # Pour les autres canaux, gérer les réactions de rôle normales
        # Log le canal actuel pour le débogage
        logger.info(f"Réaction reçue dans le canal: {channel.name}, emoji: {str(payload.emoji)}")
        
        # Map emojis to role names
        emoji_to_role = {
            "🌸": "🌸 Créatif.ve",
            "✨": "✨ Gamer",
            "☁": "☁ Chillax",
            "⋆": "⋆ Baby Nini"
        }
        
        # Check if the emoji is one we're tracking
        emoji = str(payload.emoji)
        if emoji not in emoji_to_role:
            logger.info(f"Emoji non reconnu: {emoji}")
            return
        
        # Get the role based on emoji
        role_name = emoji_to_role[emoji]
        role = discord.utils.get(guild.roles, name=role_name)
        
        if not role:
            logger.warning(f"Rôle '{role_name}' introuvable sur le serveur")
            # Parcourir tous les rôles du serveur pour voir ceux qui existent
            existing_roles = [r.name for r in guild.roles]
            logger.info(f"Rôles existants: {existing_roles}")
            return
        
        # Get the member and assign the role
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        try:
            await member.add_roles(role)
            logger.info(f"Added role '{role_name}' to {member.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to assign role '{role_name}'")
        except Exception as e:
            logger.error(f"Error assigning role: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle removing roles based on reaction removal."""
        # Skip if it's the bot's own reaction
        if payload.user_id == self.bot.user.id:
            return
        
        # Get the guild
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        # Get the channel
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return
            
        # Log for debugging
        logger.info(f"Réaction retirée dans le canal: {channel.name}, emoji: {str(payload.emoji)}")
        
        # We don't remove the verified role when reaction is removed from rules
        if channel.name == "📖・règlement" and str(payload.emoji) == "✅":
            return
        
        # Map emojis to role names
        emoji_to_role = {
            "🌸": "🌸 Créatif.ve",
            "✨": "✨ Gamer",
            "☁": "☁ Chillax",
            "⋆": "⋆ Baby Nini"
        }
        
        # Check if the emoji is one we're tracking
        emoji = str(payload.emoji)
        if emoji not in emoji_to_role:
            logger.info(f"Emoji non reconnu (retrait): {emoji}")
            return
        
        # Get the role based on emoji
        role_name = emoji_to_role[emoji]
        role = discord.utils.get(guild.roles, name=role_name)
        
        if not role:
            logger.warning(f"Rôle '{role_name}' introuvable sur le serveur (retrait)")
            return
        
        # Get the member and remove the role
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        try:
            await member.remove_roles(role)
            logger.info(f"Removed role '{role_name}' from {member.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to remove role '{role_name}'")
        except Exception as e:
            logger.error(f"Error removing role: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_verification(self, ctx):
        """Configure le système complet de vérification avec rôles et salons nécessaires."""
        guild = ctx.guild
        status_message = await ctx.send("⏳ Configuration du système complet de vérification...")
        
        # Étape 1 : Créer ou vérifier les rôles nécessaires
        await status_message.edit(content=f"{status_message.content}\n\n**Étape 1/4 : Configuration des rôles**")
        
        # Vérifier et créer les rôles Membre et Non vérifié
        roles = {role.name: role for role in guild.roles}
        
        # Créer le rôle Non vérifié s'il n'existe pas
        if "Non vérifié" not in roles:
            try:
                unverified_role = await guild.create_role(
                    name="Non vérifié",
                    colour=discord.Colour(0x95A5A6),  # Gris
                    hoist=True,       # Séparé dans la liste des membres
                    mentionable=True,
                    reason="Rôle pour les nouveaux membres non vérifiés"
                )
                await status_message.edit(content=f"{status_message.content}\n✅ Rôle 'Non vérifié' créé")
            except Exception as e:
                logger.error(f"Erreur lors de la création du rôle 'Non vérifié': {e}")
                await ctx.send(f"❌ Erreur lors de la création du rôle 'Non vérifié': {e}")
                return False
        else:
            unverified_role = roles["Non vérifié"]
            await status_message.edit(content=f"{status_message.content}\nℹ️ Rôle 'Non vérifié' déjà existant")
        
        # Créer le rôle Membre s'il n'existe pas
        if "Membre" not in roles:
            try:
                # Créer le rôle avec les permissions de base pour un membre normal
                permissions = discord.Permissions()
                permissions.update(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    add_reactions=True,
                    connect=True,
                    speak=True
                )
                
                member_role = await guild.create_role(
                    name="Membre",
                    colour=discord.Colour(0x3498DB),  # Bleu
                    permissions=permissions,
                    hoist=True,
                    mentionable=True,
                    reason="Rôle pour les membres ayant accepté le règlement"
                )
                await status_message.edit(content=f"{status_message.content}\n✅ Rôle 'Membre' créé")
            except Exception as e:
                logger.error(f"Erreur lors de la création du rôle 'Membre': {e}")
                await ctx.send(f"❌ Erreur lors de la création du rôle 'Membre': {e}")
                return False
        else:
            member_role = roles["Membre"]
            await status_message.edit(content=f"{status_message.content}\nℹ️ Rôle 'Membre' déjà existant")
        
        # Récupérer les autres rôles d'administration existants
        admin_role = discord.utils.get(guild.roles, name="✦ ꒰ Nini Queen ꒱") or discord.utils.get(guild.roles, name="Administrateur")
        mod_role = discord.utils.get(guild.roles, name="♡ Staff") or discord.utils.get(guild.roles, name="Modérateur")
        
        # Étape 2 : Créer ou configurer la catégorie d'accueil
        await status_message.edit(content=f"{status_message.content}\n\n**Étape 2/4 : Configuration de la catégorie d'accueil**")
        
        # Créer ou trouver la catégorie Bienvenue
        welcome_category = discord.utils.get(guild.categories, name="୨୧・Bienvenue")
        category_action = "mise à jour"
        
        # Définir les permissions de base pour la catégorie
        overwrites = {
            # Par défaut, personne ne voit la catégorie
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            
            # Le bot peut voir et gérer la catégorie
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            ),
            
            # Les nouveaux membres non vérifiés peuvent voir uniquement cette catégorie
            unverified_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                read_message_history=True,
                add_reactions=True
            ),
            
            # Les membres vérifiés peuvent aussi voir cette catégorie
            member_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True,
                add_reactions=True
            )
        }
        
        # Ajouter les permissions pour les administrateurs et modérateurs s'ils existent
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True
            )
        
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True
            )
        
        # Créer la catégorie si elle n'existe pas
        if not welcome_category:
            try:
                welcome_category = await guild.create_category(
                    name="୨୧・Bienvenue",
                    overwrites=overwrites,
                    position=0  # En haut du serveur
                )
                category_action = "créée"
            except Exception as e:
                logger.error(f"Erreur lors de la création de la catégorie Bienvenue: {e}")
                await ctx.send(f"❌ Erreur lors de la création de la catégorie Bienvenue: {e}")
                return False
        else:
            # Mettre à jour les permissions de la catégorie existante
            try:
                await welcome_category.edit(overwrites=overwrites)
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des permissions de la catégorie: {e}")
                await ctx.send(f"❌ Erreur lors de la mise à jour des permissions de la catégorie: {e}")
        
        await status_message.edit(content=f"{status_message.content}\n✅ Catégorie '୨୧・Bienvenue' {category_action}")
        
        # Étape 3 : Créer ou configurer les salons nécessaires
        await status_message.edit(content=f"{status_message.content}\n\n**Étape 3/4 : Configuration des salons essentiels**")
        
        # Créer ou configurer le salon de règlement
        rules_channel = discord.utils.get(guild.text_channels, name="📖・règlement")
        if not rules_channel:
            try:
                # Les overwrites pour le salon sont différents - tout le monde peut voir le règlement
                rules_overwrites = dict(overwrites)  # Copier les permissions de base
                
                # Le salon des règles est accessible aux non-vérifiés mais ils ne peuvent pas écrire
                rules_overwrites[unverified_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True,
                    add_reactions=True
                )
                
                rules_channel = await guild.create_text_channel(
                    name="📖・règlement",
                    category=welcome_category,
                    overwrites=rules_overwrites,
                    position=0,  # Premier salon de la catégorie
                    topic="Règlement du serveur - Réagis avec ✅ pour accepter"
                )
                await status_message.edit(content=f"{status_message.content}\n✅ Salon 'règlement' créé")
            except Exception as e:
                logger.error(f"Erreur lors de la création du salon de règlement: {e}")
                await ctx.send(f"❌ Erreur lors de la création du salon de règlement: {e}")
                return False
        else:
            # Mettre à jour les permissions du salon existant
            try:
                rules_overwrites = dict(overwrites)
                rules_overwrites[unverified_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True,
                    add_reactions=True
                )
                
                # Déplacer le salon dans la bonne catégorie si nécessaire
                if rules_channel.category != welcome_category:
                    await rules_channel.edit(
                        category=welcome_category,
                        overwrites=rules_overwrites,
                        position=0,
                        topic="Règlement du serveur - Réagis avec ✅ pour accepter"
                    )
                else:
                    await rules_channel.edit(
                        overwrites=rules_overwrites,
                        position=0,
                        topic="Règlement du serveur - Réagis avec ✅ pour accepter"
                    )
                
                await status_message.edit(content=f"{status_message.content}\n✅ Salon 'règlement' mis à jour")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour du salon de règlement: {e}")
                await ctx.send(f"❌ Erreur lors de la mise à jour du salon de règlement: {e}")
        
        # Créer ou configurer le salon de rôles
        roles_channel = discord.utils.get(guild.text_channels, name="✨・rôles")
        if not roles_channel:
            try:
                # Les overwrites pour le salon des rôles - uniquement accessible aux membres vérifiés
                roles_overwrites = dict(overwrites)
                
                # Les non-vérifiés ne peuvent pas voir le salon des rôles
                roles_overwrites[unverified_role] = discord.PermissionOverwrite(
                    read_messages=False
                )
                
                roles_channel = await guild.create_text_channel(
                    name="✨・rôles",
                    category=welcome_category,
                    overwrites=roles_overwrites,
                    position=1,  # Deuxième salon de la catégorie
                    topic="Choisis tes rôles en cliquant sur les réactions"
                )
                await status_message.edit(content=f"{status_message.content}\n✅ Salon 'rôles' créé")
            except Exception as e:
                logger.error(f"Erreur lors de la création du salon de rôles: {e}")
                await ctx.send(f"❌ Erreur lors de la création du salon de rôles: {e}")
        else:
            # Mettre à jour les permissions du salon existant
            try:
                roles_overwrites = dict(overwrites)
                roles_overwrites[unverified_role] = discord.PermissionOverwrite(
                    read_messages=False
                )
                
                # Déplacer le salon dans la bonne catégorie si nécessaire
                if roles_channel.category != welcome_category:
                    await roles_channel.edit(
                        category=welcome_category,
                        overwrites=roles_overwrites,
                        position=1,
                        topic="Choisis tes rôles en cliquant sur les réactions"
                    )
                else:
                    await roles_channel.edit(
                        overwrites=roles_overwrites,
                        position=1,
                        topic="Choisis tes rôles en cliquant sur les réactions"
                    )
                
                await status_message.edit(content=f"{status_message.content}\n✅ Salon 'rôles' mis à jour")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour du salon de rôles: {e}")
                await ctx.send(f"❌ Erreur lors de la mise à jour du salon de rôles: {e}")
        
        # Créer ou configurer le salon de bienvenue
        welcome_channel = discord.utils.get(guild.text_channels, name="👋・bienvenue")
        if not welcome_channel:
            try:
                # Salon de bienvenue accessible à tous les membres
                welcome_overwrites = dict(overwrites)
                welcome_overwrites[member_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,  # Seul le bot peut y écrire
                    read_message_history=True,
                    add_reactions=True
                )
                
                # Les non-vérifiés ne peuvent pas voir le salon de bienvenue
                welcome_overwrites[unverified_role] = discord.PermissionOverwrite(
                    read_messages=False
                )
                
                welcome_channel = await guild.create_text_channel(
                    name="👋・bienvenue",
                    category=welcome_category,
                    overwrites=welcome_overwrites,
                    position=2,  # Troisième salon de la catégorie
                    topic="Bienvenue aux nouveaux membres !"
                )
                
                # Message de bienvenue par défaut
                welcome_embed = discord.Embed(
                    title="✨ Bienvenue sur le serveur ! ✨",
                    description="Nous sommes ravis de t'accueillir parmi nous !\n\n"
                                "Voici quelques informations importantes :\n"
                                "• Lis attentivement le règlement dans <#📖・règlement>\n"
                                "• Choisis tes rôles dans <#✨・rôles>\n"
                                "• Présente-toi dans <#💬・discussion-générale>",
                    color=discord.Colour.pink()
                )
                welcome_embed.set_footer(text="✧ Ninis • Made with 💖")
                
                await welcome_channel.send(embed=welcome_embed)
                await status_message.edit(content=f"{status_message.content}\n✅ Salon 'bienvenue' créé")
            except Exception as e:
                logger.error(f"Erreur lors de la création du salon de bienvenue: {e}")
                await ctx.send(f"❌ Erreur lors de la création du salon de bienvenue: {e}")
        else:
            # Mettre à jour les permissions du salon existant
            try:
                welcome_overwrites = dict(overwrites)
                welcome_overwrites[member_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True,
                    add_reactions=True
                )
                
                welcome_overwrites[unverified_role] = discord.PermissionOverwrite(
                    read_messages=False
                )
                
                # Déplacer le salon dans la bonne catégorie si nécessaire
                if welcome_channel.category != welcome_category:
                    await welcome_channel.edit(
                        category=welcome_category,
                        overwrites=welcome_overwrites,
                        position=2,
                        topic="Bienvenue aux nouveaux membres !"
                    )
                else:
                    await welcome_channel.edit(
                        overwrites=welcome_overwrites,
                        position=2,
                        topic="Bienvenue aux nouveaux membres !"
                    )
                
                await status_message.edit(content=f"{status_message.content}\n✅ Salon 'bienvenue' mis à jour")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour du salon de bienvenue: {e}")
                await ctx.send(f"❌ Erreur lors de la mise à jour du salon de bienvenue: {e}")
        
        # Étape 4 : Configurer les messages de règlement et de rôles
        await status_message.edit(content=f"{status_message.content}\n\n**Étape 4/4 : Configuration des messages**")
        
        # Créer ou mettre à jour le message de règlement
        rules_updated = await self.update_rules(ctx, rules_channel.id)
        
        if rules_updated:
            await status_message.edit(content=f"{status_message.content}\n✅ Message de règlement configuré")
        else:
            await status_message.edit(content=f"{status_message.content}\n❌ Erreur lors de la configuration du message de règlement")
        
        # Créer ou mettre à jour le message des rôles
        if roles_channel:
            roles_cog = self.bot.get_cog('Roles')
            if roles_cog:
                try:
                    # Sauvegarder le contexte original
                    original_command = ctx.command
                    
                    # Définir temporairement une nouvelle commande pour l'appel
                    ctx.command = self.bot.get_command('setup_role_reactions')
                    
                    # Appeler la méthode de configuration des rôles
                    await roles_cog.setup_role_reactions(ctx)
                    
                    # Restaurer le contexte original
                    ctx.command = original_command
                    
                    await status_message.edit(content=f"{status_message.content}\n✅ Messages de rôles configurés")
                except Exception as e:
                    logger.error(f"Erreur lors de la configuration des messages de rôles: {e}")
                    await status_message.edit(content=f"{status_message.content}\n❌ Erreur lors de la configuration des messages de rôles: {e}")
            else:
                await status_message.edit(content=f"{status_message.content}\n⚠️ Module de rôles non trouvé - configuration manuelle requise")
        
        # Configuration terminée, envoi du message récapitulatif
        embed = discord.Embed(
            title="✅ Système de vérification configuré avec succès !",
            description="Le système de vérification des nouveaux membres est maintenant en place.",
            color=discord.Colour.green()
        )
        
        embed.add_field(
            name="Comment ça marche",
            value="1️⃣ Les nouveaux membres reçoivent automatiquement le rôle `Non vérifié`\n"
                 "2️⃣ Ils ne peuvent voir que le salon des règles\n"
                 "3️⃣ En cliquant sur ✅, ils acceptent le règlement\n"
                 "4️⃣ Le rôle `Membre` leur est attribué automatiquement\n"
                 "5️⃣ Ils ont alors accès à tout le serveur",
            inline=False
        )
        
        embed.add_field(
            name="Salons configurés",
            value=f"📖 {rules_channel.mention} - Règlement à accepter\n"
                 f"✨ {roles_channel.mention if roles_channel else '❌ Non créé'} - Choix des rôles\n"
                 f"👋 {welcome_channel.mention if welcome_channel else '❌ Non créé'} - Accueil des nouveaux",
            inline=False
        )
        
        embed.add_field(
            name="Rôles configurés",
            value=f"🔹 `Non vérifié` - Attribué automatiquement\n"
                 f"🔹 `Membre` - Après acceptation du règlement\n"
                 f"🔹 Rôles optionnels - Garçon/Fille, Majeur/Mineur",
            inline=False
        )
        
        embed.set_footer(text="💡 Rappel : pensez à configurer les autres catégories pour qu'elles soient visibles uniquement par les membres vérifiés !")
        
        # Mise à jour de la dernière configuration
        # Enregistrer la date de la dernière configuration
        self.save_verification_info(guild.id, {
            "last_setup": datetime.now().isoformat(),
            "rules_channel_id": rules_channel.id if rules_channel else None,
            "roles_channel_id": roles_channel.id if roles_channel else None,
            "welcome_channel_id": welcome_channel.id if welcome_channel else None,
            "member_role_id": member_role.id if member_role else None,
            "unverified_role_id": unverified_role.id if unverified_role else None
        })
        
        await ctx.send(embed=embed)
        return True
    
    def save_verification_info(self, guild_id, info):
        """Sauvegarde les informations de vérification pour le serveur."""
        try:
            # Vérifier si le fichier existe et le charger
            verification_data = {}
            if os.path.exists('verification_data.json'):
                with open('verification_data.json', 'r') as f:
                    verification_data = json.load(f)
            
            # Mettre à jour les données pour ce serveur
            verification_data[str(guild_id)] = info
            
            # Sauvegarder les données
            with open('verification_data.json', 'w') as f:
                json.dump(verification_data, f, indent=4)
                
            logger.info(f"Informations de vérification sauvegardées pour le serveur {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des informations de vérification: {e}")
            return False
            
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def update_rules(self, ctx, channel_id=None):
        """Met à jour le règlement du serveur avec un système de rôle-réaction pour l'acceptation."""
        # Si aucun canal n'est spécifié, essayez de trouver celui des règles
        if channel_id is None:
            rules_channel = discord.utils.get(ctx.guild.text_channels, name="📖・règlement")
            if not rules_channel:
                await ctx.send("❌ Canal de règlement introuvable. Spécifie un ID de canal ou crée d'abord le salon '📖・règlement' avec `!setup_verification`.")
                return False
            channel = rules_channel
        else:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except (ValueError, discord.NotFound, discord.Forbidden):
                await ctx.send("❌ Canal introuvable. Vérifie l'ID et mes permissions.")
                return False
        
        # Vérifier que les rôles nécessaires existent
        roles = {role.name: role for role in ctx.guild.roles}
        member_role = roles.get("Membre")
        unverified_role = roles.get("Non vérifié")
        
        if not member_role:
            await ctx.send("⚠️ Le rôle 'Membre' n'existe pas. Je vais le créer.")
            try:
                permissions = discord.Permissions()
                permissions.update(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    add_reactions=True,
                    connect=True,
                    speak=True
                )
                member_role = await ctx.guild.create_role(
                    name="Membre",
                    colour=discord.Colour(0x3498DB),  # Bleu
                    permissions=permissions,
                    hoist=True,
                    mentionable=True,
                    reason="Rôle pour les membres ayant accepté le règlement"
                )
                await ctx.send("✅ Rôle 'Membre' créé avec succès.")
            except Exception as e:
                logger.error(f"Erreur lors de la création du rôle 'Membre': {e}")
                await ctx.send(f"❌ Erreur lors de la création du rôle 'Membre': {e}")
                return False
        
        if not unverified_role:
            await ctx.send("⚠️ Le rôle 'Non vérifié' n'existe pas. Je vais le créer.")
            try:
                unverified_role = await ctx.guild.create_role(
                    name="Non vérifié",
                    colour=discord.Colour(0x95A5A6),  # Gris
                    hoist=True,
                    mentionable=True,
                    reason="Rôle pour les nouveaux membres non vérifiés"
                )
                await ctx.send("✅ Rôle 'Non vérifié' créé avec succès.")
            except Exception as e:
                logger.error(f"Erreur lors de la création du rôle 'Non vérifié': {e}")
                await ctx.send(f"❌ Erreur lors de la création du rôle 'Non vérifié': {e}")
                return False
        
        # Création de l'embed de règlement
        rules_embed = discord.Embed(
            title="୨୧﹒ RÈGLEMENT DU SERVEUR NINIS ﹒୨୧",
            description="Pour accéder au serveur, tu dois lire et accepter le règlement ci-dessous :",
            color=discord.Colour.pink()
        )
        # Ajout d'une image cute core
        rules_embed.set_image(url="https://media.discordapp.net/attachments/1081222505335267448/1093466437046317076/cute-heart.gif")
        
        # Contenu du règlement - Nouveau texte
        rules_text = """
╭︰୨୧︰﹒꒰ 𝓡𝓔̀𝓖𝓛𝓔𝓜𝓔𝓝𝓣 ꒱﹒︰୨୧︰╮

♡ 1.  Sois respectueux.se et bienveillant.e avec chacun.e
♡ 2.  Aucun contenu NSFW, choquant ou inapproprié
♡ 3.  Pas de propos haineux, discriminants ou toxiques
♡ 4.  Pas de spam, pub sauvage ou MP non sollicités
♡ 5.  Garde un pseudo et une photo corrects
♡ 6.  Pas d'auto-promo sans l'accord du staff
♡ 7.  Respecte la vie privée des autres membres
♡ 8.  Le drama reste dehors, ici c'est chill & cozy
♡ 9.  Utilise les bons salons pour chaque sujet
♡ 10. Les décisions du staff sont à respecter

︶︶︶︶︶︶︶︶︶︶

**En cliquant sur ✅, tu acceptes ce règlement**
et tu recevras le rôle `Membre` pour accéder à tout le serveur !

╰︰୨୧︰﹒Merci d'être là, on t'aime fort !﹒︰୨୧︰╯
        """
        
        rules_embed.add_field(name="Règles de la communauté", value=rules_text, inline=False)
        rules_embed.add_field(
            name="Acceptation du règlement",
            value="Pour accéder au serveur, réagis avec ✅ pour confirmer que tu as lu et accepté le règlement.",
            inline=False
        )
        rules_embed.set_footer(text="✧ Ninis • Made with 💖")
        
        # Purge le canal des messages existants
        try:
            await channel.purge(limit=100)
            logger.info(f"Canal '{channel.name}' nettoyé pour le nouveau règlement")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du canal '{channel.name}': {e}")
            await ctx.send(f"⚠️ Je n'ai pas pu nettoyer le canal. Erreur: {e}")
        
        # Envoie le nouveau règlement
        rules_message = await channel.send(embed=rules_embed)
        
        # Ajoute la réaction pour accepter
        await rules_message.add_reaction("✅")
        
        # Sauvegarde l'ID du message et du canal pour les futures utilisations
        try:
            with open('rules_data.json', 'w') as f:
                rules_data = {
                    "rules_message_id": rules_message.id,
                    "rules_channel_id": channel.id
                }
                json.dump(rules_data, f, indent=4)
                
            # Mise à jour des variables globales
            config.RULES_MESSAGE_ID = rules_message.id
            config.RULES_CHANNEL_ID = channel.id
            
            logger.info(f"IDs sauvegardés: Message: {rules_message.id}, Canal: {channel.id}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des IDs: {e}")
            await ctx.send(f"⚠️ Erreur lors de la sauvegarde des données: {e}")
        
        # Configurer le gestionnaire d'événements raw_reaction_add s'il n'existe pas déjà
        if not hasattr(self.bot, '_rules_reaction_handler_registered'):
            @self.bot.event
            async def on_raw_reaction_add(payload):
                # Vérifier si c'est une réaction sur le message de règlement
                if payload.message_id == config.RULES_MESSAGE_ID:
                    # Vérifier si c'est la bonne réaction (✅)
                    if str(payload.emoji) == config.RULES_EMOJI:
                        # Ignorer les réactions du bot
                        if payload.user_id == self.bot.user.id:
                            return
                        
                        # Obtenir le serveur et le membre
                        guild = self.bot.get_guild(payload.guild_id)
                        if not guild:
                            return
                        
                        member = guild.get_member(payload.user_id)
                        if not member:
                            return
                        
                        # Obtenir le rôle "Membre"
                        member_role = discord.utils.get(guild.roles, name="Membre")
                        unverified_role = discord.utils.get(guild.roles, name="Non vérifié")
                        
                        if not member_role:
                            logger.error("Rôle 'Membre' non trouvé!")
                            return
                        
                        # Vérifier si le membre n'a pas déjà le rôle
                        if member_role not in member.roles:
                            try:
                                # Ajouter le rôle "Membre"
                                await member.add_roles(member_role)
                                logger.info(f"Rôle 'Membre' ajouté à {member.display_name}")
                                
                                # Retirer le rôle "Non vérifié" si présent
                                if unverified_role and unverified_role in member.roles:
                                    await member.remove_roles(unverified_role)
                                    logger.info(f"Rôle 'Non vérifié' retiré de {member.display_name}")
                                
                                # Envoyer un message de bienvenue privé
                                try:
                                    welcome_embed = discord.Embed(
                                        title="✨ Bienvenue sur Ninis ! ✨",
                                        description=f"Merci d'avoir accepté le règlement, {member.mention} !\n\n"
                                                   f"Tu as maintenant accès à tous les salons du serveur. N'hésite pas à te présenter et à choisir tes rôles dans le salon <#✨・rôles>.",
                                        color=discord.Colour.green()
                                    )
                                    welcome_embed.set_footer(text="✧ Ninis • Made with 💖")
                                    
                                    await member.send(embed=welcome_embed)
                                except Exception as e:
                                    logger.error(f"Impossible d'envoyer un DM à {member.display_name}: {e}")
                            except Exception as e:
                                logger.error(f"Erreur lors de l'attribution du rôle 'Membre' à {member.display_name}: {e}")
            
            self.bot._rules_reaction_handler_registered = True
            logger.info("Gestionnaire d'événements pour les réactions du règlement enregistré")
        
        await ctx.send(f"✅ Règlement mis à jour dans <#{channel.id}> avec système d'acceptation par réaction.")
        return True

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def create_bot_commands(self, ctx):
        """Create a dedicated channel for bot commands."""
        # Check if a commands channel already exists
        existing_channel = discord.utils.get(ctx.guild.text_channels, name="🤖・commandes-bot")
        
        if existing_channel:
            await ctx.send(f"⚠️ Le salon {existing_channel.mention} existe déjà.")
            return
            
        try:
            # Look for a utility category or create one
            category = discord.utils.get(ctx.guild.categories, name="💬 DISCUSSIONS")
            
            if not category:
                # Look for other community-like categories
                for cat in ctx.guild.categories:
                    if "discussion" in cat.name.lower() or "communaut" in cat.name.lower() or "chat" in cat.name.lower():
                        category = cat
                        break
            
            if not category:
                # Create a new category
                category = await ctx.guild.create_category(name="💬 DISCUSSIONS")
                logger.info(f"Created new category '💬 DISCUSSIONS' in {ctx.guild.name}")
            
            # Create permissions overwrites for the channel
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                ),
                ctx.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    manage_messages=True
                )
            }
            
            # Create the channel
            channel = await ctx.guild.create_text_channel(
                name="🤖・commandes-bot",
                category=category,
                overwrites=overwrites,
                topic="Salon pour les commandes du bot Ninis"
            )
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Salon de commandes bot créé",
                description=f"Le salon {channel.mention} a été créé pour utiliser les commandes du bot.",
                color=discord.Colour.green()
            )
            
            await ctx.send(embed=embed)
            
            # Send welcome message in the new channel
            welcome_embed = discord.Embed(
                title="🤖 Commandes Bot Ninis",
                description="Ce salon est dédié aux commandes du bot Ninis.\n\n"
                            "Voici quelques commandes utiles :\n"
                            f"• `{config.PREFIX}help` - Voir toutes les commandes disponibles\n"
                            f"• `{config.PREFIX}info` - Informations sur le bot\n"
                            f"• `{config.PREFIX}serverinfo` - Informations sur le serveur\n"
                            f"• `{config.PREFIX}check_tiktok_now` - Vérifier les mises à jour TikTok",
                color=discord.Colour.blue()
            )
            
            welcome_embed.set_footer(text="✧ Ninis • Made with 💖")
            
            await channel.send(embed=welcome_embed)
            
        except Exception as e:
            logger.error(f"Error creating bot commands channel: {e}")
            await ctx.send(f"❌ Erreur lors de la création du salon: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset_server(self, ctx):
        """Reset the entire server by deleting all channels and roles."""
        guild = ctx.guild
        
        # Generate a random verification code for security
        verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Create warning embed with verification
        warning_embed = discord.Embed(
            title="⚠️ RÉINITIALISATION TOTALE DU SERVEUR ⚠️",
            description="Cette commande va supprimer **TOUS** les salons et rôles du serveur, et le remettre à zéro.\n\n"
                        "**ATTENTION: Cette action est irréversible et destructive !**",
            color=discord.Colour.red()
        )
        warning_embed.add_field(
            name="Confirmation requise",
            value=f"Pour confirmer, tape exactement:\n`{verification_code}`\n\n"
                  f"Tu as 30 secondes pour confirmer, ou `annuler` pour annuler.",
            inline=False
        )
        warning_embed.set_footer(text="⚠️ Cette action est extrêmement destructive et ne peut pas être annulée.")
        
        await ctx.send(embed=warning_embed)
        
        # Wait for confirmation with the exact verification code
        try:
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel and \
                       (message.content == verification_code or message.content.lower() == "annuler")
            
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if response.content.lower() == "annuler":
                await ctx.send("✅ Réinitialisation annulée.")
                return
            
            if response.content != verification_code:
                await ctx.send("❌ Code de vérification incorrect. Réinitialisation annulée.")
                return
                
        except asyncio.TimeoutError:
            await ctx.send("⏱️ Délai d'attente expiré. Réinitialisation annulée.")
            return
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_basic_roles(self, ctx):
        """Configure les rôles de base simplifiés pour le serveur (Owner, Nini Queen, Administrateur, Modérateur, Membre)."""
        guild = ctx.guild
        
        # Message de confirmation
        embed = discord.Embed(
            title="👑 Configuration des rôles simplifiés",
            description=(
                "Cette commande va configurer les rôles essentiels suivants UNIQUEMENT :\n\n"
                "• Owner (Propriétaire)\n"
                "• ✦ ꒰ Nini Queen ꒱\n"
                "• Administrateur\n"
                "• Modérateur\n"
                "• Membre\n\n"
                "Les autres rôles seront supprimés pour simplifier la structure."
            ),
            color=discord.Colour.gold()
        )
        
        embed.set_footer(text="Réponds avec 'oui' pour confirmer ou 'non' pour annuler.")
        
        await ctx.send(embed=embed)
        
        # Attendre la confirmation
        try:
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel and \
                       message.content.lower() in ["oui", "non", "yes", "no"]
            
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            
            if response.content.lower() in ["non", "no"]:
                await ctx.send("❌ Configuration annulée.")
                return
                
        except asyncio.TimeoutError:
            await ctx.send("⏱️ Délai d'attente expiré. Configuration annulée.")
            return
            
        # Envoyer un message indiquant que la configuration a commencé
        status_message = await ctx.send("⏳ Configuration des rôles de base en cours...")
        
        # Récupérer les rôles existants
        existing_roles = {role.name: role for role in guild.roles}
        
        # Créer ou mettre à jour les rôles de base
        created_roles = []
        updated_roles = []
        
        for role_name, role_data in config.BASIC_ROLES.items():
            if role_name in existing_roles:
                # Le rôle existe déjà, mettre à jour ses propriétés
                try:
                    role = existing_roles[role_name]
                    
                    # Définir les permissions administratives si nécessaire
                    if role_data["permissions"]:
                        permissions = discord.Permissions()
                        permissions.update(
                            administrator=True
                        )
                    else:
                        # Permissions de base pour les membres
                        permissions = discord.Permissions()
                        permissions.update(
                            read_messages=True,
                            send_messages=True,
                            read_message_history=True,
                            add_reactions=True,
                            connect=True,
                            speak=True
                        )
                    
                    # Mettre à jour le rôle
                    await role.edit(
                        colour=discord.Colour(role_data["color"]),
                        permissions=permissions,
                        hoist=role_data["hoist"],
                        mentionable=role_data["mentionable"],
                        reason="Mise à jour du rôle via !setup_basic_roles"
                    )
                    updated_roles.append(role_name)
                    logger.info(f"Rôle '{role_name}' mis à jour avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour du rôle '{role_name}': {e}")
                    await ctx.send(f"❌ Erreur lors de la mise à jour du rôle '{role_name}': {e}")
            else:
                # Le rôle n'existe pas, le créer
                try:
                    # Définir les permissions administratives si nécessaire
                    if role_data["permissions"]:
                        permissions = discord.Permissions()
                        permissions.update(
                            administrator=True
                        )
                    else:
                        # Permissions de base pour les membres
                        permissions = discord.Permissions()
                        permissions.update(
                            read_messages=True,
                            send_messages=True,
                            read_message_history=True,
                            add_reactions=True,
                            connect=True,
                            speak=True
                        )
                    
                    # Créer le rôle
                    new_role = await guild.create_role(
                        name=role_name,
                        colour=discord.Colour(role_data["color"]),
                        permissions=permissions,
                        hoist=role_data["hoist"],
                        mentionable=role_data["mentionable"],
                        reason="Création de rôle via !setup_basic_roles"
                    )
                    created_roles.append(role_name)
                    logger.info(f"Rôle '{role_name}' créé avec succès")
                    
                    # Mettre à jour la position du rôle pour l'Owner en haut
                    if role_name == "Owner":
                        # Placer Owner tout en haut, juste en dessous du bot
                        try:
                            positions = {
                                new_role: guild.me.top_role.position - 1
                            }
                            await guild.edit_role_positions(positions=positions)
                            logger.info(f"Position du rôle '{role_name}' mise à jour")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour de la position du rôle '{role_name}': {e}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la création du rôle '{role_name}': {e}")
                    await ctx.send(f"❌ Erreur lors de la création du rôle '{role_name}': {e}")
        
        # Mettre à jour le message de statut
        summary = ""
        
        if created_roles:
            summary += f"✅ **Rôles créés ({len(created_roles)})** :\n"
            summary += "• " + "\n• ".join(created_roles) + "\n\n"
        
        if updated_roles:
            summary += f"✅ **Rôles mis à jour ({len(updated_roles)})** :\n"
            summary += "• " + "\n• ".join(updated_roles)
        
        if not created_roles and not updated_roles:
            summary = "❌ Aucun rôle n'a été créé ou mis à jour."
        
        # Créer un embed récapitulatif
        embed = discord.Embed(
            title="✨ Configuration des rôles de base terminée",
            description="Les rôles de base ont été configurés pour le serveur.",
            color=discord.Colour.green()
        )
        
        embed.add_field(
            name="Résumé",
            value=summary,
            inline=False
        )
        
        embed.add_field(
            name="Prochaines étapes",
            value="1. Utilise `!setup_verification` pour configurer le système de vérification\n"
                 "2. Associe les rôles aux membres appropriés manuellement\n"
                 "3. Configure les salons avec les permissions appropriées",
            inline=False
        )
        
        embed.set_footer(text="✧ Ninis • Made with 💖")
        
        await status_message.edit(content="", embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_bot(self, ctx):
        """Configure un ensemble de salons et catégories dédiés aux commandes du bot."""
        guild = ctx.guild
        
        # Crée une catégorie pour les commandes du bot
        try:
            # Création d'une catégorie pour les commandes du bot
            bot_category = await guild.create_category("🤖・BOT", position=0)
            
            # Création du salon de commandes
            command_channel = await guild.create_text_channel(
                "👾・commandes", 
                category=bot_category,
                topic="Utilisez ce salon pour les commandes du bot"
            )
            
            # Création d'un salon de logs
            logs_channel = await guild.create_text_channel(
                "📝・logs", 
                category=bot_category,
                topic="Logs automatiques du serveur"
            )
            
            # Message de confirmation
            embed = discord.Embed(
                title="✅ Configuration des salons bot terminée",
                description="Les salons dédiés au bot ont été créés avec succès !",
                color=discord.Colour.green()
            )
            
            embed.add_field(
                name="Salons créés",
                value=f"• {command_channel.mention}\n• {logs_channel.mention}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des salons du bot: {e}")
            await ctx.send(f"❌ Une erreur est survenue: {e}")
            
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_basic_roles(self, ctx):
        """Crée les rôles de base pour le serveur, y compris les rôles de niveau."""
        guild = ctx.guild
        
        # Message d'initialisation
        status_message = await ctx.send("⏳ Configuration des rôles de base...")
        
        # Créer les rôles de base
        roles_created = []
        roles_updated = []
        roles_failed = []
        
        # Parcourir tous les rôles de la configuration
        for role_name, role_data in config.BASIC_ROLES.items():
            # Vérifier si le rôle existe déjà
            existing_role = discord.utils.get(guild.roles, name=role_name)
            
            if existing_role:
                # Mettre à jour le rôle existant
                try:
                    await existing_role.edit(
                        colour=discord.Colour(role_data["color"]),
                        hoist=role_data.get("hoist", False),
                        mentionable=role_data.get("mentionable", False),
                        reason="Mise à jour des rôles de base"
                    )
                    roles_updated.append(f"✅ **{role_name}** (mis à jour)")
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour du rôle '{role_name}': {e}")
                    roles_failed.append(f"❌ **{role_name}** (erreur: {e})")
            else:
                # Créer le nouveau rôle
                try:
                    permissions = discord.Permissions()
                    if role_data.get("permissions", False):
                        # Rôle d'administration avec toutes les permissions
                        permissions.update(administrator=True)
                    else:
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
                        colour=discord.Colour(role_data["color"]),
                        permissions=permissions,
                        hoist=role_data.get("hoist", False),
                        mentionable=role_data.get("mentionable", False),
                        reason="Création des rôles de base"
                    )
                    roles_created.append(f"✅ **{role_name}** (créé)")
                except Exception as e:
                    logger.error(f"Erreur lors de la création du rôle '{role_name}': {e}")
                    roles_failed.append(f"❌ **{role_name}** (erreur: {e})")
        
        # Mettre à jour le message de statut
        await status_message.edit(content="✅ Configuration des rôles terminée !")
        
        # Créer un embed pour afficher les résultats
        embed = discord.Embed(
            title="🔧 Configuration des Rôles",
            description="Résultat de la création des rôles de base pour le serveur",
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
        
        # Ajouter des informations sur les rôles de niveau
        embed.add_field(
            name="Rôles de niveau",
            value=(
                "Les rôles de niveau ont été créés/mis à jour :\n"
                "• **Nini Nouveau** — Niveau 1\n"
                "• **Nini Curieux** — Niveau 5\n"
                "• **Nini Actif** — Niveau 10\n"
                "• **Nini Confirmé** — Niveau 20\n"
                "• **Nini Légende** — Niveau 30\n\n"
                "*Pour créer uniquement les rôles de niveau, utilisez `!setup_levels`*"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(Setup(bot))
