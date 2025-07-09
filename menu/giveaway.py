"""
Module Giveaway pour le Bot Discord.
Ce module permet de créer des tirages au sort personnalisés.
"""
import discord
import asyncio
import random
from discord.ext import commands
from datetime import datetime, timedelta

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def gstart(self, ctx, temps: str, gagnants: int, *, prix: str):
        """Lance un giveaway personnalisé.
        Exemple: !gstart 10m 1 Nitro Classic"""
        # Convertir le temps
        unit = temps[-1].lower()
        try:
            value = int(temps[:-1])
        except ValueError:
            await ctx.send("⚠️ Format de temps invalide! Utilisez s/m/h/d (ex: 30s, 5m, 2h, 1d)")
            return

        seconds = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }.get(unit, 0) * value

        if seconds == 0:
            await ctx.send("⚠️ Unité de temps invalide! Utilisez s/m/h/d")
            return

        # Créer l'embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**{prix}**\n\n"
                       f"Réagissez avec 🎉 pour participer!\n"
                       f"Gagnants: **{gagnants}**\n"
                       f"Fin le: **{(datetime.now() + timedelta(seconds=seconds)).strftime('%d/%m/%Y à %H:%M')}**",
            color=discord.Color.gold(),
            timestamp=datetime.now() + timedelta(seconds=seconds)
        )
        embed.set_footer(text=f"Organisé par {ctx.author.name}")

        # Envoyer et enregistrer
        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")

        self.active_giveaways[message.id] = {
            'channel': ctx.channel.id,
            'winners': gagnants,
            'prize': prix
        }

        # Planifier la fin
        await asyncio.sleep(seconds)
        await self.end_giveaway(message.id)

    async def end_giveaway(self, message_id):
        if message_id not in self.active_giveaways:
            return

        data = self.active_giveaways.pop(message_id)
        channel = self.bot.get_channel(data['channel'])
        if not channel:
            return

        message = await channel.fetch_message(message_id)
        reaction = discord.utils.get(message.reactions, emoji='🎉')

        users = [user async for user in reaction.users() if not user.bot]

        if len(users) < data['winners']:
            winners = users
        else:
            winners = random.sample(users, data['winners'])

        # Annoncer les gagnants
        if winners:
            win_text = ", ".join(w.mention for w in winners)
            await channel.send(f"🎉 Félicitations {win_text}! Vous avez gagné **{data['prize']}**!")
        else:
            await channel.send("😢 Pas assez de participants pour le giveaway!")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def greroll(self, ctx, message_id: int):
        """Relance un giveaway terminé."""
        try:
            message = await ctx.channel.fetch_message(message_id)
            reaction = discord.utils.get(message.reactions, emoji='🎉')
            users = [user async for user in reaction.users() if not user.bot]

            if users:
                winner = random.choice(users)
                await ctx.send(f"🎉 Nouveau gagnant: {winner.mention}!")
            else:
                await ctx.send("😢 Pas de participants trouvés!")
        except:
            await ctx.send("⚠️ Message non trouvé!")

async def setup(bot):
    await bot.add_cog(Giveaway(bot))