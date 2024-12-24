import random
import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma
from utility.config import EMBED_COLOR
from utility.database import Database
from cogs.voting import Voting

class Ticket(discord.ui.View):
    '''Represents a scratch ticket.'''
    def __init__(self, user: discord.User, db: Database):
        super().__init__(timeout=None)
        self.user = user
        self.db = db

    def get_lottery_result(self):
        '''Randomly selects a result for a lottery ticket and returns the text and reward to display.'''

        # Possible outcomes are emojis with a message to display
        # ':gem: Jackpot!'          - 500 points - 1% chance
        # ':moneybag: Super Lucky!' - 100 points - 10% chance
        # ':dollar: Lucky!'         - 50 points  - 34% chance
        # ':coin: Normal!'          - 10 points  - 50% chance
        # ':poop: Unlucky!'         - 5 points   - 5% chance

        result_number = random.choices([0, 1, 2, 3, 4], weights=[1, 10, 34, 50, 5])[0]

        rewards = [500, 100, 50, 10, 5]
        reward = rewards[result_number]
        self.db.give_lottery_reward(self.user.id, reward)

        results = [
            (":gem: Jackpot!", "You won 500 points!"),
            (":moneybag: Super Lucky!", "You won 100 points!"),
            (":dollar: Lucky!", "You won 50 points!"),
            (":coin: Normal!", "You won 10 points!"),
            (":poop: Unlucky!", "You won 5 points!")
        ]
        return results[result_number]

    @discord.ui.button(label='Scratch!', style=discord.ButtonStyle.primary)
    async def scratch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.id == self.user.id:
            await interaction.response.send_message("You can't scratch someone else's ticket!", ephemeral=True)

        button.label = 'Used'
        button.style = discord.ButtonStyle.gray
        button.disabled = True

        embed = interaction.message.embeds[0]
        embed.description = None

        result_text, reward_text = self.get_lottery_result()
        embed.add_field(name=result_text, value=reward_text)

        await Voting.nick_update(self.user, self.db.get_iq(self.user.id))

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()

class Lottery(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db = client.db
        self.db.create_lottery_tables()

    def create_embed(self) -> discord.Embed:
        '''Creates an embed with three blank spots to be "scratched" later'''
        return discord.Embed(title="Scratch Ticket", description=":grey_question: Scratch to claim!", color=EMBED_COLOR)

    @app_commands.command(name="daily", description="Redeem your daily reward!")
    async def daily(self, interaction: discord.Interaction):
        #TODO: Check cooldown
        embed = self.create_embed()
        view = Ticket(interaction.user, self.db)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(client: MiniSigma):
    await client.add_cog(Lottery(client))