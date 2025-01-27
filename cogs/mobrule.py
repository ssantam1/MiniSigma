import logging
import discord
from bot import MiniSigma

logger = logging.getLogger("client.mobrule")

class MobRule(discord.ext.commands.Cog):
    '''Some fun utilities that allow non-admins to wreak havoc.'''
    def __init__(self, client: MiniSigma):
        self.client = client

    @discord.app_commands.command(name="icon", description="Change the server icon.")
    async def icon(self, interaction: discord.Interaction, attachment: discord.Attachment):
        '''Change the server icon.'''
        logger.info(f"{interaction.user.name} issued /icon, ({interaction.channel})")
        await interaction.guild.edit(icon=await attachment.read(), reason=f"Requested by {interaction.user.name}")
    
async def setup(client: MiniSigma):
    await client.add_cog(MobRule(client))