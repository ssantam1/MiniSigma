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
    @commands.is_owner()
    async def give_iq(self, ctx: commands.Context, user: discord.Member, iq: int):
        '''Gives a user a number of IQ'''
        # Add iq to user's offset
        self.db.c.execute("UPDATE Users SET offset = offset + ? id = ?", (iq, user.id))
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