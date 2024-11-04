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
import utility.database as DB
from utility.config import *
import csv

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

        embed = discord.Embed(url="https://cdn.discordapp.com/", color=EMBED_COLOR)
        embed.set_author(name=f"{target.name}'s Profile Picture", icon_url=pfp_url)
        embed.set_image(url=pfp_url)

        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def messages_in_channel(self, ctx: commands.Context):
        '''Replies with the number of messages in the channel'''
        message_count = 0
        perf_start = time.perf_counter()

        history = ctx.channel.history(limit=None, after=ctx.channel.created_at, before=ctx.message.created_at)
        history = [message async for message in history]
        message_count = len(history)

        perf_end = time.perf_counter()
        perf_time = perf_end - perf_start

        await ctx.reply(f"Done! Total messages: {message_count}\nTime: {perf_time: .2f} seconds")

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

        embed = discord.Embed(color=EMBED_COLOR)
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
    async def emojiname(self, ctx: commands.Context, emoji: str):
        '''Replies with a string representation of the emoji, (probably still a way to exploit this)'''
        emoji = emoji.replace("`", "")
        await ctx.reply(f"```{emoji}```")
    
    async def send_txt(self, ctx: commands.Context, list: list):
        '''Creates a txt file with the string, sends it to a channel, and deletes it'''
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
    async def users_to_csv(self, ctx: commands.Context):
        '''Replies with the user database in CSV format'''
        users = self.db.list_users() # list of tuples (id, username, upvotes, downvotes, offset)
        filename = "users.csv"

        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "Username", "Upvotes", "Downvotes", "Offset"])
            for user in users:
                writer.writerow(user)
        with open(filename, "rb") as f:
            await ctx.reply(file=discord.File(f, filename))
        os.remove(filename)

    @commands.command()
    async def memberotw(self, ctx: commands.Context):
        '''Replies with the member of the week'''
        motw = self.db.get_memberotw(ctx.guild.id)
        if motw:
            await ctx.reply(f"Member of the week: <@{motw[0]}>, with {motw[2]} score gained!")
        else:
            await ctx.reply("No member of the week found")

    @commands.command()
    async def messageotw(self, ctx: commands.Context):
        '''Replies with the message of the week'''
        message_id, channel_id, score = self.db.get_messageotw(ctx.guild.id)

        channel: discord.TextChannel = self.client.get_channel(channel_id)
        try:
            message: discord.Message = await channel.fetch_message(message_id)
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.reply("Message not found: " + str(e))
            return
        
        embed = discord.Embed(
            description=message.content,
            color=EMBED_COLOR
        )

        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )

        embed.add_field(
            name="Source",
            value=f"[Jump to message]({message.jump_url})",
            inline=False
        )

        if message.attachments:
            attachment = message.attachments[0]
            if attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
            else:
                embed.add_field(
                    name="Attachment",
                    value=f"[{attachment.filename}]({attachment.url})",
                    inline=False
                )

        embed.set_footer(text=str(message.id))

        await ctx.reply(f"Top message of this week:\n{message.channel.mention}, Score: {score}", embed=embed)
    
    @commands.command()
    @commands.is_owner()
    async def give_iq(self, ctx: commands.Context, user: discord.Member, iq: int):
        '''Gives a user a number of IQ'''
        # Add iq to user's offset
        self.db.c.execute("UPDATE Users SET offset = offset + ? WHERE id = ?", (iq, user.id))
        await ctx.send(f"{iq} IQ points have been given to {user.mention}")

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx: commands.Context):
        '''Restarts bot'''
        subprocess.Popen([sys.executable, "bot.py"])
        await ctx.send(f"Subprocess spawned, closing running client...")
        await self.client.close()

    @commands.command()
    @commands.is_owner()
    async def off(self, ctx: commands.Context):
        '''Turns off the bot'''
        await ctx.send("Shutting down...")
        await self.client.close()

async def setup(client: MiniSigma):
    await client.add_cog(Debug(client))