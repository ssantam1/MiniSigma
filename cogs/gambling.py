import discord
from discord import app_commands
from discord.ext import commands
from bot import MiniSigma
import utility.database as DB
import logging
import random

logger = logging.getLogger("client.gambling")

# Blackjack game

class Card:
    '''Represents a playing card with a suit and value.'''
    def __init__(self, suit: str, value: int):
        self.suit = suit
        self.value = value
        self.down = False

    @property
    def symbol(self) -> str:
        if self.value <= 10: return str(self.value)
        return { 11: 'J', 12: 'Q', 13: 'K', 14: 'A' }[self.value]

    def __str__(self) -> str:
        return f"[{self.symbol} {self.suit}]" if not self.down else "[? ?]"
    
class Deck:
    '''Represents a deck of playing cards.'''
    def __init__(self, size: int = 1):
        self.cards: list[Card] = []
        for _ in range(size):
            self.cards.extend([Card(suit, value) for suit in ["♠", "♣", "♦", "♥"] for value in range(2, 15)])
        self.shuffle()
    
    def shuffle(self) -> None:
        # Fisher-Yates shuffle
        for i in range(len(self.cards) - 1, 0, -1):
            r = random.randint(0, i)
            self.cards[i], self.cards[r] = self.cards[r], self.cards[i]
    
    def drawCard(self) -> Card:
        return self.cards.pop()

class BlackjackInactiveView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.active_user = None

    @discord.ui.button(label="Go Again!", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def start(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.stop()
        view = BlackjackView()
        await view.update(interaction)

    @discord.ui.button(label="Change bet", style=discord.ButtonStyle.secondary, emoji="💵")
    async def change_bet(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.active_user = interaction.user
        await interaction.response.send_modal(BlackjackBetModal(self))

class BlackjackBetModal(discord.ui.Modal):
    def __init__(self, view: BlackjackInactiveView):
        super().__init__(title="Change bet")
        self.view = view

    bet = discord.ui.TextInput(label="Bet amount:")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            selection = int(self.bet.value)
        except ValueError:
            await interaction.response.send_message('Invalid input! Please enter an integer.', ephemeral=True)
            return

class BlackjackView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.deck = Deck()
        self.playerHand = [self.deck.drawCard(), self.deck.drawCard()]
        self.dealerHand = [self.deck.drawCard(), self.deck.drawCard()]
        self.dealerHand[1].down = True

        self.embed = discord.Embed(title="BlackJack", color=discord.Color.green())
        self.embed.add_field(name="Dealer's Hand:", value=f"```{self.handStr(self.dealerHand)}```", inline=False)
        self.embed.add_field(name="Player's Hand:", value=f"```{self.handStr(self.playerHand)}```", inline=False)

    def update_hands(self):
        self.embed.set_field_at(0, name="Dealer's Hand:", value=f"```{self.handStr(self.dealerHand)}```", inline=False)
        self.embed.set_field_at(1, name="Player's Hand:", value=f"```{self.handStr(self.playerHand)}```", inline=False)

    async def send(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.embed, view=self)

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.embed, view=self)

    @staticmethod
    def handValue(hand: list[Card]) -> int:
        hand = [card for card in hand if not card.down]
        total = sum(11 if card.symbol == 'A' else 10 if card.symbol in 'JQK' else int(card.value) for card in hand)
        aces = sum(1 for card in hand if card.symbol == 'A')
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
    
    @staticmethod
    def handStr(hand: list[Card]) -> str:
        hand_str = ""
        for card in hand:
            hand_str += str(card) + " "
        hand_str += f"\nTotal: {BlackjackView.handValue(hand)}"
        return hand_str

    @staticmethod
    def endCheck(hand: list[Card]) -> bool:
        return BlackjackView.handValue(hand) >= 21
    
    def winStr(self) -> str:
        player = self.handValue(self.playerHand)
        dealer = self.handValue(self.dealerHand)
        if player > 21: return "Player busts, dealer wins!"
        if dealer > 21: return "Dealer busts, player wins!"
        if player == dealer: return "It's a tie!"
        if player > dealer: return "Player wins!"
        return "Dealer wins!"

    async def endGame(self, interaction: discord.Interaction):
        self.update_hands()
        self.embed.add_field(name="Result:", value=self.winStr(), inline=False)
        await interaction.response.edit_message(embed=self.embed, view=BlackjackInactiveView())
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👊")
    async def hit(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.playerHand.append(self.deck.drawCard())
        if self.endCheck(self.playerHand):
            await self.endGame(interaction)
            return
        self.update_hands()
        await self.update(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.blurple, emoji="👋")
    async def stand(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.dealerHand[1].down = False
        while self.handValue(self.dealerHand) < 17:
            self.dealerHand.append(self.deck.drawCard())
            if self.endCheck(self.dealerHand):
                break
        await self.endGame(interaction)

class Gambling(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

    @app_commands.command(name="blackjack", description="Play a game of blackjack")
    async def blackjack(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user.name} issued /blackjack, ({interaction.channel})")
        view = BlackjackView()
        await view.send(interaction)

async def setup(client: MiniSigma):
    await client.add_cog(Gambling(client))