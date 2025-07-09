"""
Emoji cog for the Ninis discord bot.
This cog handles adding and managing server emojis.
"""
import logging
import os
import discord
from discord.ext import commands
import aiohttp
import io
import random
import asyncio
import traceback

# Set up logging
logger = logging.getLogger('ninis_bot')

# Liste d'émojis anime
ANIME_EMOJIS = [
    {"name": "anime_happy", "url": "https://i.imgur.com/HrvVfJJ.gif"},
    {"name": "anime_cry", "url": "https://i.imgur.com/FnTjXfK.gif"},
    {"name": "anime_love", "url": "https://i.imgur.com/lgM6oTe.gif"},
    {"name": "anime_dance", "url": "https://i.imgur.com/Ucdh0V0.gif"},
    {"name": "anime_shy", "url": "https://i.imgur.com/fOD3Ho1.gif"},
    {"name": "anime_wink", "url": "https://i.imgur.com/RnYICun.gif"},
    {"name": "anime_neko", "url": "https://i.imgur.com/xtD4EPl.gif"},
    {"name": "anime_sleep", "url": "https://i.imgur.com/Ys6YfaZ.gif"},
    {"name": "anime_pout", "url": "https://i.imgur.com/gy7Xt5w.gif"},
    {"name": "anime_blush", "url": "https://i.imgur.com/56hAf1C.gif"},
    {"name": "anime_pat", "url": "https://i.imgur.com/xtVLdi5.gif"},
    {"name": "anime_laugh", "url": "https://i.imgur.com/CaX4A3f.gif"},
    {"name": "anime_hug", "url": "https://i.imgur.com/7QolYQm.gif"},
    {"name": "anime_wave", "url": "https://i.imgur.com/XVNQ3BU.gif"},
    {"name": "anime_kiss", "url": "https://i.imgur.com/QGHnvDa.gif"},
    {"name": "anime_smile", "url": "https://i.imgur.com/1Yfuwu7.gif"},
    {"name": "anime_uwu", "url": "https://i.imgur.com/kVfIlsv.gif"},
    {"name": "anime_sad", "url": "https://i.imgur.com/uaqT6QZ.gif"},
    {"name": "anime_wow", "url": "https://i.imgur.com/YcJetXL.gif"},
    {"name": "anime_think", "url": "https://i.imgur.com/STgCgI5.gif"},
    {"name": "anime_angry", "url": "https://i.imgur.com/gAcse7N.gif"},
    {"name": "anime_thumbsup", "url": "https://i.imgur.com/YvAkrRA.gif"},
    {"name": "anime_sparkle", "url": "https://i.imgur.com/m7g9GYf.gif"},
    {"name": "anime_nod", "url": "https://i.imgur.com/ZY0nPPY.gif"},
    {"name": "anime_heart", "url": "https://i.imgur.com/S5B1VCm.gif"}
]

# Liste d'émojis basiques/tendance
BASIC_EMOJIS = [
    {"name": "kawaii_heart", "url": "https://i.imgur.com/kQD6Ysj.png"},
    {"name": "sparkle", "url": "https://i.imgur.com/Z9DcRVt.png"},
    {"name": "butterfly", "url": "https://i.imgur.com/xqQB1o0.png"},
    {"name": "star_pink", "url": "https://i.imgur.com/MAtpHEK.png"},
    {"name": "cloud", "url": "https://i.imgur.com/0PJ5Qz8.png"},
    {"name": "rainbow", "url": "https://i.imgur.com/Q5L3EJh.png"},
    {"name": "flower_pink", "url": "https://i.imgur.com/7dkAtxp.png"},
    {"name": "moon", "url": "https://i.imgur.com/R6iW6UF.png"},
    {"name": "cherry", "url": "https://i.imgur.com/BLxxPwE.png"},
    {"name": "crown", "url": "https://i.imgur.com/cZM2S0X.png"},
    {"name": "strawberry", "url": "https://i.imgur.com/1TYjtzj.png"},
    {"name": "happy_face", "url": "https://i.imgur.com/pGPyj9j.png"},
    {"name": "angel", "url": "https://i.imgur.com/5wt5xue.png"},
    {"name": "devil", "url": "https://i.imgur.com/aXYIulU.png"},
    {"name": "pink_heart", "url": "https://i.imgur.com/l86SjBt.png"},
    {"name": "blue_heart", "url": "https://i.imgur.com/BBpT7pZ.png"},
    {"name": "purple_heart", "url": "https://i.imgur.com/QShCg1h.png"},
    {"name": "green_heart", "url": "https://i.imgur.com/DUljI0c.png"},
    {"name": "yellow_heart", "url": "https://i.imgur.com/0Vxl1fU.png"},
    {"name": "black_heart", "url": "https://i.imgur.com/7iP0QOt.png"},
    {"name": "white_heart", "url": "https://i.imgur.com/HxDJKZ7.png"},
    {"name": "bow", "url": "https://i.imgur.com/IixTPaZ.png"},
    {"name": "star_shine", "url": "https://i.imgur.com/MdWY8Fb.png"},
    {"name": "pearl", "url": "https://i.imgur.com/gPLG47U.png"},
    {"name": "flower_white", "url": "https://i.imgur.com/M5a9KXe.png"}
]

