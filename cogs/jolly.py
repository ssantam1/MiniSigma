import logging
import discord
from discord.ext import commands
from discord import app_commands

logger = logging.getLogger("client.jolly")

class Jolly(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.channels = set()

    @app_commands.command(name="jolly", description="Makes this channel full of Christmas Spirit!")
    async def jolly(self, interaction: discord.Interaction):
        '''Toggles the jolly status of the channel'''
        logger.info(f"{interaction.user.name} issued /jolly, ({interaction.channel.name})")

        if interaction.channel_id not in self.channels:
            logger.info(f"Adding {interaction.channel_id} to jolly channels...")
            self.channels.add(interaction.channel_id)
            await interaction.response.send_message("This channel is now full of Christmas Spirit!")
        else:
            logger.info(f"Removing {interaction.channel_id} from jolly channels...")
            self.channels.remove(interaction.channel_id)
            await interaction.response.send_message("This channel is no longer jollified :(")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        '''Deletes messages in jolly channels that don't contain Christmas Spirit'''
        if message.author.bot:
            return

        if message.channel.id in self.channels:
            if "hohoho" not in message.content.lower() and "merry christmas" not in message.content.lower() and "ho ho ho" not in message.content.lower():
                await message.delete()
                await message.channel.send(f"You're a grinch, {message.author.mention}! Your message has been deleted. Please try again with a little more Christmas Spirit. Merry Christmas!", silent=True, delete_after=5)

    @commands.command()
    async def list_jolly_channels(self, ctx: commands.Context):
        '''Lists all jolly channel ids'''
        await ctx.send(f"Jolly Channels: {self.channels}")

async def setup(client: commands.Bot):
    await client.add_cog(Jolly(client))