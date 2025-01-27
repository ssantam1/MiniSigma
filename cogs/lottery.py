import random
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import app_commands
from bot import MiniSigma
from utility.config import EMBED_COLOR
from utility.database import Database
from utility.utils import nick_update

class Ticket(discord.ui.View):
    '''Represents a scratch ticket.'''
    def __init__(self, user: discord.User, db: Database):
        super().__init__(timeout=None)
        self.user = user
        self.db = db

    def get_lottery_result(self) -> tuple[str, str]:
        '''Randomly selects a result for a lottery ticket and returns the text and reward to display.'''

        # Possible outcomes are emojis with a message to display
        # ':gem: Jackpot!'          - 500 points - 1% chance
        # ':moneybag: Super Lucky!' - 100 points - 10% chance
        # ':dollar: Lucky!'         - 50 points  - 34% chance
        # ':coin: Normal!'          - 10 points  - 50% chance
        # ':poop: Unlucky!'         - 5 points   - 5% chance

        results = [
            (":gem: Jackpot!", "You won 500 points!", 500, 1),
            (":moneybag: Super Lucky!", "You won 100 points!", 100, 10),
            (":dollar: Lucky!", "You won 50 points!", 50, 34),
            (":coin: Normal!", "You won 10 points!", 10, 50),
            (":poop: Unlucky!", "You won 5 points!", 5, 5)
        ]

        weights = [result[3] for result in results]
        result = random.choices(results, weights=weights, k=1)[0]

        result_text, reward_text, reward, _ = result        
        self.db.give_lottery_reward(self.user.id, reward)

        return result_text, reward_text

    @discord.ui.button(label='Scratch!', style=discord.ButtonStyle.primary)
    async def scratch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.id == self.user.id:
            await interaction.response.send_message("You can't scratch someone else's ticket!", ephemeral=True)
            return

        button.label = 'Used'
        button.style = discord.ButtonStyle.gray
        button.disabled = True

        embed = interaction.message.embeds[0]
        embed.description = None

        result_text, reward_text = self.get_lottery_result()
        embed.add_field(name=result_text, value=reward_text)

        await nick_update(self.user, self.db.get_iq(self.user.id))

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
    
    def get_cooldown(self, user_id: int) -> int:
        '''Returns time remaining until the user can play the lottery again, 0 if they can play now.'''
        time_since_last_played: timedelta = self.db.get_lottery_cooldown(user_id) 

        if time_since_last_played is None:
            return 0

        cooldown_period = timedelta(days=1)
        time_remaining = cooldown_period - time_since_last_played

        if time_remaining.total_seconds() > 0:
            return int(time_remaining.total_seconds())
        return 0

    @app_commands.command(name="daily", description="Redeem your daily reward!")
    async def daily(self, interaction: discord.Interaction):
        '''Allows the user to play the lottery once per day.'''
        cooldown = self.get_cooldown(interaction.user.id)
        if cooldown > 0:
           await interaction.response.send_message(f"Please wait {cooldown} seconds before playing again!", ephemeral=True)
           return

        embed = self.create_embed()
        view = Ticket(interaction.user, self.db)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(client: MiniSigma):
    await client.add_cog(Lottery(client))