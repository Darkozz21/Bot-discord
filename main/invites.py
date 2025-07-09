"""
Module de suivi des invitations pour le Bot Chii.
Ce module permet de suivre qui a invité chaque membre et combien d'invitations chaque personne a générées.
"""

import json
import logging
import discord
from discord.ext import commands

# Configuration du logger
logger = logging.getLogger('ninis_bot')

class Invites(commands.Cog):
    """Système de suivi des invitations."""
    
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}
        self.invite_uses = {}
        self.data_file = 'invites_data.json'
        self.load_data()
        
        # Cette variable est importante pour éviter de bloquer au démarrage
        self.ready = False
        
        # Lancer la tâche d'initialisation
        self.bot.loop.create_task(self.initialize())
    
    async def initialize(self):
        """Initialise le cache des invitations après le démarrage du bot."""
        await self.bot.wait_until_ready()
        try:
            for guild in self.bot.guilds:
                # Récupérer toutes les invitations du serveur
                try:
                    self.invites[guild.id] = {}
                    invites = await guild.invites()
                    
                    for invite in invites:
                        self.invites[guild.id][invite.code] = invite.uses
                        
                        # Mettre à jour l'utilisation totale des invitations
                        inviter_id = str(invite.inviter.id) if invite.inviter else "unknown"
                        if guild.id not in self.invite_uses:
                            self.invite_uses[guild.id] = {}
                        
                        if inviter_id not in self.invite_uses[guild.id]:
                            self.invite_uses[guild.id][inviter_id] = 0
                    
                    logger.info(f"Invitations initialisées pour {guild.name}: {len(invites)} invitations trouvées")
                except Exception as e:
                    logger.error(f"Erreur lors de l'initialisation des invitations pour {guild.name}: {e}")
            
            # Marquer comme prêt
            self.ready = True
            self.save_data()
            logger.info("Module d'invitations initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur globale lors de l'initialisation des invitations: {e}")
    
    def load_data(self):
        """Charge les données d'invitations depuis le fichier JSON."""
        try:
            import os
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convertir les clés de guild_id en entiers
                    self.invite_uses = {int(k): v for k, v in data.items()}
                    logger.info(f"Données d'invitations chargées: {len(self.invite_uses)} serveurs")
            else:
                self.invite_uses = {}
                logger.info("Aucun fichier de données d'invitations trouvé, initialisation à vide")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données d'invitations: {e}")
            self.invite_uses = {}
    
    def save_data(self):
        """Sauvegarde les données d'invitations dans le fichier JSON."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.invite_uses, f, indent=4)
            logger.info("Données d'invitations sauvegardées")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données d'invitations: {e}")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Met à jour le cache des invitations quand le bot rejoint un nouveau serveur."""
        try:
            self.invites[guild.id] = {}
            invites = await guild.invites()
            
            for invite in invites:
                self.invites[guild.id][invite.code] = invite.uses
            
            logger.info(f"Cache d'invitations initialisé pour le nouveau serveur {guild.name}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des invitations pour le nouveau serveur {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Nettoie les données quand le bot quitte un serveur."""
        try:
            if guild.id in self.invites:
                del self.invites[guild.id]
            
            if guild.id in self.invite_uses:
                del self.invite_uses[guild.id]
            
            self.save_data()
            logger.info(f"Données d'invitations nettoyées pour le serveur {guild.name}")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des données d'invitations pour {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Met à jour le cache quand une nouvelle invitation est créée."""
        try:
            guild_id = invite.guild.id
            if guild_id not in self.invites:
                self.invites[guild_id] = {}
            
            self.invites[guild_id][invite.code] = invite.uses
            logger.info(f"Nouvelle invitation {invite.code} ajoutée au cache pour {invite.guild.name}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du cache pour la nouvelle invitation: {e}")
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Met à jour le cache quand une invitation est supprimée."""
        try:
            guild_id = invite.guild.id
            if guild_id in self.invites and invite.code in self.invites[guild_id]:
                del self.invites[guild_id][invite.code]
                logger.info(f"Invitation {invite.code} supprimée du cache pour {invite.guild.name}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du cache pour l'invitation supprimée: {e}")
    
    async def find_used_invite(self, guild):
        """
        Détermine quelle invitation a été utilisée pour rejoindre le serveur.
        
        Args:
            guild: Le serveur à vérifier
            
        Returns:
            tuple: (code d'invitation, inviteur, nombre d'utilisations de l'inviteur)
                  ou (None, None, 0) si aucune invitation n'est trouvée
        """
        # Si le module n'est pas prêt, retourner None
        if not self.ready:
            return None, None, 0
        
        # Si le serveur n'est pas dans le cache, initialiser
        if guild.id not in self.invites:
            self.invites[guild.id] = {}
            logger.warning(f"Le serveur {guild.name} n'était pas dans le cache d'invitations")
        
        # Récupérer l'état avant l'invitation
        invites_before = self.invites[guild.id].copy()
        
        try:
            # Récupérer les invitations actuelles
            current_invites = await guild.invites()
            
            # Mettre à jour le cache
            self.invites[guild.id] = {invite.code: invite.uses for invite in current_invites}
            
            # Chercher l'invitation utilisée
            for invite in current_invites:
                # Si l'invitation n'était pas dans le cache avant ou si son compteur a augmenté
                if invite.code not in invites_before or invite.uses > invites_before[invite.code]:
                    # Mettre à jour le compteur total d'invitations de l'inviteur
                    if guild.id not in self.invite_uses:
                        self.invite_uses[guild.id] = {}
                    
                    inviter_id = str(invite.inviter.id) if invite.inviter else "unknown"
                    
                    if inviter_id not in self.invite_uses[guild.id]:
                        self.invite_uses[guild.id][inviter_id] = 1
                    else:
                        self.invite_uses[guild.id][inviter_id] += 1
                    
                    # Sauvegarder les données
                    self.save_data()
                    
                    # Retourner les informations
                    return invite.code, invite.inviter, self.invite_uses[guild.id][inviter_id]
            
            # Si aucune invitation n'a été trouvée
            logger.warning(f"Aucune invitation utilisée trouvée pour {guild.name}")
            return None, None, 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de l'invitation utilisée: {e}")
            return None, None, 0
    
    @commands.command()
    async def invites(self, ctx, member: discord.Member = None):
        """Affiche le nombre d'invitations générées par un membre.
        
        Args:
            member: Le membre dont on veut voir les invitations. Si non spécifié, affiche les invitations de l'auteur de la commande.
        """
        member = member or ctx.author
        
        if ctx.guild.id not in self.invite_uses:
            await ctx.send(f"{member.mention} n'a pas encore invité de personnes sur ce serveur.")
            return
        
        member_id = str(member.id)
        invite_count = self.invite_uses[ctx.guild.id].get(member_id, 0)
        
        if invite_count == 0:
            await ctx.send(f"{member.mention} n'a pas encore invité de personnes sur ce serveur.")
        else:
            plural = "s" if invite_count > 1 else ""
            await ctx.send(f"🎉 {member.mention} a invité **{invite_count}** personne{plural} sur ce serveur !")
    
    @commands.command()
    async def topinvites(self, ctx):
        """Affiche le classement des membres qui ont invité le plus de personnes."""
        if ctx.guild.id not in self.invite_uses or not self.invite_uses[ctx.guild.id]:
            await ctx.send("Aucune invitation n'a encore été utilisée sur ce serveur.")
            return
        
        # Trier les membres par nombre d'invitations
        sorted_inviters = sorted(
            self.invite_uses[ctx.guild.id].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Limiter à 10 membres
        top_inviters = sorted_inviters[:10]
        
        # Créer l'embed
        embed = discord.Embed(
            title="🏆 Classement des Invitations",
            description="Les membres ayant invité le plus de personnes",
            color=discord.Colour.pink()
        )
        
        # Générer la liste des membres
        leaderboard_text = ""
        for i, (inviter_id, count) in enumerate(top_inviters):
            # Gérer le cas spécial "unknown"
            if inviter_id == "unknown":
                member_name = "Inviteur inconnu"
            else:
                # Obtenir le membre depuis l'ID
                member = ctx.guild.get_member(int(inviter_id))
                member_name = member.display_name if member else f"Utilisateur {inviter_id}"
            
            # Emoji pour les 3 premiers
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
            
            # Pluriel
            plural = "s" if count > 1 else ""
            
            leaderboard_text += f"{medal} **{member_name}** • {count} invitation{plural}\n"
        
        if not leaderboard_text:
            leaderboard_text = "Aucune invitation trouvée."
        
        embed.description = leaderboard_text
        embed.set_footer(text="✨ Invite tes amis pour faire grandir notre communauté ! ✨")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Installer le module d'invitations."""
    await bot.add_cog(Invites(bot))