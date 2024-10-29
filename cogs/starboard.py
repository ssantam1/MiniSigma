import logging
import discord
from discord.ext import commands

from bot import MiniSigma

logger = logging.getLogger("client.StarBoard")

class StarBoard(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db = client.db
        self.score_threshold = 1  # Maybe move this to a config file later

    def create_embed(self, message: discord.Message) -> discord.Embed:
        '''Creates an embed for displaying a message on the starboard'''
        embed = discord.Embed(
            description=message.content,
            color=discord.Color.gold()
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        embed.add_field(
            name="Source",
            value=f"[Jump to message]({message.jump_url})"
        )
        embed.set_footer(
            text=f"Message ID: {message.id}"
        )
        return embed
    
    def num_stars(self, message: discord.Message):
        for reaction in message.reactions:
            if reaction.emoji == "⭐":
                return reaction.count
    
    async def send_starboard_message(self, target_channel:discord.TextChannel, message: discord.Message):
        '''Displays a message in the starboard channel'''
        await target_channel.send(
            content=f"⭐ {self.num_stars(message)} | <#{message.channel.id}>",
            embed=self.create_embed(message)
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
        if event.emoji.name != "⭐":
            return

        channel = self.client.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)

        logger.info(f"Registered star reaction on message '{channel}'")

        # Not final implementation, simply testing in prod lol
        await self.send_starboard_message(channel, message)

async def setup(client: MiniSigma):
    await client.add_cog(StarBoard(client))