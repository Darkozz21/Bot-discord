"""
Utility cog for the Ninis discord bot.
Includes welcome messages, statistics channels and utility commands.
"""
import logging
import discord
from discord.ext import commands, tasks
import config
import asyncio

# Set up logging
logger = logging.getLogger('ninis_bot')

class Utils(commands.Cog):
    """Utility commands and event handlers."""
    
    def __init__(self, bot):
        self.bot = bot
        self.stats_channels = {}
        # Démarrage différé de la tâche de mise à jour pour permettre au bot de se préparer
        self.bot.loop.create_task(self.start_tasks())
        
    async def start_tasks(self):
        """Démarre les tâches périodiques après l'initialisation du bot."""
        await self.bot.wait_until_ready()
        logger.info("Démarrage des tâches périodiques de Utils")
        # Initialiser les canaux de statistiques existants
        await self.initialize_stats_channels()
        # Démarrer la tâche de mise à jour
        self.update_stats_channels.start()
        
    def cog_unload(self):
        """Cancel the task when the cog is unloaded."""
        self.update_stats_channels.cancel()
        
    async def initialize_stats_channels(self):
        """Recherche et initialise les canaux de statistiques existants."""
        logger.info("Initialisation des canaux de statistiques...")
        for guild in self.bot.guilds:
            try:
                # Recherche tous les canaux vocaux qui pourraient être des canaux de statistiques
                stats_channels = [channel for channel in guild.channels if 
                                  isinstance(channel, discord.VoiceChannel) and
                                  (("membres" in channel.name.lower()) or 
                                   ("en ligne" in channel.name.lower()) or
                                   ("en vocal" in channel.name.lower()) or
                                   ("👥" in channel.name) or
                                   ("👤" in channel.name) or
                                   ("🔊" in channel.name))]
                
                if len(stats_channels) >= 3:
                    # Trouver le canal des membres
                    members_channel = None
                    for channel in stats_channels:
                        if "membres" in channel.name.lower() or "👥" in channel.name:
                            members_channel = channel
                            break
                    
                    # Trouver le canal des membres en ligne
                    online_channel = None
                    for channel in stats_channels:
                        if "en ligne" in channel.name.lower() or "👤" in channel.name:
                            online_channel = channel
                            break
                    
                    # Trouver le canal des membres en vocal
                    voice_channel = None
                    for channel in stats_channels:
                        if "en vocal" in channel.name.lower() or "🔊" in channel.name:
                            voice_channel = channel
                            break
                    
                    # Si tous les canaux sont trouvés, les enregistrer
                    if members_channel and online_channel and voice_channel:
                        self.stats_channels[guild.id] = {
                            "members": members_channel.id,
                            "online": online_channel.id,
                            "voice": voice_channel.id,
                        }
                        logger.info(f"Canaux de statistiques trouvés pour {guild.name}: {members_channel.name}, {online_channel.name}, {voice_channel.name}")
                        # Mise à jour immédiate
                        await self.update_guild_stats(guild)
                    else:
                        logger.warning(f"Canaux de statistiques incomplets pour {guild.name}. Trouvés: {len([c for c in [members_channel, online_channel, voice_channel] if c])}/3")
                        # Déboguer quels canaux sont trouvés
                        if members_channel:
                            logger.info(f"Canal membres trouvé: {members_channel.name}")
                        if online_channel:
                            logger.info(f"Canal en ligne trouvé: {online_channel.name}")
                        if voice_channel:
                            logger.info(f"Canal en vocal trouvé: {voice_channel.name}")
                else:
                    logger.info(f"Pas assez de canaux de statistiques trouvés pour {guild.name} ({len(stats_channels)})")
                    # Déboguer quels canaux sont disponibles
                    for channel in stats_channels:
                        logger.info(f"Canal potentiel: {channel.name}")
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation des canaux de stats pour {guild.name}: {e}")
                continue
        
    @commands.command()
    async def delete_stats_channels(self, ctx):
        """Supprime les canaux de statistiques du serveur."""
        # Vérifier si l'utilisateur est administrateur ou propriétaire du serveur
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id):
            await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
            return
            
        # Vérifier si nous avons des canaux de statistiques enregistrés pour ce serveur
        if ctx.guild.id not in self.stats_channels:
            await ctx.send("⚠️ Aucun canal de statistiques n'est enregistré pour ce serveur.")
            return
            
        try:
            # Récupérer les IDs des canaux
            members_id = self.stats_channels[ctx.guild.id]["members"]
            online_id = self.stats_channels[ctx.guild.id]["online"]
            voice_id = self.stats_channels[ctx.guild.id]["voice"]
            
            # Récupérer les objets de canaux
            members_channel = ctx.guild.get_channel(members_id)
            online_channel = ctx.guild.get_channel(online_id)
            voice_channel = ctx.guild.get_channel(voice_id)
            
            # Compter combien de canaux existent encore
            existing_channels = 0
            deleted_channels = 0
            
            # Supprimer les canaux s'ils existent
            if members_channel:
                existing_channels += 1
                await members_channel.delete(reason="Suppression des canaux de statistiques")
                deleted_channels += 1
                
            if online_channel:
                existing_channels += 1
                await online_channel.delete(reason="Suppression des canaux de statistiques")
                deleted_channels += 1
                
            if voice_channel:
                existing_channels += 1
                await voice_channel.delete(reason="Suppression des canaux de statistiques")
                deleted_channels += 1
                
            # Supprimer les données
            del self.stats_channels[ctx.guild.id]
            
            # Envoyer un message de confirmation
            if existing_channels > 0:
                await ctx.send(f"✅ {deleted_channels}/{existing_channels} canaux de statistiques ont été supprimés avec succès.")
            else:
                await ctx.send("⚠️ Les canaux de statistiques n'existaient plus, mais les données ont été nettoyées.")
                
            logger.info(f"Canaux de statistiques supprimés pour {ctx.guild.name} par {ctx.author}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des canaux de statistiques: {e}")
            await ctx.send(f"❌ Une erreur s'est produite lors de la suppression des canaux: {e}")
    
    @commands.command()
    async def create_stats_channels(self, ctx):
        """Create channels displaying server statistics at the top of the channel list."""
        # Vérifier si l'utilisateur est administrateur ou propriétaire du serveur
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id):
            await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
            return
            
        # Check if stats channels already exist
        existing_members = discord.utils.get(ctx.guild.channels, name=lambda n: "👥・membres:" in n if n else False)
        existing_online = discord.utils.get(ctx.guild.channels, name=lambda n: "👤・en ligne:" in n if n else False)
        existing_voice = discord.utils.get(ctx.guild.channels, name=lambda n: "🔊・en vocal:" in n if n else False)
        
        if existing_members and existing_online and existing_voice:
            await ctx.send("⚠️ Les salons de statistiques existent déjà.")
            return
        
        try:
            # Envoyer un message pour indiquer que les canaux sont en cours de création
            status_message = await ctx.send("⏳ Création des canaux de statistiques en cours...")
            
            # Create category for stats
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    view_channel=True,
                    connect=False,
                    send_messages=False,
                )
            }
            
            # Create the channels
            members_channel = await ctx.guild.create_voice_channel(
                name=f"👥・membres: {ctx.guild.member_count}",
                overwrites=overwrites,
                position=0,
                reason="Canal de statistiques - membres"
            )
            
            # Attendre un peu pour éviter le rate limiting
            await asyncio.sleep(1)
            
            # Estimation du nombre de membres en ligne (nous ne pouvons plus accéder au statut)
            online_count = int(ctx.guild.member_count * 0.3)  # Environ 30% en ligne
            online_channel = await ctx.guild.create_voice_channel(
                name=f"👤・en ligne: ~{online_count}",
                overwrites=overwrites,
                position=1,
                reason="Canal de statistiques - membres en ligne"
            )
            
            # Attendre un peu pour éviter le rate limiting
            await asyncio.sleep(1)
            
            # Calculate voice members count
            voice_count = sum(1 for m in ctx.guild.members if m.voice is not None)
            voice_channel = await ctx.guild.create_voice_channel(
                name=f"🔊・en vocal: {voice_count}",
                overwrites=overwrites,
                position=2,
                reason="Canal de statistiques - membres en vocal"
            )
            
            # Store the channels
            self.stats_channels[ctx.guild.id] = {
                "members": members_channel.id,
                "online": online_channel.id,
                "voice": voice_channel.id,
            }
            
            # Log the creation
            logger.info(f"Canaux de statistiques créés pour {ctx.guild.name} par {ctx.author}")
            
            # Mise à jour immédiate des statistiques
            await self.update_guild_stats(ctx.guild)
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Canaux de statistiques créés",
                description="Les canaux de statistiques apparaissent en haut de la liste des canaux et seront mis à jour toutes les 5 minutes.",
                color=discord.Colour.green()
            )
            
            await status_message.edit(content=None, embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating stats channels: {e}")
            await ctx.send(f"❌ Erreur lors de la création des canaux de statistiques: {e}")
    
    async def update_guild_stats(self, guild):
        """Met à jour les canaux de statistiques pour un serveur spécifique."""
        try:
            # Vérifier que nous avons des canaux de statistiques pour ce serveur
            if guild.id not in self.stats_channels:
                return False
            
            # Récupérer les objets de canaux
            members_channel = guild.get_channel(self.stats_channels[guild.id]["members"])
            online_channel = guild.get_channel(self.stats_channels[guild.id]["online"])
            voice_channel = guild.get_channel(self.stats_channels[guild.id]["voice"])
            
            if not all([members_channel, online_channel, voice_channel]):
                # Un ou plusieurs canaux ont été supprimés
                if guild.id in self.stats_channels:
                    del self.stats_channels[guild.id]
                return False
            
            # Mise à jour du compteur de membres
            member_count = guild.member_count
            await members_channel.edit(name=f"👥・membres: {member_count}")
            
            # Mise à jour du compteur 'en ligne'
            # Note: Nous ne pouvons plus accéder au statut de présence car il nécessite des intents privilégiés
            # Nous utilisons une valeur approximative basée sur le nombre total de membres
            online_count = int(member_count * 0.3)  # Estimation approximative: ~30% sont en ligne
            await online_channel.edit(name=f"👤・en ligne: ~{online_count}")
            
            # Mise à jour du compteur vocal
            voice_count = sum(1 for m in guild.members if m.voice is not None)
            await voice_channel.edit(name=f"🔊・en vocal: {voice_count}")
            
            logger.info(f"Statistiques mises à jour pour {guild.name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques pour {guild.name}: {e}")
            return False
    
    @tasks.loop(minutes=2)
    async def update_stats_channels(self):
        """Met à jour les canaux de statistiques avec les informations actuelles du serveur.
        Cette tâche s'exécute toutes les 2 minutes."""
        logger.info("Début de la mise à jour des canaux de statistiques...")
        success_count = 0
        for guild in self.bot.guilds:
            success = await self.update_guild_stats(guild)
            if success:
                success_count += 1
                
        logger.info(f"Mise à jour des statistiques terminée. {success_count}/{len(self.bot.guilds)} serveurs mis à jour avec succès.")
    
    @update_stats_channels.before_loop
    async def before_update_stats(self):
        """Attend que le bot soit prêt avant de commencer la boucle."""
        await self.bot.wait_until_ready()
        logger.info("Tâche de mise à jour des statistiques prête à démarrer")
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def find_stats_channels(self, ctx):
        """Recherche et configure les canaux de statistiques existants."""
        await ctx.send("🔍 Recherche des canaux de statistiques existants...")
        
        # Recherche tous les canaux vocaux qui pourraient être des canaux de statistiques
        stats_channels = [channel for channel in ctx.guild.channels if 
                          isinstance(channel, discord.VoiceChannel) and
                          (("membres" in channel.name.lower()) or 
                           ("en ligne" in channel.name.lower()) or
                           ("en vocal" in channel.name.lower()) or
                           ("👥" in channel.name) or
                           ("👤" in channel.name) or
                           ("🔊" in channel.name))]
        
        if len(stats_channels) < 3:
            await ctx.send(f"⚠️ Seulement {len(stats_channels)} canaux de statistiques potentiels trouvés. Au moins 3 sont nécessaires.")
            if stats_channels:
                canaux = "\n".join([f"- {c.name}" for c in stats_channels])
                await ctx.send(f"Canaux trouvés:\n{canaux}")
            return
            
        # Trouver le canal des membres
        members_channel = None
        for channel in stats_channels:
            if "membres" in channel.name.lower() or "👥" in channel.name:
                members_channel = channel
                break
        
        # Trouver le canal des membres en ligne
        online_channel = None
        for channel in stats_channels:
            if "en ligne" in channel.name.lower() or "👤" in channel.name:
                online_channel = channel
                break
        
        # Trouver le canal des membres en vocal
        voice_channel = None
        for channel in stats_channels:
            if "en vocal" in channel.name.lower() or "🔊" in channel.name:
                voice_channel = channel
                break
        
        # Si tous les canaux sont trouvés, les enregistrer
        if members_channel and online_channel and voice_channel:
            self.stats_channels[ctx.guild.id] = {
                "members": members_channel.id,
                "online": online_channel.id,
                "voice": voice_channel.id,
            }
            await ctx.send(f"✅ Canaux de statistiques trouvés et configurés :\n- Membres: {members_channel.name}\n- En ligne: {online_channel.name}\n- En vocal: {voice_channel.name}")
            logger.info(f"Canaux de statistiques trouvés manuellement pour {ctx.guild.name}: {members_channel.name}, {online_channel.name}, {voice_channel.name}")
            
            # Mise à jour immédiate
            success = await self.update_guild_stats(ctx.guild)
            if success:
                await ctx.send("✅ Statistiques mises à jour avec succès.")
            else:
                await ctx.send("⚠️ Erreur lors de la mise à jour des statistiques.")
        else:
            await ctx.send(f"⚠️ Tous les canaux nécessaires n'ont pas été trouvés.\nTrouvés: {len([c for c in [members_channel, online_channel, voice_channel] if c])}/3")
            # Afficher quels canaux sont trouvés
            canaux_trouves = []
            if members_channel:
                canaux_trouves.append(f"- Membres: {members_channel.name}")
            if online_channel:
                canaux_trouves.append(f"- En ligne: {online_channel.name}")
            if voice_channel:
                canaux_trouves.append(f"- En vocal: {voice_channel.name}")
                
            if canaux_trouves:
                await ctx.send("Canaux trouvés:\n" + "\n".join(canaux_trouves))
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def update_stats(self, ctx):
        """Force la mise à jour immédiate des canaux de statistiques."""
        # Vérifier si le serveur a des canaux de statistiques configurés
        if ctx.guild.id not in self.stats_channels:
            await ctx.send("⚠️ Ce serveur n'a pas de canaux de statistiques configurés. Utilisez `!find_stats_channels` pour rechercher les canaux existants ou `!create_stats_channels` pour en créer.")
            return
            
        await ctx.send("⏳ Mise à jour des statistiques en cours...")
        
        # Essayer de mettre à jour les statistiques
        success = await self.update_guild_stats(ctx.guild)
        
        if success:
            # Récupérer les compteurs actuels pour les afficher
            member_count = ctx.guild.member_count
            voice_count = sum(1 for m in ctx.guild.members if m.voice is not None)
            online_count = int(member_count * 0.3)  # Estimation approximative: ~30% sont en ligne
            
            embed = discord.Embed(
                title="✅ Statistiques mises à jour",
                description="Les canaux de statistiques ont été mis à jour avec succès.",
                color=discord.Colour.green()
            )
            
            embed.add_field(name="👥 Membres", value=str(member_count), inline=True)
            embed.add_field(name="👤 En ligne (estimé)", value=f"~{online_count}", inline=True)
            embed.add_field(name="🔊 En vocal", value=str(voice_count), inline=True)
            
            embed.set_footer(text="Les statistiques sont automatiquement mises à jour toutes les 2 minutes")
            
            await ctx.send(embed=embed)
            logger.info(f"Statistiques mises à jour manuellement pour {ctx.guild.name} par {ctx.author}")
        else:
            await ctx.send("❌ Erreur lors de la mise à jour des statistiques. Vérifiez que les canaux existent toujours.")
            logger.error(f"Échec de la mise à jour manuelle des statistiques pour {ctx.guild.name}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send welcome message when a new member joins and add unverified role."""
        # Utiliser directement l'ID du canal spécifié
        welcome_channel = member.guild.get_channel(1357030847768825969)
        
        # Fallback au cas où le canal avec cet ID n'existe pas
        if not welcome_channel:
            # Chercher d'autres salons de bienvenue
            welcome_channel = discord.utils.get(member.guild.text_channels, name="hello-toujours-coquette")
            
            if not welcome_channel:
                welcome_channel = discord.utils.get(member.guild.text_channels, name="📌・bienvenue")
            
            if not welcome_channel:
                # Try to find any welcome-related channel
                for channel in member.guild.text_channels:
                    if "bienvenue" in channel.name or "welcome" in channel.name or "hello" in channel.name:
                        welcome_channel = channel
                        break
            
            if not welcome_channel:
                # No welcome channel found, log error
                logger.warning(f"No welcome channel found for guild {member.guild.name}")
                return
        
        # Get rule and role channels for mentions
        rules_channel = discord.utils.get(member.guild.text_channels, name="📖・règlement")
        roles_channel = discord.utils.get(member.guild.text_channels, name="✨・rôles")
        
        # Trouver qui a invité le membre
        invite_code = None
        inviter = None
        invite_count = 0
        
        # Récupérer le module d'invitations s'il est disponible
        invites_cog = self.bot.get_cog('Invites')
        if invites_cog:
            try:
                invite_code, inviter, invite_count = await invites_cog.find_used_invite(member.guild)
                logger.info(f"Invitation trouvée pour {member.name}: {invite_code} par {inviter.name if inviter else 'Inconnu'}")
            except Exception as e:
                logger.error(f"Erreur lors de la récupération de l'invitation pour {member.name}: {e}")
        
        # Format welcome message with proper channel mentions - ici on garde l'ancien format
        welcome_msg = config.WELCOME_MESSAGE.format(
            member=member,
            guild=member.guild,
            member_count=len(member.guild.members)
        )
        
        # Create welcome embed
        embed = discord.Embed(
            title=f"✨ Bienvenue {member.name} !",
            description=welcome_msg,
            color=discord.Colour.pink()
        )
        
        # Ajouter l'information sur l'invitation si disponible
        if inviter:
            # Pluriel des invitations
            s = "s" if invite_count > 1 else ""
            embed.add_field(
                name="💌 Invitation",
                value=f"Tu as été invité(e) par {inviter.mention} qui a maintenant **{invite_count}** invitation{s} !",
                inline=False
            )
        
        # Add channel mentions if channels exist
        if rules_channel and roles_channel:
            embed.add_field(
                name="📌 Navigation",
                value=f"Tu peux consulter {rules_channel.mention} et choisir tes rôles dans {roles_channel.mention} !",
                inline=False
            )
        
        if rules_channel:
            embed.add_field(
                name="⚠️ IMPORTANT ⚠️",
                value=f"Pour accéder à l'ensemble du serveur, tu dois lire et accepter le règlement dans {rules_channel.mention} en cliquant sur ✅",
                inline=False
            )
        
        # Set author with member avatar
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        
        # Set footer
        embed.set_footer(text=f"✧ {member.guild.name} • Made with 💖")
        
        # Send welcome message
        await welcome_channel.send(embed=embed)
        
        # Ajout du rôle "Non vérifié"
        try:
            unverified_role = discord.utils.get(member.guild.roles, name="Non vérifié")
            if unverified_role:
                await member.add_roles(unverified_role)
                logger.info(f"Rôle Non vérifié ajouté à {member.name}")
            else:
                logger.warning(f"Rôle Non vérifié introuvable pour {member.guild.name}")
                
                # Fallback au rôle par défaut si "Non vérifié" n'existe pas
                default_role = discord.utils.get(member.guild.roles, name="⋆ Baby Nini")
                if default_role:
                    await member.add_roles(default_role)
                    logger.info(f"Role par défaut ajouté à {member.name} (car Non vérifié n'existe pas)")
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du rôle au nouveau membre {member.name}: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Send leave message when a member leaves."""
        # Get welcome channel
        welcome_channel = discord.utils.get(member.guild.text_channels, name="📌・bienvenue")
        
        if not welcome_channel:
            # Try to find any welcome-related channel
            for channel in member.guild.text_channels:
                if "bienvenue" in channel.name or "welcome" in channel.name:
                    welcome_channel = channel
                    break
        
        if not welcome_channel:
            # No welcome channel found
            return
        
        # Create leave embed
        embed = discord.Embed(
            title=f"👋 Au revoir !",
            description=config.LEAVE_MESSAGE.format(
                member=member,
                member_count=len(member.guild.members)
            ),
            color=discord.Colour.light_grey()
        )
        
        # Set author with member name
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        
        # Set footer
        embed.set_footer(text=f"✧ {member.guild.name} • Made with 💖")
        
        # Send leave message
        await welcome_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Log when commands are used."""
        logger.info(f"Command '{ctx.command}' used by {ctx.author} in {ctx.guild}")
    
    @commands.command()
    async def ping(self, ctx):
        """Check the bot's latency."""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong !",
            description=f"Latence du bot: **{latency}ms**",
            color=discord.Colour.pink()
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    async def avatar(self, ctx, member: discord.Member = None):
        """Display a user's avatar."""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"Avatar de {member.name}",
            color=discord.Colour.pink()
        )
        
        # Add avatar URL at different sizes
        embed.set_image(url=member.display_avatar.url)
        embed.description = f"[Lien direct]({member.display_avatar.url})"
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):
        """Display information about a user."""
        member = member or ctx.author
        
        # Create embed
        embed = discord.Embed(
            title=f"Informations sur {member.name}",
            color=member.color
        )
        
        # Add user information
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add basic info
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Surnom", value=member.display_name, inline=True)
        embed.add_field(name="Bot", value="Oui" if member.bot else "Non", inline=True)
        
        # Add dates
        created_at = f"<t:{int(member.created_at.timestamp())}:R>"
        joined_at = f"<t:{int(member.joined_at.timestamp())}:R>"
        
        embed.add_field(name="Compte créé", value=created_at, inline=True)
        embed.add_field(name="A rejoint", value=joined_at, inline=True)
        
        # Add roles
        roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
        roles_str = " ".join(roles) if roles else "Aucun"
        
        embed.add_field(name=f"Rôles [{len(roles)}]", value=roles_str, inline=False)
        
        # Set footer
        embed.set_footer(text=f"✧ Ninis • Made with 💖")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def suggest(self, ctx, *, suggestion=None):
        """Submit a suggestion for the server."""
        if not suggestion:
            await ctx.send("❌ Tu dois inclure une suggestion !")
            return
        
        # Find suggestions channel, or use a default one
        suggestions_channel = discord.utils.get(ctx.guild.text_channels, name="💡・idées-du-staff")
        
        if not suggestions_channel:
            # Use current channel if no suggestions channel is found
            suggestions_channel = ctx.channel
        
        # Create suggestion embed
        embed = discord.Embed(
            title="💡 Nouvelle suggestion",
            description=suggestion,
            color=discord.Colour.gold()
        )
        
        # Add author info
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        # Add timestamp
        embed.timestamp = ctx.message.created_at
        
        # Set footer
        embed.set_footer(text=f"ID: {ctx.author.id}")
        
        # Send the suggestion and add reaction emojis for voting
        suggestion_message = await suggestions_channel.send(embed=embed)
        await suggestion_message.add_reaction("👍")
        await suggestion_message.add_reaction("👎")
        
        # Confirm to user if not in the suggestions channel
        if ctx.channel != suggestions_channel:
            await ctx.send(f"✅ Ta suggestion a été envoyée dans {suggestions_channel.mention} !")
            
    @commands.command()
    async def say(self, ctx, *, message=None):
        """Le bot répète ton message à l'identique et supprime ta commande."""
        if not message:
            await ctx.send("❌ Tu dois inclure un message. Usage: `!say <ton message>`", delete_after=5)
            return
        
        # Supprimer le message original
        try:
            await ctx.message.delete()
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du message: {e}")
        
        # Envoyer le même message avec le bot
        await ctx.send(message)

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(Utils(bot))
