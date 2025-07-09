"""
Moderation cog for the Ninis discord bot.
"""
import logging
import discord
from discord.ext import commands

# Set up logging
logger = logging.getLogger('ninis_bot')

class Moderation(commands.Cog):
    """Commands for server moderation."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5):
        """Clear a specified number of messages from the channel."""
        if amount <= 0 or amount > 100:
            await ctx.send("❌ Le nombre de messages à supprimer doit être entre 1 et 100.")
            return
        
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        
        # Send confirmation that auto-deletes after 5 seconds
        confirm_message = await ctx.send(f"✅ {len(deleted)-1} messages ont été supprimés.")
        await confirm_message.delete(delay=5)
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick a member from the server."""
        # Check if the bot can kick the member
        if not ctx.guild.me.top_role > member.top_role:
            await ctx.send("❌ Je ne peux pas expulser ce membre car son rôle est supérieur au mien.")
            return
        
        # Check if the user can kick the member
        if not ctx.author.top_role > member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Tu ne peux pas expulser ce membre car son rôle est supérieur au tien.")
            return
        
        # Handle reason
        reason = reason or "Aucune raison spécifiée"
        
        # Attempt to send a DM to the user
        try:
            embed = discord.Embed(
                title="❌ Expulsion",
                description=f"Tu as été expulsé(e) du serveur **{ctx.guild.name}**",
                color=discord.Colour.red()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            
            await member.send(embed=embed)
        except discord.HTTPException:
            # Couldn't send DM
            pass
        
        # Kick the member
        try:
            await ctx.guild.kick(member, reason=f"{ctx.author}: {reason}")
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Membre expulsé",
                description=f"{member.mention} a été expulsé(e) du serveur.",
                color=discord.Colour.green()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logger.info(f"Member {member} kicked by {ctx.author} for: {reason}")
            
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission d'expulser ce membre.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Une erreur est survenue: {e}")
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member from the server."""
        # Check if the bot can ban the member
        if not ctx.guild.me.top_role > member.top_role:
            await ctx.send("❌ Je ne peux pas bannir ce membre car son rôle est supérieur au mien.")
            return
        
        # Check if the user can ban the member
        if not ctx.author.top_role > member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Tu ne peux pas bannir ce membre car son rôle est supérieur au tien.")
            return
        
        # Handle reason
        reason = reason or "Aucune raison spécifiée"
        
        # Attempt to send a DM to the user
        try:
            embed = discord.Embed(
                title="🔨 Bannissement",
                description=f"Tu as été banni(e) du serveur **{ctx.guild.name}**",
                color=discord.Colour.red()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            
            await member.send(embed=embed)
        except discord.HTTPException:
            # Couldn't send DM
            pass
        
        # Ban the member
        try:
            await ctx.guild.ban(member, reason=f"{ctx.author}: {reason}", delete_message_days=1)
            
            # Send confirmation
            embed = discord.Embed(
                title="🔨 Membre banni",
                description=f"{member.mention} a été banni(e) du serveur.",
                color=discord.Colour.red()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logger.info(f"Member {member} banned by {ctx.author} for: {reason}")
            
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de bannir ce membre.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Une erreur est survenue: {e}")
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason=None):
        """Unban a user by their ID."""
        reason = reason or "Aucune raison spécifiée"
        
        try:
            # Get the ban entry
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            user = ban_entry.user
            
            # Unban the user
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Utilisateur débanni",
                description=f"{user.mention} a été débanni(e) du serveur.",
                color=discord.Colour.green()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logger.info(f"User {user} unbanned by {ctx.author} for: {reason}")
            
        except discord.NotFound:
            await ctx.send("❌ Ce membre n'est pas banni ou l'ID est incorrect.")
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de débannir ce membre.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Une erreur est survenue: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        """Timeout a member (mute)."""
        # Check if the bot can mute the member
        if not ctx.guild.me.top_role > member.top_role:
            await ctx.send("❌ Je ne peux pas rendre muet ce membre car son rôle est supérieur au mien.")
            return
        
        # Check if the user can mute the member
        if not ctx.author.top_role > member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Tu ne peux pas rendre muet ce membre car son rôle est supérieur au tien.")
            return
        
        # Handle reason
        reason = reason or "Aucune raison spécifiée"
        
        try:
            # Use Discord's built-in timeout feature (28 days max)
            import datetime
            from discord.utils import utcnow
            until = utcnow() + datetime.timedelta(minutes=60)  # 1 hour timeout
            await member.timeout(until, reason=f"{ctx.author}: {reason}")
            
            # Send confirmation
            embed = discord.Embed(
                title="🔇 Membre rendu muet",
                description=f"{member.mention} a été rendu muet pour 1 heure.",
                color=discord.Colour.orange()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            embed.add_field(name="Durée", value="1 heure", inline=False)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logger.info(f"Member {member} muted by {ctx.author} for: {reason}")
            
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de rendre muet ce membre.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Une erreur est survenue: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unmute(self, ctx, member: discord.Member, *, reason=None):
        """Remove timeout from a member (unmute)."""
        # Handle reason
        reason = reason or "Aucune raison spécifiée"
        
        try:
            # Remove timeout
            await member.timeout(None, reason=f"{ctx.author}: {reason}")
            
            # Send confirmation
            embed = discord.Embed(
                title="🔊 Membre réactivé",
                description=f"{member.mention} n'est plus muet.",
                color=discord.Colour.green()
            )
            embed.add_field(name="Raison", value=reason)
            embed.add_field(name="Modérateur", value=ctx.author.mention)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logger.info(f"Member {member} unmuted by {ctx.author} for: {reason}")
            
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas la permission de réactiver ce membre.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Une erreur est survenue: {e}")

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(Moderation(bot))
