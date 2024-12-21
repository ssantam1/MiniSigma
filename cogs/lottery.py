import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma
from utility.config import EMBED_COLOR

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

        embed = interaction.message.embeds[0]
        embed.description = None
        embed.add_field(name=":cherries: :cherries: :cherries:", value="You won the jackpot!")

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()

class Lottery(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db = client.db

    def create_embed(self) -> discord.Embed:
        '''Creates an embed with three blank spots to be "scratched" later'''
        return discord.Embed(title="Scratch Ticket", description=":fog: :fog: :fog:", color=EMBED_COLOR)

    @app_commands.command(name="daily", description="Redeem your daily reward!")
    async def daily(self, interaction: discord.Interaction):
        #TODO: Check cooldown
        embed = self.create_embed()
        view = Ticket(interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(client: MiniSigma):
    await client.add_cog(Lottery(client))