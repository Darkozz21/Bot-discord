"""
Module musical pour le Bot Ninis.
Ce cog permet de jouer de la musique depuis YouTube dans les salons vocaux.
Utilise yt-dlp pour une extraction fiable des flux audio.
"""

import asyncio
import discord
import logging
import os
import re
import json
import time
import aiohttp
import yt_dlp
import functools
import concurrent.futures

from discord.ext import commands

# Configuration du logger
logger = logging.getLogger('ninis_bot')

# Options pour yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False, # Permet la lecture des playlists
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # Bind to ipv4
    'extract_flat': False, # Permet l'extraction complète
    'progress_hooks': [],
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
    }],
}

# Options pour FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af "volume=0.5"',
}

# Pool d'exécuteurs pour les opérations bloquantes
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

class YTDLSource:
    """Classe pour gérer la recherche et l'extraction des données audio YouTube."""
    
    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

    def __init__(self, source, data, requester):
        self.source = source
        self.data = data
        self.requester = requester
        
        self.title = data.get('title')
        self.url = data.get('webpage_url') or data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration')
        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        
    @classmethod
    async def create_source(cls, ctx, query, *, requester=None):
        """Crée une source audio à partir d'une recherche ou d'une URL YouTube."""
        requester = requester or ctx.author.name
        
        # Exécute l'extraction d'info dans un thread séparé pour éviter le blocage
        loop = asyncio.get_event_loop()
        try:
            partial = functools.partial(cls.ytdl.extract_info, query, download=False)
            data = await loop.run_in_executor(executor, partial)
        except yt_dlp.DownloadError as e:
            logger.error(f"Erreur lors de l'extraction d'infos de {query}: {str(e)}")
            return None
        
        if data is None:
            logger.error(f"Aucune donnée trouvée pour {query}")
            return None
            
        # Gérer les playlists ou les recherches qui renvoient plusieurs résultats
        if 'entries' in data:
            if not data['entries']:
                logger.warning(f"Aucune entrée trouvée pour {query}")
                return None
            data = data['entries'][0]
            
        # Construire le dictionnaire de piste
        track = {
            'url': data.get('webpage_url') or query,
            'title': data.get('title', 'Titre inconnu'),
            'thumbnail': data.get('thumbnail', None),
            'duration': data.get('duration', 0),
            'uploader': data.get('uploader', 'Inconnu'),
            'stream_url': data.get('url'),  # URL du flux direct
            'requester': requester
        }
        
        return track


