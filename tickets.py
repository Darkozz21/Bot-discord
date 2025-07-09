"""
Module de tickets pour le Bot Discord.
"""
import discord
import logging
from discord.ext import commands
from discord import ui, ButtonStyle

logger = logging.getLogger('ninis_bot')

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Créer un ticket", style=ButtonStyle.primary, emoji="📩", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketModal())

class TicketModal(ui.Modal, title="Création de ticket"):
    sujet = ui.TextInput(
        label="Sujet du ticket",
        placeholder="Entrez le sujet de votre ticket...",
        required=True,
        max_length=100
    )

    description = ui.TextInput(
        label="Description",
        placeholder="Décrivez votre demande...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Vérifier si l'utilisateur a déjà un ticket
            ticket_channel = discord.utils.get(interaction.guild.channels, 
                                             name=f"ticket-{interaction.user.name.lower()}")
            if ticket_channel:
                await interaction.response.send_message("Vous avez déjà un ticket ouvert!", ephemeral=True)
                return

            # Créer la catégorie si elle n'existe pas
            category = discord.utils.get(interaction.guild.categories, name="Tickets")
            if not category:
                category = await interaction.guild.create_category("Tickets")

            # Configurer les permissions
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Créer le canal
            channel = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )

            # Créer l'embed
            embed = discord.Embed(
                title=f"Ticket: {self.sujet.value}",
                description=self.description.value,
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            # Bouton de fermeture
            close_button = ui.Button(label="Fermer le ticket", style=ButtonStyle.danger, custom_id="close_ticket")
            view = ui.View()
            view.add_item(close_button)

            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"Votre ticket a été créé: {channel.mention}", ephemeral=True)

        except Exception as e:
            logger.error(f"Erreur lors de la création du ticket: {e}")
            await interaction.response.send_message("Une erreur s'est produite lors de la création du ticket.", ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        if interaction.data.get("custom_id") == "close_ticket":
            if "ticket-" in interaction.channel.name:
                await interaction.response.send_message("Fermeture du ticket...", ephemeral=True)
                await interaction.channel.delete()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Configure le système de tickets."""
        embed = discord.Embed(
            title="Support par ticket",
            description="Pour contacter le staff, cliquez sur le bouton ci-dessous pour créer un ticket.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=TicketView())

async def setup(bot):
    await bot.add_cog(Tickets(bot))