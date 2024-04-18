import re
import os
import json
import random
import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma
import utility.bumper_generator as bumper_generator


class Fun(commands.Cog):

    def __init__(self, client: MiniSigma) -> None:
        self.client = client
        self.resources_dir = os.path.join(os.path.curdir, 'resources')

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        msg_text = msg.clean_content.lower()

        if "piccolo" in msg_text:
            fpath = os.path.join(self.resources_dir, "piccolo.mp4")
            with open(fpath, "rb") as file:
                piccolo = discord.File(file, "piccolo.mp4")

            await msg.channel.send(file = piccolo)

        if "kys" in msg_text:
            response = "https://media.tenor.com/67LIumILNRsAAAAd/ltg-low-tier-god.gif"
            await msg.channel.send(response)

        if self.client.user.mentioned_in(msg) and not msg.mention_everyone and not msg.author.bot:
            fpath = os.path.join(self.resources_dir, "quotes.json")
            with open(fpath, "r") as file:
                quotes = json.load(file)
                selected_quote = random.choice(quotes)
        
            await msg.reply(selected_quote)

        # Brazilian time unit conversion (inside joke)
        if msg.author.id == 249951720598142977:
            if "a bit" in msg_text:
                reply = f'Brazilian time unit detected: "a bit"\nAmerican time translation: "{random.randint(2,12)} hours"'
                await msg.reply(content=reply)
            elif "a min" in msg_text:
                reply = f'Brazilian time unit detected: "a min"\nAmerican time translation: "{random.randint(2,12)} days"'
                await msg.reply(content=reply)
            elif "a sec" in msg_text:
                reply = f'Brazilian time unit detected: "a sec"\nAmerican time translation: "{random.randint(2,12)} years"'
                await msg.reply(content=reply)

    @commands.command()
    async def roll(self, ctx: commands.Context, sides: int = 6):
        if sides <= 0:
            await ctx.send("Whoops! You can't roll a die with less than 1 side. Try again.")
            return

        roll_result = random.randint(1, sides)
        await ctx.send(f"Rolling a {sides}-sided die: You rolled a {roll_result}!")

    @app_commands.command(name="adultswim", description="Generate an AdultSwim bumper image with any text")
    @app_commands.describe(content="The text to put in the bumper. Wrap in square brackets for authentic [adult swim] feel.")
    @app_commands.describe(small="Set to true for a smaller version with less empty space.")
    async def adultswim(self, interaction: discord.Interaction, content: str, small: bool = False):
        bumper_generator.generate(content, small)
        fpath = os.path.join(self.resources_dir, "bumper.png")
        with open(fpath, "rb") as file:
            bumper = discord.File(file, "bumper.png")

        await interaction.response.send_message(file=bumper)

async def setup(client: MiniSigma):
    await client.add_cog(Fun(client))