"""
Module Question du Jour pour le Bot Chii.
Ce module envoie automatiquement une question aléatoire chaque jour à minuit
pour stimuler l'activité du serveur.
"""
import discord
import logging
import asyncio
import json
import os
import random
from datetime import datetime, time, timedelta, timezone
from discord.ext import commands, tasks

# Configuration du logger
logger = logging.getLogger('ninis_bot')

# Questions du jour prédéfinies
DEFAULT_QUESTIONS = [
    "Quel est votre jeu vidéo préféré et pourquoi?",
    "Si vous pouviez voyager n'importe où dans le monde, où iriez-vous?",
    "Quel super-pouvoir choisiriez-vous si vous pouviez en avoir un?",
    "Quelle est votre série TV/anime préférée du moment?",
    "Si vous pouviez dîner avec une célébrité, qui choisiriez-vous?",
    "Quel talent aimeriez-vous maîtriser instantanément?",
    "Quel est votre plat préféré?",
    "Si vous pouviez vivre à n'importe quelle époque, laquelle choisiriez-vous?",
    "Quelle est votre plus grande réussite?",
    "Si vous pouviez avoir un animal exotique comme animal de compagnie, lequel choisiriez-vous?",
    "Quelle est votre façon préférée de vous détendre après une longue journée?",
    "Quel est votre livre ou manga préféré?",
    "Si vous deviez changer de carrière demain, que feriez-vous?",
    "Quel est votre film préféré de tous les temps?",
    "Si vous pouviez résoudre un problème mondial, lequel choisiriez-vous?",
    "Quelle est votre saison préférée et pourquoi?",
    "Si vous pouviez maîtriser n'importe quelle langue instantanément, laquelle choisiriez-vous?",
    "Quelle est la chose la plus courageuse que vous ayez jamais faite?",
    "Où vous voyez-vous dans 5 ans?",
    "Si vous pouviez avoir un don illimité pour une chose, qu'est-ce que ce serait?",
    "Quelle est votre activité préférée le week-end?",
    "Si vous pouviez vivre dans un monde fictif (livre, film, jeu), lequel choisiriez-vous?",
    "Quel conseil donneriez-vous à votre moi plus jeune?",
    "Quelle est la chose la plus importante que vous avez apprise cette année?",
    "Si vous aviez une journée complètement libre, comment la passeriez-vous?",
    "Quel est votre rêve le plus fou?",
    "Quelle musique écoutez-vous le plus en ce moment?",
    "Si vous pouviez rencontrer n'importe quel personnage fictif, qui choisiriez-vous?",
    "Quelle est votre citation préférée?",
    "Quelle est la chose la plus folle sur votre bucket list?",
    "Si vous pouviez être célèbre pour une chose, que serait-ce?",
    "Quelle application utilisez-vous le plus sur votre téléphone?",
    "Quel est votre souvenir d'enfance préféré?",
    "Si vous pouviez avoir une conversation avec n'importe quel animal, lequel choisiriez-vous?",
    "Quel passe-temps aimeriez-vous essayer?",
    "Quelle est votre destination de vacances de rêve?",
    "Si vous pouviez changer une chose dans le monde, que serait-ce?",
    "Quel est votre emoji préféré?",
    "Quel est votre plus grand accomplissement à ce jour?",
    "Si vous deviez écrire un livre, de quoi parlerait-il?",
    "Quelle est la chose la plus importante que vous ayez apprise de vos parents?",
    "Si vous pouviez participer à une émission de télé-réalité, laquelle serait-ce?",
    "Quel est votre bonbon ou dessert préféré?",
    "Quelle est la chose la plus bizarre que vous ayez jamais mangée?",
    "Si vous pouviez créer une nouvelle tradition pour tout le monde, quelle serait-elle?",
    "Quel talent unique possédez-vous?",
    "Si vous pouviez voyager dans le temps une seule fois, où et quand iriez-vous?",
    "Quelle est la chose la plus gentille qu'un étranger ait jamais faite pour vous?",
    "Quel est le meilleur conseil que vous ayez jamais reçu?",
    "Si vous deviez changer votre prénom, que choisiriez-vous?",
    "Quel artiste ou groupe aimeriez-vous voir en concert?",
    "Quelle est votre façon préférée de vous exprimer créativement?",
    "Si vous pouviez être invisible pendant une journée, que feriez-vous?",
    "Quel est votre jeu de société préféré?",
    "Quelle est la chose la plus précieuse que vous possédez?",
    "Si vous pouviez être connu comme expert dans un domaine, lequel choisiriez-vous?",
    "Quelle compétence aimeriez-vous apprendre en 2025?",
    "Si vous pouviez vivre n'importe où sur Terre, où serait-ce?",
    "Quel événement historique auriez-vous aimé vivre?",
    "Quelle est la chose la plus effrayante que vous ayez jamais faite?",
    "Si vous pouviez contrôler un élément (eau, feu, air, terre), lequel choisiriez-vous?"
]

