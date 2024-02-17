import datetime
import discord
from discord.ext import commands
import utility.database as DB
from bot import MiniSigma
from tqdm import tqdm
import logging
from typing import AsyncIterator
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

    async def scan_channel(self, channel: discord.TextChannel) -> None:
        (upvote, downvote) = self.db.get_emojis(channel.guild.id)
        end_pt = datetime.datetime.now(datetime.timezone.utc)
        overall_diff: datetime.timedelta = end_pt - channel.created_at.replace(tzinfo=datetime.timezone.utc)
        
        print(f"Starting scan on channel: ({channel.name}), Start date: {channel.created_at.strftime('%Y-%m-%d')}")

        upvoted_msg_count, downvoted_msg_count = 0, 0
        pbar = tqdm(total=overall_diff.days, unit="day", unit_scale=True)

        async for message in channel.history(limit=None, after=channel.created_at, before=end_pt):
            for reaction in message.reactions:
                emoji = str(reaction.emoji)
                if emoji not in (upvote, downvote):
                    continue

                if emoji == upvote:
                    upvoted_msg_count += 1
                    async for voter in reaction.users():
                        if voter.id == message.author.id:
                            continue
                        self.db.upvote_user(message.author.id, 1, voter.id)

                elif emoji == downvote:
                    downvoted_msg_count += 1
                    async for voter in reaction.users():
                        if voter.id == message.author.id:
                            continue
                        self.db.downvote_user(message.author.id, 1, voter.id)

                else:
                    raise Exception("Emoji was in vote_strings, but didn't match either case. How did you get here?")
                
            iter_diff: datetime.timedelta = message.created_at - channel.created_at
            pbar.n = iter_diff.days
            pbar.update()

        pbar.close()
        logger.info(f"Finished scanning channel, upvoted messages: {upvoted_msg_count}, downvoted messages: {downvoted_msg_count}")

    async def enter_reactions(self, guild: discord.Guild):
        (upvote, downvote) = self.db.get_emojis(guild.id)
        
        for channel in guild.text_channels:
            logger.info(f"Scanning channel: {channel.name}, from creation date: {channel.created_at.strftime('%Y-%m-%d')}")

            async for message in channel.history(limit=None, after=channel.created_at, before=datetime.datetime.now()):
                for reaction in message.reactions:

                    if str(reaction.emoji) not in (upvote, downvote):
                        continue

                    async for voter in reaction.users():
                        if voter.id == message.author.id:
                            continue
                        self.db.add_reaction(voter.id, message.author.id, message.id, channel.id, guild.id, 1 if str(reaction.emoji) == upvote else -1, message.created_at.strftime('%Y-%m-%d %H:%M:%S'))

        logger.info(f"Finished scanning guild: {guild.name}")

    @commands.command()
    async def enter_reactions_guild(self, ctx: commands.Context):
        logger.info(f"{ctx.author.name} issued !enter_reactions_guild, ({ctx.channel})")
        await ctx.send(f"Entering reactions for guild: {ctx.guild.name}")

        start_time = time.perf_counter()
        await self.enter_reactions(ctx.guild)
        total_time = time.perf_counter() - start_time
        
        await ctx.reply(f"Reactions entered! Total time: {total_time:.2f} seconds.")

    @commands.command()
    async def scan_target(self, ctx: commands.Context, channel: discord.TextChannel):
        await ctx.send(f"Scanning target: {channel.name}, from creation date: {channel.created_at.strftime('%Y-%m-%d')}")
        await self.scan_channel(channel)
        await ctx.reply(f"Scan done! Results recorded in log.")

    @commands.command()
    async def scan_guild(self, ctx: commands.Context):
        prog_string = "Beginning scan on guild:\n"
        prog_message = await ctx.send(prog_string)

        for channel in ctx.guild.text_channels:
            # Exclude plans channel
            if channel.id == 779432929445150811:
                continue
            
            await prog_message.edit(content=prog_string + f"- Scanning {channel.name}...")
            await self.scan_channel(channel)
            prog_string += f"- Finished scan on {channel.name}!\n"
            await prog_message.edit(content=prog_string)

        await prog_message.edit(content=prog_string + "Historical recording complete, populating data.\n")
        await self.fill_names(None)

        await prog_message.edit(content=prog_string + "✅ Scan done! Results recorded in log.")

    async def get_history_list(self, channel: discord.TextChannel) -> list[discord.Message]:
        start_pt = channel.created_at
        end_pt = datetime.datetime.now()

        hist: list[discord.Message] = [message async for message in channel.history(limit=None, after=start_pt, before=end_pt)]

        return hist

    @commands.command()
    async def benchmark_scan(self, ctx: commands.Context, channel: discord.TextChannel = None):
        '''Benchmark scanning one channel'''
        channel = ctx.channel if channel is None else channel
        logger.info(f"{ctx.author.name} issued !benchmark_scan, {channel}, ({ctx.channel})")

        start_time = time.perf_counter()
        hist: list[discord.Message] = await self.get_history_list(channel)
        flatten_time = time.perf_counter() - start_time
        logger.info(f"Flattening {len(hist)} messages done in {flatten_time:.2f} seconds. First poster: {hist[0].author.name}")
        await ctx.reply(f"Flattening: {flatten_time:.2f} seconds")

        start_time = time.perf_counter()
        (upvote, downvote) = self.db.get_emojis(channel.guild.id)
        for message in hist:
            for reaction in message.reactions:
                if str(reaction.emoji) not in (upvote, downvote):
                    continue

                async for voter in reaction.users():
                    if voter.id == message.author.id:
                        continue
                    self.db.add_reaction(voter.id, message.author.id, message.id, channel.id, channel.guild.id, 1 if str(reaction.emoji) == upvote else -1, message.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        reaction_enter_time = time.perf_counter() - start_time
        logger.info(f"Entering reactions for {len(hist)} messages done in {reaction_enter_time:.2f} seconds.")
        await ctx.reply(f"Entering reactions: {reaction_enter_time:.2f} seconds")

        start_time = time.perf_counter()
        upvoted_msg_count, downvoted_msg_count = 0, 0
        for message in hist:
            for reaction in message.reactions:
                emoji = str(reaction.emoji)
                if emoji not in (upvote, downvote):
                    continue

                if emoji == upvote:
                    upvoted_msg_count += 1
                    async for voter in reaction.users():
                        if voter.id == message.author.id:
                            continue
                        self.db.upvote_user(message.author.id, 1, voter.id)

                elif emoji == downvote:
                    downvoted_msg_count += 1
                    async for voter in reaction.users():
                        if voter.id == message.author.id:
                            continue
                        self.db.downvote_user(message.author.id, 1, voter.id)

                else:
                    raise Exception("Emoji was in vote_strings, but didn't match either case. How did you get here?")
        scan_time = time.perf_counter() - start_time
        logger.info(f"Scanning {len(hist)} messages done in {scan_time:.2f} seconds. Upvoted: {upvoted_msg_count}, Downvoted: {downvoted_msg_count}")
        await ctx.reply(f"Scanning: {scan_time:.2f} seconds")

async def setup(client: MiniSigma):
    await client.add_cog(Scanner(client))