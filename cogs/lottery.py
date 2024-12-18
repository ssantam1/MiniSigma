import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma

class Ticket(discord.ui.View):
    '''Represents a scratch ticket.'''
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label='Scratch!', style=discord.ButtonStyle.primary)
    async def scratch(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = 'Used'
        button.style = discord.ButtonStyle.gray
        button.disabled = True

        await interaction.message.edit(view=self)

class Lottery(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db = client.db

    @app_commands.command(name="daily", description="Redeem your daily reward!")
    async def daily(self, interaction: discord.Interaction):
        #TODO: Check cooldown
        view = Ticket(interaction.user)
        await interaction.response.send_message(view=view)

async def setup(client: MiniSigma):
    await client.add_cog(Lottery(client))