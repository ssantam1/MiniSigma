import logging
import discord
from discord.ext import commands
from discord import app_commands

from bot import MiniSigma
from utility.utils import create_message_embed

logger = logging.getLogger("client.StarBoard")

class StarBoard(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db = client.db
        self.default_threshold = 4
        self.db.create_starboard_tables()

    def create_embed(self, message: discord.Message) -> discord.Embed:
        '''Creates an embed for displaying a message on the starboard'''
        embed = create_message_embed(message, discord.Color.gold())
        return embed
    
    def num_stars(self, message: discord.Message) -> int:
        '''Returns number of star reactions on a message'''
        for reaction in message.reactions:
            if reaction.emoji == "⭐":
                return reaction.count
        return 0
    
    async def send_starboard_message(self, target_channel: discord.TextChannel, message: discord.Message) -> discord.Message:
        '''Displays a message in the starboard channel'''
        return await target_channel.send(
            content=f"⭐ {self.num_stars(message)} | <#{message.channel.id}>",
            embed=self.create_embed(message)
        )
    
    def is_starboard_server(self, guild_id: int) -> bool:
        '''Checks if a server has a starboard channel set'''
        return self.db.get_starboard_channel(guild_id) is not None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
        if event.emoji.name != "⭐":
            return
        
        if not self.is_starboard_server(event.guild_id):
            return

        channel = self.client.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)

        logger.info(f"Registered star reaction on message '{channel}'")

        if self.num_stars(message) < self.db.get_starboard_threshold(event.guild_id):
            return
        
        if self.db.message_is_starboarded(message.id):
            starboard_message_id, starboard_channel_id = self.db.get_starboard_message(message.id)

            starboard_channel = self.client.get_channel(starboard_channel_id)
            starboard_message = await starboard_channel.fetch_message(starboard_message_id)

            logger.info(f"Updating starboard message '{starboard_channel.name}'...")
            await starboard_message.edit(content=f"⭐ {self.num_stars(message)} | <#{message.channel.id}>")

        else:
            starboard_channel_id = self.db.get_starboard_channel(channel.guild.id)
            starboard_channel = self.client.get_channel(starboard_channel_id)

            logger.info(f"Sending message to starboard channel '{starboard_channel.name}'...")
            starboard_message = await self.send_starboard_message(starboard_channel, message)
            self.db.add_starboard_message(message.id, starboard_message.id, starboard_channel.id)

    @app_commands.command(name="starboard", description="Set the starboard channel & threshold for the server")
    @app_commands.describe(threshold="The number of stars required to display a message on the starboard")
    @app_commands.guild_only()
    async def starboard(self, interaction: discord.Interaction, threshold: int):
        '''Set the starboard channel and star threshold for the server'''
        if not interaction.guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return
        
        if threshold < 1:
            await interaction.response.send_message("Threshold must be at least 1.", ephemeral=True)
            return
        
        channel = interaction.channel
        self.db.set_starboard_channel(interaction.guild_id, channel.id)
        self.db.set_starboard_threshold(interaction.guild.id, threshold)

        content = f"Starboard channel set to {channel.mention}!\
            \nAll future messages with more than {threshold} stars will be displayed here."

        await interaction.response.send_message(content=content)

        logger.info(f"Starboard channel set to {channel.name} for server {interaction.guild.name}")

    @commands.command()
    @commands.is_owner()
    async def starboard_reset(self, ctx: commands.Context):
        '''DROPS ALL STARBOARD TABLES'''
        self.db.reset_starboard_tables()
        await ctx.send("Starboard database reset!")

        logger.info(f"Starboard tables reset globally by {ctx.author.name}")

async def setup(client: MiniSigma):
    await client.add_cog(StarBoard(client))