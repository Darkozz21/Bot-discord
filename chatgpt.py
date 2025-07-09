"""
Module ChatGPT pour le Bot Chii.
Ce module permet aux membres du serveur d'interagir avec ChatGPT via l'API OpenAI.
"""
import os
import logging
import discord
from discord.ext import commands
import openai
from openai import OpenAI

# Configuration du logger
logger = logging.getLogger('chii_bot')

class ChatGPT(commands.Cog):
    """Commandes pour interagir avec ChatGPT."""

    def __init__(self, bot):
        self.bot = bot
        # Initialiser l'API OpenAI avec la clé API depuis les variables d'environnement
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.error("Clé API OpenAI non trouvée dans les variables d'environnement.")
            raise ValueError("OPENAI_API_KEY non définie")
        
        # Log uniquement les premiers caractères de la clé pour vérification (ne pas logger toute la clé)
        logger.info(f"Utilisation de la clé API OpenAI commençant par: {self.openai_api_key[:10]}...")
            
        self.client = OpenAI(api_key=self.openai_api_key)
        logger.info("Module ChatGPT initialisé avec succès avec le modèle gpt-4o-mini")

    @commands.command()
    async def ask(self, ctx, *, question=None):
        """Pose une question à ChatGPT.
        
        Args:
            question: La question à poser à ChatGPT.
        """
        # Vérifier si une question a été fournie
        if not question:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Tu dois poser une question ! Usage: `!ask <question>`",
                color=discord.Colour.red()
            )
            await ctx.send(embed=embed)
            return

        # Envoyer un message indiquant que le bot réfléchit
        thinking_message = await ctx.send("🤔 Je réfléchis à ta question...")

        try:
            # Appeler l'API OpenAI avec le modèle gpt-4o-mini
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=[
                    {"role": "system", "content": "Tu es un assistant utile, précis et amical qui répond aux questions dans un serveur Discord. Garde tes réponses concises, moins de 1500 caractères si possible."},
                    {"role": "user", "content": question}
                ],
                max_tokens=800,  # Limite le nombre de tokens pour garder la réponse courte
                temperature=0.7  # Contrôle la créativité (0.7 est un bon équilibre)
            )
            
            # Récupérer la réponse
            answer = response.choices[0].message.content.strip()
            
            # Limiter la réponse à 2000 caractères pour éviter les erreurs Discord
            if len(answer) > 2000:
                logger.info(f"Réponse tronquée de {len(answer)} à 2000 caractères")
                answer = answer[:1997] + "..."
            
            # Créer un embed pour la réponse
            embed = discord.Embed(
                title=f"📝 Réponse à: {question[:100] + '...' if len(question) > 100 else question}",
                description=answer,
                color=discord.Colour.blue()
            )
            
            # Ajouter des informations supplémentaires
            embed.set_footer(text=f"Demandé par {ctx.author.display_name} • Propulsé par GPT-4o-mini")
            
            # Envoyer la réponse
            await thinking_message.delete()
            await ctx.send(embed=embed)
            
            # Journaliser l'utilisation
            logger.info(f"Commande ChatGPT utilisée par {ctx.author} - Question: {question[:50]}...")
            
        except Exception as e:
            # Gérer les erreurs
            logger.error(f"Erreur lors de l'appel à l'API OpenAI: {e}")
            
            await thinking_message.delete()
            
            # Gestion des erreurs plus spécifiques pour OpenAI
            error_message = str(e)
            
            if "insufficient_quota" in error_message:
                error_description = "Le quota d'utilisation de l'API OpenAI est épuisé. Contactez l'administrateur du bot pour recharger les crédits."
            elif "rate_limit_exceeded" in error_message:
                error_description = "Trop de demandes ont été envoyées à OpenAI. Veuillez réessayer dans quelques minutes."
            elif "maximum context length" in error_message or "max_tokens" in error_message:
                error_description = "La question est trop longue. Essayez de la reformuler plus brièvement."
            else:
                error_description = f"Je n'ai pas pu obtenir une réponse de ChatGPT.\nErreur: {str(e)[:100]}..."
                
            error_embed = discord.Embed(
                title="❌ Erreur avec ChatGPT",
                description=error_description,
                color=discord.Colour.red()
            )
            
            # Ajouter un lien vers la documentation OpenAI
            if "insufficient_quota" in error_message:
                error_embed.add_field(
                    name="Solution",
                    value="L'administrateur doit vérifier le compte OpenAI pour recharger les crédits ou mettre à jour le plan de facturation.",
                    inline=False
                )
                
            await ctx.send(embed=error_embed)

async def setup(bot):
    """Fonction d'installation du cog."""
    await bot.add_cog(ChatGPT(bot))