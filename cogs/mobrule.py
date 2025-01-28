import logging
import discord
from bot import MiniSigma
from config import EMBED_COLOR

logger = logging.getLogger("client.mobrule")

class MobRule(discord.ext.commands.Cog):
    '''Some fun utilities that allow non-admins to wreak havoc.'''
    def __init__(self, client: MiniSigma):
        self.client = client

    def get_icon_change_embed(self, user: discord.User, icon: discord.Attachment) -> discord.Embed:
        embed = discord.Embed(
            title="Server Icon Updated!", 
            description=f"Changed by {user.mention}",
            color=EMBED_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url
        )
        embed.set_thumbnail(url=icon.url)
        embed.set_footer(
            text=f"Automated by {self.client.user.display_name}",
            icon_url=self.client.user.display_avatar.url
        )
        return embed

    @discord.app_commands.command(name="icon", description="Change the server icon.")
    async def icon(self, interaction: discord.Interaction, attachment: discord.Attachment):
        '''Change the server icon.'''
        logger.info(f"{interaction.user.name} issued /icon, ({interaction.channel})")
        await interaction.guild.edit(icon=await attachment.read(), reason=f"Requested by {interaction.user.name}")
        embed = self.get_icon_change_embed(interaction.user, attachment)
        await interaction.response.send_message(embed=embed)
    
async def setup(client: MiniSigma):
    await client.add_cog(MobRule(client))