class DailyQuestion(commands.Cog):
    """Module pour la question du jour automatique."""
    
    def __init__(self, bot):
        self.bot = bot
        self.questions = DEFAULT_QUESTIONS
        self.questions_file = "daily_questions.json"
        self.used_questions = []
        self.channels = {}  # {guild_id: channel_id}
        
        # Configuration du canal prédéfini (ID spécifique du canal "question du jour")
        self.predefined_channel_id = 1354524457569485003
        
        self.load_data()
        self.daily_question_task.start()
        logger.info("Module Question du Jour initialisé")
    
    def cog_unload(self):
        """Nettoyage lors du déchargement du cog."""
        self.daily_question_task.cancel()
    
    def load_data(self):
        """Charge les données depuis le fichier JSON."""
        # Charger les questions personnalisées si elles existent
        if os.path.exists(self.questions_file):
            try:
                with open(self.questions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "questions" in data:
                        self.questions = data["questions"]
                    if "used_questions" in data:
                        self.used_questions = data["used_questions"]
                    if "channels" in data:
                        self.channels = data["channels"]
                logger.info(f"Questions du jour chargées: {len(self.questions)} questions disponibles")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des questions du jour: {e}")
    
    def save_data(self):
        """Sauvegarde les données dans le fichier JSON."""
        data = {
            "questions": self.questions,
            "used_questions": self.used_questions,
            "channels": self.channels
        }
        try:
            with open(self.questions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des questions du jour: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def send_question_now(self, ctx):
        """Envoie immédiatement une question du jour dans le canal 'question du jour' ou équivalent."""
        success = await self.send_daily_question(ctx.guild)
        if success:
            await ctx.send("✅ Question du jour envoyée avec succès! Une nouvelle question sera automatiquement envoyée chaque jour à minuit.")
        else:
            await ctx.send("❌ Impossible d'envoyer la question. Le bot n'a pas trouvé le canal approprié. Veuillez vérifier que l'ID du canal est correct.")
    

    
    async def get_next_question(self):
        """Récupère la prochaine question aléatoire qui n'a pas été utilisée récemment."""
        available_questions = [q for q in self.questions if q not in self.used_questions]
        
        # Si toutes les questions ont été utilisées, on réinitialise
        if not available_questions:
            # Garder les 5 dernières questions dans la liste des utilisées pour éviter de les répéter trop vite
            if len(self.used_questions) > 5:
                self.used_questions = self.used_questions[-5:]
            available_questions = [q for q in self.questions if q not in self.used_questions]
        
        # S'il n'y a toujours pas de questions disponibles, utiliser une question aléatoire
        if not available_questions:
            return random.choice(self.questions)
        
        question = random.choice(available_questions)
        self.used_questions.append(question)
        self.save_data()
        return question
    
    async def send_daily_question(self, guild):
        """Envoie une question du jour dans le canal configuré pour un serveur."""
        # D'abord vérifier si un canal est configuré
        if guild.id in self.channels:
            channel_id = self.channels[guild.id]
            channel = guild.get_channel(channel_id)
            if channel:
                logger.info(f"Canal de question du jour trouvé (configuré) pour {guild.name}")
                return await self._send_question_to_channel(channel, guild)
        
        # Utiliser directement le canal prédéfini si disponible
        channel = guild.get_channel(self.predefined_channel_id)
        if channel:
            logger.info(f"Canal de question du jour prédéfini trouvé: {channel.name} pour {guild.name}")
            # Sauvegarder ce canal pour les prochaines fois
            self.channels[guild.id] = channel.id
            self.save_data()
            return await self._send_question_to_channel(channel, guild)
        
        # Sinon chercher un canal avec "question du jour" dans le nom
        for channel in guild.text_channels:
            if "question" in channel.name.lower() and "jour" in channel.name.lower():
                logger.info(f"Canal de question du jour trouvé automatiquement: {channel.name} pour {guild.name}")
                # Sauvegarder ce canal pour les prochaines fois
                self.channels[guild.id] = channel.id
                self.save_data()
                return await self._send_question_to_channel(channel, guild)
            elif "daily" in channel.name.lower() and "question" in channel.name.lower():
                logger.info(f"Canal de question du jour trouvé automatiquement: {channel.name} pour {guild.name}")
                # Sauvegarder ce canal pour les prochaines fois
                self.channels[guild.id] = channel.id
                self.save_data()
                return await self._send_question_to_channel(channel, guild)
                
        logger.error(f"Canal de question du jour introuvable pour {guild.name}")
        return False
    
    async def _send_question_to_channel(self, channel, guild):
        """Envoie une question du jour dans le canal spécifié."""
        try:
            question = await self.get_next_question()
            
            # Créer un embed pour la question
            embed = discord.Embed(
                title="❓ Question du Jour",
                description=question,
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Ajouter une petite explication
            embed.add_field(
                name="Participez!",
                value="Répondez à cette question pour animer la communauté! 💬",
                inline=False
            )
            
            # Ajouter une note de date
            now = datetime.now(timezone.utc)
            date_str = now.strftime("%d/%m/%Y")
            embed.set_footer(text=f"Question du {date_str} • Nouvelle question demain à minuit")
            
            await channel.send(embed=embed)
            logger.info(f"Question du jour envoyée dans {guild.name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la question du jour: {e}")
            return False
    
    @tasks.loop(time=time(0, 0, 0, 0, tzinfo=timezone.utc))  # Minuit UTC
    async def daily_question_task(self):
        """Tâche qui s'exécute tous les jours à minuit pour envoyer la question du jour."""
        try:
            logger.info("Exécution de la tâche de question du jour")
            
            # Parcourir tous les serveurs où le bot est présent
            for guild in self.bot.guilds:
                try:
                    await self.send_daily_question(guild)
                    # Attendre un peu entre chaque serveur pour éviter les rate limits
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Erreur pour le serveur {guild.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur dans la tâche de question du jour: {e}")
    
    @daily_question_task.before_loop
    async def before_daily_task(self):
        """Attend que le bot soit prêt avant de démarrer la tâche."""
        await self.bot.wait_until_ready()
        logger.info("Tâche de question du jour prête à démarrer")
        
        # Calculer le temps restant jusqu'à minuit pour le log
        now = datetime.now(timezone.utc)
        midnight = datetime.combine(now.date() + timedelta(days=1), time(0, 0, 0, 0, tzinfo=timezone.utc))
        delta = midnight - now
        minutes, seconds = divmod(delta.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        logger.info(f"Prochaine question du jour dans {hours}h {minutes}m {seconds}s")

async def setup(bot):
    """Fonction d'installation du cog."""
    await bot.add_cog(DailyQuestion(bot))
    logger.info("Cog 'daily_question' chargé avec succès")