import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma
import subprocess
import sys
import os
import time
import datetime
import logging
from zoneinfo import ZoneInfo
from tqdm import tqdm
import utility.database as DB

logger = logging.getLogger("client.debug")

class Debug(commands.Cog):
    '''Cog used for debug and testing basic features'''

    def __init__(self, client: MiniSigma):
        self.client = client
        self.start_time = datetime.datetime.now(tz=ZoneInfo('US/Eastern'))
        self.db: DB.Database = client.db

    @app_commands.command(name="pfp", description="Displays the profile pic of target user. Target defaults to command user if empty")
    @app_commands.describe(target="The server member you would like an image of")
    async def pfp(self, interaction: discord.Interaction, target: discord.Member = None):
        '''Replies with a higher-res image of target's profile picture'''
        target = interaction.user if target == None else target

        pfp_url = str(target.display_avatar.url)

        embed = discord.Embed(url="https://cdn.discordapp.com/", color=self.client.config.EMBED_COLOR)
        embed.set_author(name=f"{target.name}'s Profile Picture", icon_url=pfp_url)
        embed.set_image(url=pfp_url)

        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def messages_in_channel(self, ctx: commands.Context):
        '''Replies with the number of messages in the channel'''
        await ctx.send(f'Beginning scan of channel...')
        message_count = 0
        perf_start = time.perf_counter()

        hist = ctx.channel.history(limit=None, after=ctx.channel.created_at, before=ctx.message.created_at)
        
        hist = [message async for message in hist]

        for _ in hist:
            message_count += 1

        perf_end = time.perf_counter()
        perf_time = perf_end - perf_start

        await ctx.send(f"Done! Total messages: {message_count}\nTime: {perf_time: .2f} seconds")

    @commands.command()
    async def flatten_time(self, ctx: commands.Context, channel: discord.TextChannel):
        await ctx.send("Flattening channel history object to list...")
        start_pt = channel.created_at
        end_pt = ctx.message.created_at
        overall_diff: datetime.timedelta = end_pt - start_pt

        hist: list[discord.Message] = []
        pbar = tqdm(total=overall_diff.days, unit="day", unit_scale=True)
        perf_start = time.perf_counter()

        async for message in channel.history(limit=None, after=start_pt, before=end_pt):
            hist.append(message)
            iter_diff: datetime.timedelta = message.created_at - start_pt
            pbar.n = iter_diff.days
            pbar.update()
            
        pbar.close()
        perf_time = time.perf_counter() - perf_start
        await ctx.reply(f"Flattening {len(hist)} messages done in{perf_time: .2f} seconds. First poster: {hist[0].author.name}")

    @app_commands.command(name="uptime", description="Displays the last time the bot was turned on")
    async def uptime(self, interaction: discord.Interaction):
        '''Displays the last time the bot was turned on and current session duration'''
        logger.info(f"{interaction.user.name} issued /uptime, ({interaction.channel})")

        curr_time = datetime.datetime.now(tz=ZoneInfo('US/Eastern'))
        uptime: datetime.timedelta = curr_time - self.start_time

        days = uptime.days
        seconds = uptime.seconds
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        embed = discord.Embed(color=self.client.config.EMBED_COLOR)
        embed.set_author(name=f"{self.client.user.name} Uptime", icon_url=self.client.user.display_avatar.url)
        embed.add_field(name="Start Time:", value=self.start_time.strftime('%Y-%m-%d, %H:%M:%S'), inline=False)
        embed.add_field(name="Time Since Start:", value=f"{days} days, {hours} hr, {minutes} min, {seconds}s", inline=False)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def created_at(self, ctx: commands.Context):
        '''Replies with the creation date of the message'''
        await ctx.reply(f"`{str(ctx.message.created_at)}`")

    @commands.command()
    async def guild_epoch(self, ctx: commands.Context):
        '''Replies with the creation date of the guild'''
        await ctx.reply(f"Guild creation datetime: {ctx.guild.created_at}")

    @commands.command()
    async def guild_id(self, ctx: commands.Context):
        '''Replies with the ID of the current guild'''
        await ctx.reply(f"`{ctx.guild.id}`")

    @commands.command()
    async def emojiname(self, ctx: commands.Context, emoji: str):
        '''Replies with a string, super unsafe lol'''
        await ctx.reply(f"```{emoji}```")
    
    async def send_txt(self, ctx: commands.Context, list: list):
        '''Creates a txt file with the string and sends it to a channel before deleting it'''
        with open("temp.txt", "w", encoding='utf-8') as f:
            # create string, where each element is a new line
            string = "\n".join([str(x) for x in list])
            f.write(string)
        with open("temp.txt", "rb") as f:
            file = discord.File(f, "temp.txt")
            await ctx.reply(file=file)
        os.remove("temp.txt")

    @commands.command()
    async def dump_users(self, ctx: commands.Context):
        '''Replies with the user database'''
        await self.send_txt(ctx, self.db.list_users())

    @commands.command()
    async def dump_fans(self, ctx: commands.Context):
        '''Replies with the fan database'''
        await self.send_txt(ctx, self.db.list_fans())

    @commands.command()
    async def dump_emojis(self, ctx: commands.Context):
        '''Replies with the emoji database'''
        await self.send_txt(ctx, self.db.list_emojis())

    @commands.command()
    async def dump_reactions(self, ctx: commands.Context):
        '''Replies with the reaction database'''
        await self.send_txt(ctx, self.db.list_reactions())

    @commands.command()
    async def restart(self, ctx: commands.Context):
        '''Restarts bot'''
        subprocess.Popen([sys.executable, "bot.py"])
        await ctx.send(f"Subprocess spawned, closing running client...")
        await self.client.close()

    @commands.command()
    async def off(self, ctx: commands.Context):
        '''Turns off the bot'''
        await ctx.send("Shutting down...")
        await self.client.close()

async def setup(client: MiniSigma):
    await client.add_cog(Debug(client))