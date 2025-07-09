"""
TikTok notifications cog for the Ninis discord bot.
This cog checks for new TikTok lives and posts and sends notifications to a dedicated channel.
"""
import logging
import os
import json
import time
import asyncio
import datetime
import discord
from discord.ext import commands, tasks
import aiohttp
import requests
import config

# Set up logging
logger = logging.getLogger('ninis_bot')

# File to store the last checked TikTok data
CACHE_FILE = "tiktok_cache.json"

class TikTok(commands.Cog):
    """Commands and tasks for TikTok notifications."""
    
    def __init__(self, bot):
        self.bot = bot
        self.tiktok_usernames = {}  # Map Discord user IDs to TikTok usernames
        self.last_video_time = {}  # Store the timestamp of the most recent video for each user
        self.live_status = {}  # Store whether each user is currently live
        self.checking_interval = 5 * 60  # Check every 5 minutes by default
        self.load_cache()
        self.check_tiktok_updates.start()
    
    def cog_unload(self):
        """Called when the cog is unloaded."""
        self.check_tiktok_updates.cancel()
        self.save_cache()
    
    def load_cache(self):
        """Load the cached TikTok data from file."""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    self.tiktok_usernames = cache_data.get('tiktok_usernames', {})
                    self.last_video_time = cache_data.get('last_video_time', {})
                    self.live_status = cache_data.get('live_status', {})
                    logger.info(f"TikTok cache loaded with {len(self.tiktok_usernames)} accounts")
        except Exception as e:
            logger.error(f"Error loading TikTok cache: {e}")
    
    def save_cache(self):
        """Save the TikTok data to a cache file."""
        try:
            cache_data = {
                'tiktok_usernames': self.tiktok_usernames,
                'last_video_time': self.last_video_time,
                'live_status': self.live_status
            }
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
                logger.info("TikTok cache saved")
        except Exception as e:
            logger.error(f"Error saving TikTok cache: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_tiktok(self, ctx, discord_member: discord.Member):
        """Connect a Discord member to the Ninis TikTok account for notifications."""
        # Hardcoded TikTok username - only works with @yannlln
        tiktok_username = "yannlln"
        
        # Store the mapping
        self.tiktok_usernames[str(discord_member.id)] = tiktok_username
        self.save_cache()
        
        # Confirm to the user
        embed = discord.Embed(
            title="✅ Compte TikTok associé",
            description=f"Les notifications pour les vidéos et lives de **@{tiktok_username}** "
                        f"seront maintenant envoyées pour {discord_member.mention}.",
            color=discord.Colour.pink()
        )
        embed.set_footer(text="✧ Ninis • Made with 💖")
        
        await ctx.send(embed=embed)
        
        # Check immediately for any content
        await self.check_account(discord_member.id, tiktok_username, True)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def remove_tiktok(self, ctx, discord_member: discord.Member):
        """Remove TikTok notifications for a Discord member."""
        member_id = str(discord_member.id)
        if member_id in self.tiktok_usernames:
            tiktok_username = self.tiktok_usernames[member_id]
            del self.tiktok_usernames[member_id]
            if member_id in self.last_video_time:
                del self.last_video_time[member_id]
            if member_id in self.live_status:
                del self.live_status[member_id]
            self.save_cache()
            
            embed = discord.Embed(
                title="✅ Association supprimée",
                description=f"Les notifications TikTok pour {discord_member.mention} (@{tiktok_username}) ont été désactivées.",
                color=discord.Colour.red()
            )
            embed.set_footer(text="✧ Ninis • Made with 💖")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {discord_member.mention} n'est pas associé à un compte TikTok.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def list_tiktok(self, ctx):
        """List all registered TikTok accounts for notification."""
        if not self.tiktok_usernames:
            await ctx.send("❌ Aucun compte TikTok n'est enregistré pour les notifications.")
            return
        
        embed = discord.Embed(
            title="📱 Comptes TikTok enregistrés",
            description="Liste des membres avec notifications TikTok activées:",
            color=discord.Colour.pink()
        )
        
        for discord_id, tiktok_username in self.tiktok_usernames.items():
            member = ctx.guild.get_member(int(discord_id))
            if member:
                embed.add_field(
                    name=f"{member.display_name}",
                    value=f"TikTok: @{tiktok_username}",
                    inline=False
                )
        
        embed.set_footer(text="✧ Ninis • Made with 💖")
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def check_tiktok_now(self, ctx):
        """Force an immediate check for TikTok updates."""
        if not self.tiktok_usernames:
            await ctx.send("❌ Aucun compte TikTok n'est enregistré pour les notifications.")
            return
        
        message = await ctx.send("⏳ Vérification des comptes TikTok en cours...")
        
        # Manually run the check
        await self.check_all_accounts(True)
        
        await message.edit(content="✅ Vérification terminée.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_tiktok_interval(self, ctx, minutes: int):
        """Set how often to check for TikTok updates (in minutes)."""
        if minutes < 1:
            await ctx.send("❌ L'intervalle doit être d'au moins 1 minute.")
            return
        
        self.checking_interval = minutes * 60
        
        # Restart the task with the new interval
        self.check_tiktok_updates.cancel()
        self.check_tiktok_updates.change_interval(seconds=self.checking_interval)
        self.check_tiktok_updates.start()
        
        await ctx.send(f"✅ L'intervalle de vérification TikTok est maintenant de {minutes} minutes.")
    
    @tasks.loop(seconds=300)  # Default: check every 5 minutes
    async def check_tiktok_updates(self):
        """Background task to periodically check for TikTok updates."""
        await self.check_all_accounts()
    
    @check_tiktok_updates.before_loop
    async def before_check_tiktok(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
        logger.info("TikTok notifications task is starting")
    
    async def check_all_accounts(self, verbose=False):
        """Check all registered TikTok accounts for updates."""
        try:
            # Skip if no accounts are registered
            if not self.tiktok_usernames:
                if verbose:
                    logger.info("No TikTok accounts registered for checking")
                return
            
            logger.info(f"Checking {len(self.tiktok_usernames)} TikTok accounts for updates")
            
            # Check each account
            for discord_id, tiktok_username in self.tiktok_usernames.items():
                try:
                    await self.check_account(int(discord_id), tiktok_username, verbose)
                    # Add a small delay between requests to avoid rate limiting
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error checking TikTok account @{tiktok_username}: {e}")
            
            # Save cache after checking all accounts
            self.save_cache()
            
        except Exception as e:
            logger.error(f"Error in check_all_accounts: {e}")
    
    async def check_account(self, discord_id, tiktok_username, verbose=False):
        """Check a single TikTok account for updates."""
        try:
            str_discord_id = str(discord_id)
            
            # Simulate checking TikTok API (replace with real API calls when available)
            # In production code, you'd use the TikTok API to fetch this data
            current_time = int(time.time())
            
            # Simulate checking for new videos (in real implementation, use TikTok API)
            # Here we'll just demonstrate the notification system
            if str_discord_id not in self.last_video_time:
                # First time checking, just store the current time
                self.last_video_time[str_discord_id] = current_time
                logger.info(f"First check for @{tiktok_username}, setting baseline timestamp")
            else:
                # Check if there's a new video by comparing timestamps
                # In a real implementation, you'd compare with the actual video post time from the API
                if verbose:
                    # If in verbose mode and first check, send a sample notification
                    if self.last_video_time[str_discord_id] == current_time:
                        # For first notification only, simulate a "new video" for demonstration
                        await self.send_new_video_notification(discord_id, tiktok_username)
                
            # Similarly check for live status (in real implementation, use TikTok API)
            was_live = self.live_status.get(str_discord_id, False)
            
            # In a real implementation, you'd check the actual live status
            # For our example, we'll just demonstrate notifications
            if verbose and str_discord_id not in self.live_status:
                # First time running and verbose mode, send sample notification
                await self.send_live_notification(discord_id, tiktok_username, True)
                self.live_status[str_discord_id] = False  # Mark as not live after demo notification
            
        except Exception as e:
            logger.error(f"Error checking account @{tiktok_username}: {e}")
    
    async def send_new_video_notification(self, discord_id, tiktok_username):
        """Send a notification for a new TikTok video."""
        try:
            # Get all guilds the bot is in
            for guild in self.bot.guilds:
                # Check if the user is in this guild
                member = guild.get_member(discord_id)
                if not member:
                    continue
                
                # Look for a notifications channel
                notifications_channel = discord.utils.get(
                    guild.text_channels, 
                    name="📱・notifications-tiktok"
                )
                
                if not notifications_channel:
                    # Try to find alternative channels
                    for channel in guild.text_channels:
                        if "notif" in channel.name or "tiktok" in channel.name:
                            notifications_channel = channel
                            break
                
                if not notifications_channel:
                    # No appropriate channel found, skip this guild
                    continue
                
                # Get the notifications role
                notification_role = discord.utils.get(guild.roles, name="🔔 Notifications TikTok")
                ping_message = ""
                
                if notification_role:
                    ping_message = f"{notification_role.mention}"
                
                # Create an embed for the notification
                embed = discord.Embed(
                    title="🎬 Nouvelle vidéo TikTok !",
                    description=f"{member.mention} vient de poster une nouvelle vidéo sur TikTok !",
                    color=discord.Colour.pink(),
                    url=f"https://www.tiktok.com/@{tiktok_username}"
                )
                
                embed.add_field(
                    name="Créateur",
                    value=f"@{tiktok_username}",
                    inline=True
                )
                
                embed.add_field(
                    name="Voir maintenant",
                    value=f"[Ouvrir TikTok](https://www.tiktok.com/@{tiktok_username})",
                    inline=True
                )
                
                embed.set_footer(text=f"✧ Ninis • {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
                
                # Set author with member avatar
                embed.set_author(
                    name=f"Nouvelle vidéo de {member.display_name}", 
                    icon_url=member.display_avatar.url
                )
                
                # Send the notification
                await notifications_channel.send(content=ping_message, embed=embed)
                logger.info(f"Sent new video notification for @{tiktok_username} in {guild.name}")
                
        except Exception as e:
            logger.error(f"Error sending new video notification for @{tiktok_username}: {e}")
    
    async def send_live_notification(self, discord_id, tiktok_username, is_live):
        """Send a notification for TikTok live status changes."""
        try:
            # Only notify if status changed (going live or ending stream)
            if is_live:
                # User is now live
                
                # Get all guilds the bot is in
                for guild in self.bot.guilds:
                    # Check if the user is in this guild
                    member = guild.get_member(discord_id)
                    if not member:
                        continue
                    
                    # Look for a notifications channel
                    notifications_channel = discord.utils.get(
                        guild.text_channels, 
                        name="📱・notifications-tiktok"
                    )
                    
                    if not notifications_channel:
                        # Try to find alternative channels
                        for channel in guild.text_channels:
                            if "notif" in channel.name or "tiktok" in channel.name:
                                notifications_channel = channel
                                break
                    
                    if not notifications_channel:
                        # No appropriate channel found, skip this guild
                        continue
                    
                    # Create an embed for the notification
                    embed = discord.Embed(
                        title="🔴 LIVE TikTok en cours !",
                        description=f"{member.mention} est actuellement en LIVE sur TikTok !",
                        color=discord.Colour.red(),
                        url=f"https://www.tiktok.com/@{tiktok_username}/live"
                    )
                    
                    embed.add_field(
                        name="Créateur",
                        value=f"@{tiktok_username}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Regarder maintenant",
                        value=f"[Rejoindre le LIVE](https://www.tiktok.com/@{tiktok_username}/live)",
                        inline=True
                    )
                    
                    embed.set_footer(text=f"✧ Ninis • {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    
                    # Set author with member avatar
                    embed.set_author(
                        name=f"{member.display_name} est en LIVE !", 
                        icon_url=member.display_avatar.url
                    )
                    
                    # Get the notifications role
                    notification_role = discord.utils.get(guild.roles, name="🔔 Notifications TikTok")
                    ping_message = ""
                    
                    if notification_role:
                        ping_message = f"{notification_role.mention}"
                    
                    # Send the notification
                    await notifications_channel.send(content=ping_message, embed=embed)
                    logger.info(f"Sent live notification for @{tiktok_username} in {guild.name}")
            
        except Exception as e:
            logger.error(f"Error sending live notification for @{tiktok_username}: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def create_tiktok_channel(self, ctx):
        """Create a dedicated TikTok notifications channel and role."""
        # Check if the channel already exists
        existing_channel = discord.utils.get(ctx.guild.text_channels, name="📱・notifications-tiktok")
        
        # Check if the notification role already exists
        notification_role = discord.utils.get(ctx.guild.roles, name="🔔 Notifications TikTok")
        
        if not notification_role:
            try:
                # Create a role for TikTok notifications
                notification_role = await ctx.guild.create_role(
                    name="🔔 Notifications TikTok",
                    color=discord.Colour(0xFF69B4),  # Hot pink
                    mentionable=True,
                    reason="Rôle pour les notifications TikTok"
                )
                logger.info(f"Rôle '🔔 Notifications TikTok' créé pour les notifications")
                
                # Envoi d'un message de confirmation pour le rôle
                role_embed = discord.Embed(
                    title="✅ Rôle de notifications TikTok créé",
                    description=f"Le rôle {notification_role.mention} a été créé. Les membres peuvent s'assigner ce rôle pour recevoir les notifications TikTok.",
                    color=discord.Colour.green()
                )
                await ctx.send(embed=role_embed)
                
            except Exception as e:
                logger.error(f"Erreur lors de la création du rôle '🔔 Notifications TikTok': {e}")
                await ctx.send(f"❌ Erreur lors de la création du rôle: {e}")
                return
        
        if existing_channel:
            await ctx.send(f"⚠️ Le salon {existing_channel.mention} existe déjà.")
            return
        
        # Create the channel
        try:
            # Find or create a Notifications category
            category = discord.utils.get(ctx.guild.categories, name="🔔 NOTIFICATIONS")
            
            if not category:
                # Look for other notification-like categories
                for cat in ctx.guild.categories:
                    if "notif" in cat.name.lower() or "annonce" in cat.name.lower():
                        category = cat
                        break
            
            if not category:
                # Create a new category
                category = await ctx.guild.create_category(name="🔔 NOTIFICATIONS")
                logger.info(f"Created new category '🔔 NOTIFICATIONS' in {ctx.guild.name}")
            
            # Create permissions overwrites for the channel
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False
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
                name="📱・notifications-tiktok",
                category=category,
                overwrites=overwrites,
                topic="Notifications automatiques pour les lives et vidéos TikTok"
            )
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Salon de notifications TikTok créé",
                description=f"Le salon {channel.mention} a été créé pour recevoir les notifications TikTok.\n\n"
                            f"Utilisez `!set_tiktok @membre nom_utilisateur_tiktok` pour configurer les notifications.\n\n"
                            f"Les membres peuvent s'assigner le rôle {notification_role.mention} pour être notifiés.",
                color=discord.Colour.green()
            )
            
            embed.add_field(
                name="Commandes disponibles",
                value="`!set_tiktok` - Associer un compte TikTok\n"
                      "`!remove_tiktok` - Retirer un compte TikTok\n"
                      "`!list_tiktok` - Lister les comptes configurés\n"
                      "`!check_tiktok_now` - Vérifier maintenant\n"
                      "`!toggle_tiktok_ping` - Activer/désactiver les notifications",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Send welcome message in the new channel
            welcome_embed = discord.Embed(
                title="📱 Notifications TikTok",
                description=f"Ce salon affichera automatiquement des notifications quand:\n"
                            f"• Un membre enregistré commence un LIVE TikTok\n"
                            f"• Un membre enregistré publie une nouvelle vidéo TikTok\n\n"
                            f"Pour recevoir des notifications, prenez le rôle {notification_role.mention}.\n"
                            f"Un administrateur doit associer les comptes Discord aux comptes TikTok.",
                color=discord.Colour.pink()
            )
            
            welcome_embed.set_footer(text="✧ Ninis • Made with 💖")
            
            await channel.send(embed=welcome_embed)
            
        except Exception as e:
            logger.error(f"Error creating TikTok notifications channel: {e}")
            await ctx.send(f"❌ Erreur lors de la création du salon: {e}")

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(TikTok(bot))