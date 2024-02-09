import datetime
import discord
from discord.ext import commands
import utility.database as DB
from bot import MiniSigma
from tqdm import tqdm
import logging

logger = logging.getLogger("client.scanner")

class Scanner(commands.Cog):
    '''Scanner for logging upvotes in message history'''

    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

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

        await prog_message.edit(content=prog_string + "✅ Scan done! Results recorded in log.")

async def setup(client: MiniSigma):
    await client.add_cog(Scanner(client))