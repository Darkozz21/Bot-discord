"""
Module Anti-link pour le Bot Chii.
Ce module détecte et supprime les liens postés par des non-administrateurs,
et gère un système d'avertissements pouvant mener au bannissement.
"""
import json
import os
import re
import discord
from discord.ext import commands
from discord import app_commands


class AntiLink(commands.Cog):
    """Module pour supprimer les liens et gérer les avertissements."""

    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}
        self.exempt_channels = set()
        self.link_pattern = re.compile(r'https?://\S+|www\.\S+|discord\.(gg|com/invite)/\S+')
        self.load_warnings()
    
    def load_warnings(self):
        """Charge les avertissements depuis un fichier."""
        try:
            if os.path.exists("warnings_data.json"):
                with open("warnings_data.json", "r") as f:
                    warnings_data = json.load(f)
                    # Convertir les clés de str à int
                    self.warnings = {int(k): v for k, v in warnings_data.items()}
                print(f"Avertissements chargés: {len(self.warnings)} utilisateurs")
        except Exception as e:
            print(f"Erreur lors du chargement des avertissements: {e}")
            self.warnings = {}
    
    def save_warnings(self):
        """Sauvegarde les avertissements dans un fichier."""
        try:
            with open("warnings_data.json", "w") as f:
                # Convertir les clés de int à str pour JSON
                warnings_data = {str(k): v for k, v in self.warnings.items()}
                json.dump(warnings_data, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des avertissements: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Vérifie chaque message pour détecter des liens non autorisés."""
        # Ignorer les messages du bot
        if message.author.bot:
            return
        
        # Ignorer les messages des administrateurs
        if message.guild and message.author.guild_permissions.administrator:
            return
        
        # Ignorer les messages dans les canaux exemptés
        if message.channel.id in self.exempt_channels:
            return
        
        # Vérifier si le message contient un lien
        if self.link_pattern.search(message.content):
            try:
                # Supprimer le message
                await message.delete()
                
                # Avertir l'utilisateur
                user_id = message.author.id
                if user_id not in self.warnings:
                    self.warnings[user_id] = {"count": 0, "reasons": []}
                
                self.warnings[user_id]["count"] += 1
                self.warnings[user_id]["reasons"].append("Envoi de lien non autorisé")
                
                warning_count = self.warnings[user_id]["count"]
                
                # Créer un embed pour l'avertissement
                embed = discord.Embed(
                    title="⚠️ Avertissement",
                    description=f"**{message.author.mention}, les liens ne sont pas autorisés !**",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="Avertissement",
                    value=f"C'est votre **{warning_count}ème** avertissement sur 5 avant bannissement."
                )
                
                # Envoyer l'avertissement
                warning_msg = await message.channel.send(embed=embed)
                
                # Bannir l'utilisateur s'il a atteint 5 avertissements
                if warning_count >= 5:
                    try:
                        # Créer un embed pour le bannissement
                        ban_embed = discord.Embed(
                            title="🔨 Bannissement",
                            description=f"**{message.author.name}** a été banni du serveur.",
                            color=discord.Color.red()
                        )
                        ban_embed.add_field(
                            name="Raison",
                            value=f"5 avertissements accumulés pour envoi de liens non autorisés."
                        )
                        
                        # Bannir l'utilisateur
                        await message.guild.ban(
                            message.author,
                            reason="5 avertissements pour envoi de liens non autorisés"
                        )
                        
                        # Envoyer la notification de ban
                        await message.channel.send(embed=ban_embed)
                        
                    except Exception as e:
                        print(f"Erreur lors du bannissement: {e}")
                
                # Sauvegarder les avertissements
                self.save_warnings()
                
            except Exception as e:
                print(f"Erreur dans le traitement anti-lien: {e}")
    
    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def warnings(self, ctx, member: discord.Member = None):
        """Affiche les avertissements d'un membre ou de tous les membres.
        
        Args:
            member: Le membre dont on veut voir les avertissements. Si non spécifié, affiche tous les avertissements.
        """
        if member:
            # Afficher les avertissements d'un membre spécifique
            user_id = member.id
            if user_id in self.warnings:
                warning_count = self.warnings[user_id]["count"]
                embed = discord.Embed(
                    title="⚠️ Avertissements",
                    description=f"**{member.name}** a **{warning_count}** avertissement(s).",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"**{member.name}** n'a aucun avertissement.")
        else:
            # Afficher tous les avertissements
            if not self.warnings:
                await ctx.send("Aucun avertissement enregistré.")
                return
            
            embed = discord.Embed(
                title="⚠️ Liste des avertissements",
                color=discord.Color.orange()
            )
            
            for user_id, warning_data in self.warnings.items():
                user = ctx.guild.get_member(user_id)
                if user:
                    embed.add_field(
                        name=f"{user.name}",
                        value=f"{warning_data['count']} avertissement(s)",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
    
    @commands.command(name="clearwarnings")
    @commands.has_permissions(administrator=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Supprime tous les avertissements d'un membre.
        
        Args:
            member: Le membre dont on veut supprimer les avertissements.
        """
        user_id = member.id
        if user_id in self.warnings:
            del self.warnings[user_id]
            self.save_warnings()
            await ctx.send(f"Les avertissements de **{member.name}** ont été supprimés.")
        else:
            await ctx.send(f"**{member.name}** n'a aucun avertissement.")
    
    @commands.command(name="addwarning")
    @commands.has_permissions(kick_members=True)
    async def addwarning(self, ctx, member: discord.Member, *, reason=None):
        """Ajoute un avertissement à un membre.
        
        Args:
            member: Le membre à avertir.
            reason: La raison de l'avertissement (optionnel).
        """
        user_id = member.id
        if user_id not in self.warnings:
            self.warnings[user_id] = {"count": 0, "reasons": []}
        
        self.warnings[user_id]["count"] += 1
        if reason:
            self.warnings[user_id]["reasons"].append(reason)
        else:
            self.warnings[user_id]["reasons"].append("Aucune raison spécifiée")
        
        warning_count = self.warnings[user_id]["count"]
        
        # Créer un embed pour l'avertissement
        embed = discord.Embed(
            title="⚠️ Avertissement ajouté",
            description=f"**{member.name}** a reçu un avertissement.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Total",
            value=f"**{warning_count}** avertissement(s)"
        )
        if reason:
            embed.add_field(
                name="Raison",
                value=reason,
                inline=False
            )
        
        # Bannir l'utilisateur s'il a atteint 5 avertissements
        if warning_count >= 5:
            try:
                # Créer un embed pour le bannissement
                ban_embed = discord.Embed(
                    title="🔨 Bannissement",
                    description=f"**{member.name}** a été banni du serveur.",
                    color=discord.Color.red()
                )
                ban_embed.add_field(
                    name="Raison",
                    value=f"5 avertissements accumulés."
                )
                
                # Bannir l'utilisateur
                await ctx.guild.ban(
                    member,
                    reason="5 avertissements accumulés"
                )
                
                # Envoyer la notification de ban
                await ctx.send(embed=ban_embed)
                
            except Exception as e:
                print(f"Erreur lors du bannissement: {e}")
                await ctx.send(f"Erreur lors du bannissement: {e}")
        else:
            # Envoyer l'avertissement
            await ctx.send(embed=embed)
        
        # Sauvegarder les avertissements
        self.save_warnings()
    
    @commands.command(name="exempt_channel")
    @commands.has_permissions(administrator=True)
    async def exempt_channel(self, ctx, channel: discord.TextChannel = None):
        """Exempte un canal de la vérification des liens.
        
        Args:
            channel: Le canal à exempter. Si non spécifié, utilise le canal actuel.
        """
        if channel is None:
            channel = ctx.channel
        
        self.exempt_channels.add(channel.id)
        await ctx.send(f"Le canal {channel.mention} est maintenant exempté de la vérification anti-lien.")
    
    @commands.command(name="unexempt_channel")
    @commands.has_permissions(administrator=True)
    async def unexempt_channel(self, ctx, channel: discord.TextChannel = None):
        """Retire l'exemption d'un canal pour la vérification des liens.
        
        Args:
            channel: Le canal à non-exempter. Si non spécifié, utilise le canal actuel.
        """
        if channel is None:
            channel = ctx.channel
        
        if channel.id in self.exempt_channels:
            self.exempt_channels.remove(channel.id)
            await ctx.send(f"Le canal {channel.mention} n'est plus exempté de la vérification anti-lien.")
        else:
            await ctx.send(f"Le canal {channel.mention} n'était pas exempté.")


async def setup(bot):
    """Fonction d'installation du cog."""
    await bot.add_cog(AntiLink(bot))
    print(f"Module Anti-Link chargé avec succès.")