class Music(commands.Cog):
    """Commandes pour jouer de la musique dans un salon vocal."""

    def __init__(self, bot):
        self.bot = bot
        self.current_track = None
        self.now_playing_message = None
        self.queue = []
        self.queue_message = None
        self.session = None
        
    def cog_unload(self):
        """Nettoie les ressources lors du déchargement du cog."""
        if self.session:
            asyncio.create_task(self.session.close())
            
    async def cog_load(self):
        """Initialise les ressources lors du chargement du cog."""
        self.session = aiohttp.ClientSession()
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def create_music_channels(self, ctx):
        """Crée 5 salons vocaux dédiés à la musique."""
        guild = ctx.guild
        
        # Liste des salons vocaux à créer
        music_channels = [
            "🎸・lofi hip-hop",
            "🎹・piano chill",
            "🥁・pop hits",
            "🎤・karaoke party",
            "🎧・music session"
        ]
        
        # Vérifier si une catégorie Musique existe, sinon la créer
        music_category = discord.utils.get(guild.categories, name="୨୧・Musique")
        if not music_category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True, speak=True, use_voice_activation=True),
                guild.me: discord.PermissionOverwrite(connect=True, speak=True, move_members=True, mute_members=True)
            }
            music_category = await guild.create_category(name="୨୧・Musique", overwrites=overwrites)
            await ctx.send("✅ Catégorie `୨୧・Musique` créée avec succès!")
            
        # Compteur de salons créés
        created_count = 0
        
        # Créer chaque salon s'il n'existe pas déjà
        for channel_name in music_channels:
            # Vérifier si le salon existe déjà
            if discord.utils.get(music_category.channels, name=channel_name.replace("・", "-")):
                continue
                
            # Créer le salon
            try:
                await guild.create_voice_channel(
                    name=channel_name,
                    category=music_category,
                    bitrate=96000,  # 96 kbps pour une bonne qualité audio
                    user_limit=0,   # Pas de limite d'utilisateurs
                )
                created_count += 1
                logger.info(f"Salon vocal '{channel_name}' créé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la création du salon '{channel_name}': {e}")
                await ctx.send(f"❌ Erreur lors de la création du salon `{channel_name}`: {e}")
        
        # Message de confirmation
        if created_count > 0:
            await ctx.send(f"✅ {created_count} salons vocaux de musique ont été créés avec succès dans la catégorie `୨୧・Musique`!")
        else:
            await ctx.send("ℹ️ Tous les salons vocaux de musique existent déjà.")

    @commands.command()
    async def join(self, ctx):
        """Rejoint ton salon vocal."""
        # Vérifie si l'utilisateur est dans un salon vocal
        if ctx.author.voice is None:
            return await ctx.send("❌ Tu dois être dans un salon vocal pour utiliser cette commande.")

        channel = ctx.author.voice.channel
        
        # Si le bot est déjà dans un salon vocal
        if ctx.voice_client is not None:
            # Si le bot est déjà dans le même salon
            if ctx.voice_client.channel.id == channel.id:
                return await ctx.send(f"✅ Je suis déjà dans {channel.mention}")
            # Si le bot est dans un autre salon, on le déplace
            await ctx.voice_client.move_to(channel)
            return await ctx.send(f"👋 J'ai rejoint {channel.mention}")
            
        # Sinon, on rejoint le salon
        await channel.connect()
        await ctx.send(f"👋 J'ai rejoint {channel.mention}")

    @commands.command()
    async def leave(self, ctx):
        """Quitte le salon vocal."""
        if ctx.voice_client is None:
            return await ctx.send("❌ Je ne suis pas dans un salon vocal.")

        # Nettoyer la queue et les messages
        self.queue = []
        self.current_track = None
        
        # Quitter le salon
        await ctx.voice_client.disconnect()
        await ctx.send("👋 J'ai quitté le salon vocal.")

    @commands.command()
    async def play(self, ctx, *, query):
        """Joue une musique depuis YouTube. Tu peux utiliser un titre, un artiste ou une URL."""
        # Vérifie si l'utilisateur est dans un salon vocal
        if ctx.author.voice is None:
            return await ctx.send("❌ Tu dois être dans un salon vocal pour utiliser cette commande.")
            
        # Formater la recherche si ce n'est pas une URL
        if not (query.startswith('http://') or query.startswith('https://')):
            query = f"ytsearch:{query}"

        # Rejoint le salon vocal si pas déjà présent
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
        
        # Status message pour montrer que le bot cherche la musique
        status_message = await ctx.send(f"🔍 Recherche de `{query}`...")
        
        try:
            # Recherche et extrait les informations de la vidéo
            track = await YTDLSource.create_source(ctx, query, requester=ctx.author.display_name)
            
            if not track:
                await status_message.edit(content="❌ Je n'ai pas pu trouver cette musique sur YouTube.")
                return
                
            # Ajoute à la queue et informe l'utilisateur
            if ctx.voice_client.is_playing() or len(self.queue) > 0:
                self.queue.append(track)
                
                # Créer un embed pour la queue
                embed = discord.Embed(
                    title="✅ Ajouté à la queue",
                    description=f"[{track['title']}]({track['url']})",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Position dans la queue", value=f"#{len(self.queue)}", inline=True)
                embed.add_field(name="Demandé par", value=track['requester'], inline=True)
                
                if track.get('thumbnail'):
                    embed.set_thumbnail(url=track['thumbnail'])
                
                if track.get('duration'):
                    minutes, seconds = divmod(int(track['duration']), 60)
                    embed.add_field(
                        name="Durée", 
                        value=f"{minutes}:{seconds:02d}", 
                        inline=True
                    )
                
                await status_message.edit(content=None, embed=embed)
            else:
                # Joue directement si rien n'est en cours
                await status_message.edit(content=f"🎵 Lecture de `{track['title']}`...")
                await self._play_track(ctx, track)
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de musique: {str(e)}")
            await status_message.edit(content=f"❌ Erreur: Je n'ai pas pu trouver ou lire cette musique.\n```{str(e)}```")

    @commands.command()
    async def skip(self, ctx):
        """Passe à la musique suivante dans la queue."""
        if ctx.voice_client is None:
            return await ctx.send("❌ Je ne suis pas dans un salon vocal.")
            
        if not ctx.voice_client.is_playing():
            return await ctx.send("❌ Je ne joue rien actuellement.")
        
        # Skip et joue la prochaine chanson
        ctx.voice_client.stop()
        await ctx.send("⏭️ Musique passée !")
    
    @commands.command()
    async def pause(self, ctx):
        """Met en pause la musique en cours."""
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            return await ctx.send("❌ Je ne joue rien actuellement.")
            
        if ctx.voice_client.is_paused():
            return await ctx.send("⚠️ La musique est déjà en pause.")
            
        ctx.voice_client.pause()
        await ctx.send("⏸️ Musique mise en pause.")
    
    @commands.command()
    async def resume(self, ctx):
        """Reprend la lecture de la musique en pause."""
        if ctx.voice_client is None:
            return await ctx.send("❌ Je ne suis pas dans un salon vocal.")
            
        if not ctx.voice_client.is_paused():
            return await ctx.send("⚠️ La musique n'est pas en pause.")
            
        ctx.voice_client.resume()
        await ctx.send("▶️ Lecture reprise.")
    
    @commands.command()
    async def stop(self, ctx):
        """Arrête la musique et vide la queue."""
        if ctx.voice_client is None:
            return await ctx.send("❌ Je ne suis pas dans un salon vocal.")
            
        # Nettoie la queue
        self.queue = []
        self.current_track = None
        
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Lecture arrêtée, queue vidée.")
        else:
            await ctx.send("⚠️ Je ne joue rien actuellement, mais la queue a été vidée.")
    
    @commands.command()
    async def queue(self, ctx):
        """Affiche la queue des musiques."""
        if not self.queue and not self.current_track:
            return await ctx.send("📭 La queue est vide.")
            
        # Crée un embed pour la queue
        embed = discord.Embed(
            title="🎵 Queue musicale",
            color=discord.Color.blue()
        )
        
        # Ajoute la musique en cours
        if self.current_track:
            embed.add_field(
                name="🎧 En cours de lecture",
                value=f"[{self.current_track['title']}]({self.current_track['url']}) | Demandé par {self.current_track['requester']}",
                inline=False
            )
        
        # Ajoute les musiques de la queue
        if self.queue:
            queue_text = ""
            for i, track in enumerate(self.queue, 1):
                queue_text += f"{i}. [{track['title']}]({track['url']}) | Demandé par {track['requester']}\n"
                
                # Discord a une limite de 1024 caractères par champ
                if len(queue_text) > 900 and i < len(self.queue):
                    queue_text += f"... et {len(self.queue) - i} autres musiques."
                    break
                    
            embed.add_field(
                name="📋 Prochaines musiques",
                value=queue_text,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def volume(self, ctx, volume: int = None):
        """Ajuste le volume de la musique (entre 0 et 100)."""
        if ctx.voice_client is None:
            return await ctx.send("❌ Je ne suis pas dans un salon vocal.")
            
        if volume is None:
            current_volume = int(ctx.voice_client.source.volume * 100) if ctx.voice_client.source else 0
            return await ctx.send(f"🔊 Volume actuel: {current_volume}%")
            
        if not 0 <= volume <= 100:
            return await ctx.send("⚠️ Le volume doit être entre 0 et 100.")
            
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = volume / 100
            
        await ctx.send(f"🔊 Volume réglé sur {volume}%")
    
    async def _play_track(self, ctx, track):
        """Joue une piste audio et gère la progression de la queue."""
        self.current_track = track
        
        # Crée un embed pour la musique en cours
        embed = discord.Embed(
            title="🎵 Lecture en cours",
            description=f"[{track['title']}]({track['url']})",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Demandé par", value=track['requester'], inline=True)
        
        if track.get('duration'):
            minutes, seconds = divmod(int(track['duration']), 60)
            embed.add_field(
                name="Durée", 
                value=f"{minutes}:{seconds:02d}", 
                inline=True
            )
            
        if track.get('uploader'):
            embed.add_field(
                name="Chaîne", 
                value=track['uploader'], 
                inline=True
            )
        
        if track.get('thumbnail'):
            embed.set_thumbnail(url=track['thumbnail'])
            
        self.now_playing_message = await ctx.send(embed=embed)
        
        try:
            # Si nous n'avons pas d'URL de flux direct, récupérons-la
            if not track.get('stream_url'):
                # Nouvelle tentative d'extraction, au cas où
                loop = asyncio.get_event_loop()
                try:
                    partial = functools.partial(YTDLSource.ytdl.extract_info, track['url'], download=False)
                    data = await loop.run_in_executor(executor, partial)
                    if data:
                        track['stream_url'] = data.get('url')
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction de l'URL de flux: {e}")
                    raise
            
            # Vérifie que nous avons bien une URL de flux
            if not track.get('stream_url'):
                logger.error(f"URL de flux manquante pour {track['title']}")
                await ctx.send("❌ Je n'ai pas pu extraire le flux audio. Essaie une autre vidéo.")
                asyncio.run_coroutine_threadsafe(self._song_finished(ctx, None), self.bot.loop)
                return

            try:
                # Crée une source audio à partir de l'URL de flux direct
                source = discord.FFmpegPCMAudio(
                    track['stream_url'],
                    before_options=ffmpeg_options['before_options'],
                    options=ffmpeg_options['options']
                )
            except Exception as e:
                logger.error(f"Erreur FFmpeg: {str(e)}")
                await ctx.send(f"❌ Erreur lors de la lecture: {str(e)}")
                asyncio.run_coroutine_threadsafe(self._song_finished(ctx, None), self.bot.loop)
                return
            
            # Ajoute le contrôle du volume
            volume_source = discord.PCMVolumeTransformer(source, volume=0.5)
            
            # Joue la musique
            ctx.voice_client.play(
                volume_source, 
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._song_finished(ctx, e), self.bot.loop
                ).result()
            )
                
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de la musique: {str(e)}")
            await ctx.send(f"❌ Erreur: Je n'ai pas pu lire cette musique.\n```{str(e)}```")
            # Passe à la musique suivante
            asyncio.run_coroutine_threadsafe(self._song_finished(ctx, None), self.bot.loop)
            
    async def _song_finished(self, ctx, error):
        """Gère la fin d'une musique et joue la suivante si disponible."""
        if error:
            logger.error(f"Erreur lors de la lecture: {error}")
            await ctx.send(f"❌ Erreur pendant la lecture: ```{error}```")
            
        # Vérifie s'il reste des musiques dans la queue
        if self.queue:
            next_track = self.queue.pop(0)
            await self._play_track(ctx, next_track)
        else:
            self.current_track = None
            await ctx.send("📭 Queue terminée ! Ajoute plus de musiques avec `!play`.")


async def setup(bot):
    """Installe le cog de musique dans le bot."""
    await bot.add_cog(Music(bot))
    logger.info("Cog 'music' chargé avec succès")