class Emoji(commands.Cog):
    """Commandes pour gérer les émojis du serveur."""
    
    def __init__(self, bot):
        self.bot = bot
        self._session = None  # Initialisation la session à None
        logger.info("Module Emoji initialisé")
    
    def cog_unload(self):
        """Fermer la session aiohttp quand le cog est déchargé."""
        if self._session:
            asyncio.create_task(self._session.close())
            logger.info("Session aiohttp du module Emoji fermée")
    
    async def get_session(self):
        """Obtenir une session HTTP, en créant une si nécessaire."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.info("Nouvelle session aiohttp créée pour le module Emoji")
        return self._session
    
    def get_emoji_limits(self, guild):
        """Obtient les limites d'émojis basées sur le niveau de boost du serveur."""
        # Niveau de base: 50 statiques, 50 animés
        # Niveau 1: 100 statiques, 100 animés
        # Niveau 2: 150 statiques, 150 animés
        # Niveau 3: 250 statiques, 250 animés
        
        if guild.premium_tier == 0:
            return {"static": 50, "animated": 50}
        elif guild.premium_tier == 1:
            return {"static": 100, "animated": 100}
        elif guild.premium_tier == 2:
            return {"static": 150, "animated": 150}
        else:  # Niveau 3
            return {"static": 250, "animated": 250}
    
    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def add_emojis(self, ctx, emoji_type="all", count: int = 10):
        """Ajoute des émojis tendance au serveur. Types: anime, basic, all
        
        Note: Il est recommandé d'ajouter seulement 5-10 émojis à la fois pour éviter les limitations d'API."""
        guild = ctx.guild
        
        # Vérifier le type d'émoji à ajouter
        if emoji_type.lower() not in ["anime", "basic", "all"]:
            await ctx.send("❌ Type d'émoji invalide. Utilisez 'anime', 'basic' ou 'all'.")
            return
        
        # S'assurer que la quantité est valide
        if count <= 0 or count > 50:
            await ctx.send("❌ Le nombre d'émojis doit être entre 1 et 50.")
            return
        
        # Envoyer un message de départ
        status_message = await ctx.send("⏳ Préparation des émojis en cours...")
        
        try:
            # Obtenir les limites d'emoji basées sur le niveau de boost
            limits = self.get_emoji_limits(guild)
            
            # Compter les slots d'émojis disponibles
            emojis_statiques = [e for e in guild.emojis if not e.animated]
            emojis_animes = [e for e in guild.emojis if e.animated]
            
            slots_statiques_disponibles = limits["static"] - len(emojis_statiques)
            slots_animes_disponibles = limits["animated"] - len(emojis_animes)
            
            # Informer l'utilisateur des slots disponibles
            info_message = f"ℹ️ Slots disponibles avec le niveau de boost {guild.premium_tier}:\n" \
                          f"• Émojis statiques: {slots_statiques_disponibles}/{limits['static']}\n" \
                          f"• Émojis animés: {slots_animes_disponibles}/{limits['animated']}"
            
            await status_message.edit(content=info_message)
            
            if slots_statiques_disponibles <= 0 and slots_animes_disponibles <= 0:
                await ctx.send("❌ Aucun slot d'émoji disponible. Boostez le serveur pour plus d'emplacements!")
                return
            
            # Sélectionner les émojis à ajouter
            emojis_to_add = []
            
            # Obtenir une session
            session = await self.get_session()
            
            if (emoji_type.lower() == "anime" or emoji_type.lower() == "all") and slots_animes_disponibles > 0:
                # Mélanger la liste pour la randomisation
                anime_count = min(count, len(ANIME_EMOJIS), slots_animes_disponibles)
                if anime_count > 0:
                    anime_random = random.sample(ANIME_EMOJIS, anime_count)
                    emojis_to_add.extend([(emoji, True) for emoji in anime_random])  # True = animé
            
            if (emoji_type.lower() == "basic" or emoji_type.lower() == "all") and slots_statiques_disponibles > 0:
                # Mélanger la liste pour la randomisation
                basic_count = min(count, len(BASIC_EMOJIS), slots_statiques_disponibles)
                if basic_count > 0:
                    basic_random = random.sample(BASIC_EMOJIS, basic_count)
                    emojis_to_add.extend([(emoji, False) for emoji in basic_random])  # False = statique
            
            # Si aucun emoji ne peut être ajouté
            if not emojis_to_add:
                await ctx.send("❌ Aucun slot d'émoji disponible pour les types sélectionnés.")
                return
            
            await status_message.edit(content=f"⏳ Ajout de {len(emojis_to_add)} émojis en cours...")
            
            # Ajouter les émojis
            added_emojis = []
            errors = []
            
            for i, (emoji_data, is_animated) in enumerate(emojis_to_add):
                try:
                    # Mise à jour du message de statut tous les 3 émojis
                    if i > 0 and i % 3 == 0:
                        await status_message.edit(content=f"⏳ Ajout des émojis en cours... ({i}/{len(emojis_to_add)})")
                    
                    # Ajouter un délai pour éviter le rate limiting
                    if i > 0:
                        await asyncio.sleep(2)  # Pause avant de commencer une nouvelle requête
                    
                    # Télécharger l'image de l'emoji avec système de réessai amélioré
                    max_retries = 4  # Augmenter le nombre de tentatives
                    retry_count = 0
                    image_data = None
                    
                    while retry_count < max_retries:
                        try:
                            async with session.get(emoji_data["url"], timeout=15) as resp:  # Augmenter le timeout
                                if resp.status == 429:  # Rate limit spécifique
                                    retry_count += 1
                                    wait_time = 3 * (retry_count + 1)  # Backoff exponentiel: 6s, 9s, 12s
                                    logger.warning(f"Rate limit (429) pour {emoji_data['name']}, attente de {wait_time}s avant réessai ({retry_count}/{max_retries})")
                                    await status_message.edit(content=f"⏳ Rate limit détecté, attente de {wait_time}s... ({i}/{len(emojis_to_add)})")
                                    await asyncio.sleep(wait_time)
                                    continue
                                elif resp.status != 200:
                                    retry_count += 1
                                    if retry_count >= max_retries:
                                        errors.append(f"Erreur {resp.status} pour {emoji_data['name']} après {max_retries} tentatives")
                                        logger.warning(f"Échec du téléchargement de l'emoji {emoji_data['name']} après {max_retries} tentatives: {resp.status}")
                                        break
                                    await asyncio.sleep(2)  # Pause plus longue avant réessai
                                    continue
                                
                                try:
                                    image_data = await resp.read()
                                    break  # Sortir de la boucle si réussi
                                except Exception as e:
                                    retry_count += 1
                                    logger.warning(f"Erreur lors de la lecture des données de l'image {emoji_data['name']}: {str(e)}")
                                    if retry_count >= max_retries:
                                        errors.append(f"Erreur de lecture pour {emoji_data['name']}: {str(e)}")
                                        break
                                    await asyncio.sleep(1)
                        except asyncio.TimeoutError:
                            retry_count += 1
                            logger.warning(f"Timeout pour l'emoji {emoji_data['name']}, tentative {retry_count}/{max_retries}")
                            if retry_count >= max_retries:
                                errors.append(f"Timeout pour {emoji_data['name']} après {max_retries} tentatives")
                                break
                            await asyncio.sleep(1)
                        except Exception as e:
                            retry_count += 1
                            logger.warning(f"Exception pour l'emoji {emoji_data['name']}: {str(e)}")
                            if retry_count >= max_retries:
                                errors.append(f"Erreur pour {emoji_data['name']}: {str(e)}")
                                break
                            await asyncio.sleep(1)
                    
                    # Vérifier si on a bien récupéré l'image
                    if not image_data:
                        continue
                    
                    # Ajouter l'emoji au serveur
                    try:
                        emoji = await guild.create_custom_emoji(
                            name=emoji_data["name"],
                            image=image_data,
                            reason=f"Ajouté par {ctx.author.display_name if hasattr(ctx.author, 'display_name') else 'un administrateur'}"
                        )
                    except discord.errors.InvalidArgument:
                        errors.append(f"Format d'image invalide pour {emoji_data['name']}")
                        logger.warning(f"Format d'image invalide pour {emoji_data['name']}")
                        continue
                    
                    added_emojis.append(emoji)
                    
                    # Pause plus longue pour éviter les erreurs de rate limiting
                    await asyncio.sleep(3.5)
                    
                except discord.Forbidden:
                    await status_message.edit(content="❌ Je n'ai pas la permission de gérer les émojis.")
                    return
                except discord.HTTPException as e:
                    errors.append(f"Erreur pour {emoji_data['name']}: {str(e)}")
                    logger.error(f"HTTPException lors de l'ajout de {emoji_data['name']}: {str(e)}")
                except Exception as e:
                    errors.append(f"Erreur inattendue pour {emoji_data['name']}: {str(e)}")
                    logger.error(f"Erreur lors de l'ajout d'emoji: {traceback.format_exc()}")
            
            # Créer un message de confirmation
            if added_emojis:
                embed = discord.Embed(
                    title="✅ Émojis ajoutés au serveur",
                    description=f"{len(added_emojis)} émojis ajoutés avec succès!",
                    color=discord.Color.green()
                )
                
                # Diviser les émojis ajoutés en groupes pour un affichage propre
                emoji_chunks = [added_emojis[i:i+10] for i in range(0, len(added_emojis), 10)]
                for i, chunk in enumerate(emoji_chunks):
                    embed.add_field(
                        name=f"Groupe {i+1}",
                        value=" ".join(str(emoji) for emoji in chunk),
                        inline=False
                    )
                
                # Ajouter les erreurs si nécessaire
                if errors:
                    error_text = "\n".join(errors[:10])
                    if len(errors) > 10:
                        error_text += f"\n...et {len(errors) - 10} autres erreurs."
                    
                    embed.add_field(
                        name="⚠️ Erreurs rencontrées",
                        value=f"```{error_text}```",
                        inline=False
                    )
                
                # Pied de page plus sécurisé
                author_name = ctx.author.display_name if hasattr(ctx.author, 'display_name') else "utilisateur"
                author_avatar = ctx.author.avatar.url if hasattr(ctx.author, 'avatar') and ctx.author.avatar else None
                embed.set_footer(text=f"Demandé par {author_name}", icon_url=author_avatar)
                await status_message.edit(content="", embed=embed)
            else:
                # Aucun emoji ajouté, uniquement des erreurs
                embed = discord.Embed(
                    title="❌ Échec de l'ajout d'émojis",
                    description="Aucun emoji n'a pu être ajouté au serveur.",
                    color=discord.Color.red()
                )
                
                error_text = "\n".join(errors[:15])
                if len(errors) > 15:
                    error_text += f"\n...et {len(errors) - 15} autres erreurs."
                
                embed.add_field(
                    name="Erreurs",
                    value=f"```{error_text}```",
                    inline=False
                )
                
                # Pied de page plus sécurisé
                author_name = ctx.author.display_name if hasattr(ctx.author, 'display_name') else "utilisateur"
                author_avatar = ctx.author.avatar.url if hasattr(ctx.author, 'avatar') and ctx.author.avatar else None
                embed.set_footer(text=f"Demandé par {author_name}", icon_url=author_avatar)
                await status_message.edit(content="", embed=embed)
        
        except Exception as e:
            logger.error(f"Erreur dans la commande add_emojis: {traceback.format_exc()}")
            await status_message.edit(content=f"❌ Une erreur s'est produite: {str(e)}")

    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def list_emojis(self, ctx):
        """Liste tous les émojis du serveur."""
        guild = ctx.guild
        
        try:
            # Récupérer les limites basées sur le niveau de boost
            limits = self.get_emoji_limits(guild)
            
            # Séparer les émojis statiques et animés
            static_emojis = [e for e in guild.emojis if not e.animated]
            animated_emojis = [e for e in guild.emojis if e.animated]
            
            # Créer un embed pour afficher les émojis
            embed = discord.Embed(
                title=f"📋 Émojis du serveur {guild.name}",
                description=f"Niveau de boost: {guild.premium_tier} ⭐\n"
                           f"Total: {len(guild.emojis)} émojis",
                color=discord.Color.blue()
            )
            
            # Afficher les émojis statiques (par groupes de 15 max)
            if static_emojis:
                static_chunks = [static_emojis[i:i+15] for i in range(0, len(static_emojis), 15)]
                
                for i, chunk in enumerate(static_chunks):
                    if i < 2:  # Limiter le nombre de champs pour éviter de dépasser la limite Discord
                        embed.add_field(
                            name=f"Émojis statiques (groupe {i+1})",
                            value=" ".join(str(emoji) for emoji in chunk),
                            inline=False
                        )
                
                if len(static_chunks) > 2:
                    embed.add_field(
                        name="⚠️ Note",
                        value=f"Trop d'émojis pour tout afficher. {len(static_emojis) - 30} émojis statiques supplémentaires.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Émojis statiques",
                    value="Aucun",
                    inline=False
                )
            
            # Afficher les émojis animés (par groupes de 15 max)
            if animated_emojis:
                animated_chunks = [animated_emojis[i:i+15] for i in range(0, len(animated_emojis), 15)]
                
                for i, chunk in enumerate(animated_chunks):
                    if i < 2:  # Limiter le nombre de champs pour éviter de dépasser la limite Discord
                        embed.add_field(
                            name=f"Émojis animés (groupe {i+1})",
                            value=" ".join(str(emoji) for emoji in chunk),
                            inline=False
                        )
                
                if len(animated_chunks) > 2:
                    embed.add_field(
                        name="⚠️ Note",
                        value=f"Trop d'émojis pour tout afficher. {len(animated_emojis) - 30} émojis animés supplémentaires.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Émojis animés",
                    value="Aucun",
                    inline=False
                )
            
            # Ajouter des infos sur les limites
            embed.add_field(
                name="Limites (basées sur le niveau de boost)",
                value=f"Émojis statiques: {len(static_emojis)}/{limits['static']}\n"
                     f"Émojis animés: {len(animated_emojis)}/{limits['animated']}",
                inline=False
            )
            
            # Ajouter un pied de page sécurisé
            author_name = ctx.author.display_name if hasattr(ctx.author, 'display_name') else "utilisateur"
            author_avatar = ctx.author.avatar.url if hasattr(ctx.author, 'avatar') and ctx.author.avatar else None
            embed.set_footer(text=f"Demandé par {author_name}", icon_url=author_avatar)
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Erreur dans la commande list_emojis: {traceback.format_exc()}")
            await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")
    
    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def emoji_limits(self, ctx):
        """Affiche les limites d'émojis du serveur selon son niveau de boost."""
        guild = ctx.guild
        limits = self.get_emoji_limits(guild)
        
        static_emojis = [e for e in guild.emojis if not e.animated]
        animated_emojis = [e for e in guild.emojis if e.animated]
        
        embed = discord.Embed(
            title=f"Limites d'émojis pour {guild.name}",
            description=f"Niveau de boost: {guild.premium_tier} ⭐",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Émojis statiques",
            value=f"{len(static_emojis)}/{limits['static']} utilisés",
            inline=True
        )
        
        embed.add_field(
            name="Émojis animés",
            value=f"{len(animated_emojis)}/{limits['animated']} utilisés",
            inline=True
        )
        
        embed.add_field(
            name="Total",
            value=f"{len(guild.emojis)}/{limits['static'] + limits['animated']} emplacements",
            inline=True
        )
        
        embed.add_field(
            name="Augmenter les limites",
            value="Pour avoir plus d'emplacements d'émojis, boostez le serveur!\n"
                 "• Niveau 1 (2 boosts): 100 de chaque type\n"
                 "• Niveau 2 (7 boosts): 150 de chaque type\n"
                 "• Niveau 3 (14 boosts): 250 de chaque type",
            inline=False
        )
        
        # Ajouter un pied de page sécurisé
        author_name = ctx.author.display_name if hasattr(ctx.author, 'display_name') else "utilisateur"
        author_avatar = ctx.author.avatar.url if hasattr(ctx.author, 'avatar') and ctx.author.avatar else None
        embed.set_footer(text=f"Demandé par {author_name}", icon_url=author_avatar)
        await ctx.send(embed=embed)

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(Emoji(bot))
    print("Module Emoji chargé avec succès.")