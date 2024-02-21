import datetime
import discord
from discord.ext import commands
import utility.database as DB
from bot import MiniSigma
import logging
import time

logger = logging.getLogger("client.scanner")

class Scanner(commands.Cog):
    '''Scanner for logging upvotes in message history'''

    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

    @commands.command()
    async def fill_names(self, _: commands.Context):
        '''Go through the database and fill in the names of users'''
        for user in self.db.list_users():
            try:
                member = await self.client.fetch_user(user[0])
                self.db.update_username(user[0], member.name)
            except discord.errors.NotFound:
                self.db.update_username(user[0], "Unknown")

    async def scan_guild_history(self, guild: discord.Guild):
        (upvote, downvote) = self.db.get_emojis(guild.id)
        
        for channel in guild.text_channels:
            logger.info(f"Scanning channel: {channel.name}, from creation date: {channel.created_at.strftime('%Y-%m-%d')}")

            async for message in channel.history(limit=None, after=channel.created_at, before=datetime.datetime.now()):
                for reaction in message.reactions:

                    if str(reaction.emoji) not in [upvote, downvote]:
                        continue

                    voters = [voter async for voter in reaction.users()]
                    for voter in voters:
                        if voter.id == message.author.id:
                            continue

                        if str(reaction.emoji) == upvote:
                            self.db.upvote_user(message.author.id, 1, voter.id)
                            self.db.add_reaction(voter.id, message, 1, message.created_at.isoformat())
                            
                        else:
                            self.db.downvote_user(message.author.id, 1, voter.id)
                            self.db.add_reaction(voter.id, message, -1, message.created_at.isoformat())

        logger.info(f"Finished scanning guild: {guild.name}")

    @commands.command()
    async def scan_guild(self, ctx: commands.Context):
        logger.info(f"{ctx.author.name} issued !scan_guild, ({ctx.channel})")
        await ctx.send(f"Entering reactions for guild: {ctx.guild.name}")

        start_time = time.perf_counter()
        await self.scan_guild_history(ctx.guild)
        total_time = time.perf_counter() - start_time
        
        await ctx.reply(f"Scan Completed! Total time: {total_time:.2f} seconds.")

    @commands.command()
    async def scan_all_guilds(self, ctx: commands.Context):
        logger.info(f"{ctx.author.name} issued !scan_all_guilds, ({ctx.channel})")
        await ctx.send(f"Entering reactions for all guilds")

        start_time = time.perf_counter()
        for guild in self.client.guilds:
            await self.scan_guild_history(guild)
        total_time = time.perf_counter() - start_time
        
        await ctx.reply(f"Reactions entered! Total time: {total_time:.2f} seconds.")

    async def flat_history_list(self, channel: discord.TextChannel) -> list[discord.Message]:
        start_pt = channel.created_at
        end_pt = datetime.datetime.now()

        hist: list[discord.Message] = [message async for message in channel.history(limit=None, after=start_pt, before=end_pt)]

        return hist

async def setup(client: MiniSigma):
    await client.add_cog(Scanner(client))