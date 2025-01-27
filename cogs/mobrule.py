import logging
import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma

logger = logging.getLogger("client.mobrule")

class MobRule(commands.Cog):
    '''Some fun utilities that allow non-admins to wreak havoc.'''
    def __init__(self, client: MiniSigma):
        self.client = client

    @app_commands.command(name="icon", description="Change the server icon.")
    async def icon(self, interaction: discord.Interaction, attachment: discord.Attachment):
        '''Change the server icon.'''
        await interaction.response.send_message("Changing server icon... Sample: " + attachment.url, ephemeral=True)
        
    
async def setup(client: MiniSigma):
    await client.add_cog(MobRule(client))