import discord
from discord import app_commands
from discord.ext import commands
from bot import MiniSigma
import logging
import random

logger = logging.getLogger("client.gambling")

class card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f"[{self.value} {self.suit}]"
    
class deck:
    def __init__(self):
        self.cards: list[card] = []
        self.build()
        self.shuffle()

    def build(self):
        for suit in ["♠", "♣", "♦", "♥"]:
            for value in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']:
                self.cards.append(card(suit, value))
    
    def shuffle(self):
        for i in range(len(self.cards) - 1, 0, -1):
            r = random.randint(0, i)
            self.cards[i], self.cards[r] = self.cards[r], self.cards[i]
    
    def drawCard(self):
        return self.cards.pop()
    
class hand:
    def __init__(self, deck: deck):
        self.cards: list[card] = []
        self.addCard(deck.drawCard())
        self.addCard(deck.drawCard())
    
    def addCard(self, card: card):
        self.cards.append(card)
    
    def handValue(self) -> int:
        total = sum(11 if card.value == 'A' else 10 if card.value in ['J', 'Q', 'K'] else int(card.value) for card in self.cards)
        aces = sum(1 for card in self.cards if card.value == 'A')
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
    
    def isBlackjack(self) -> bool:
        return self.handValue() == 21
    
    def isBust(self) -> bool:
        return self.handValue() > 21
    
    def __str__(self, secret: bool = False):
        hand_str = ""
        if secret:
            hand_str += str(self.cards[0]) + " [? ?]"
        else:
            for card in self.cards:
                hand_str += str(card) + " "
        hand_str += f"\nTotal: {self.handValue()}"
        return hand_str

class BlackjackView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.deck = deck()
        self.playerHand = hand(self.deck)
        self.dealerHand = hand(self.deck)

        self.embed = discord.Embed(title="BlackJack", color=discord.Color.green())
        self.embed.add_field(name="Dealer's Hand:", value=self.dealerHand)
        self.embed.add_field(name="Player's Hand:", value=self.playerHand)

    def update_hands(self):
        self.embed.set_field_at(0, name="Dealer's Hand:", value=self.dealerHand)
        self.embed.set_field_at(1, name="Player's Hand:", value=self.playerHand)
    
    def pickWinner(self) -> str:
        if self.playerHand.isBlackjack() and not self.dealerHand.isBlackjack():
            return "BlackJack! Player wins!"
        elif self.dealerHand.isBlackjack() and not self.playerHand.isBlackjack():
            return "BlackJack! Dealer wins!"
        elif self.playerHand.isBust():
            return "Player bust! Dealer wins!"
        elif self.dealerHand.isBust():
            return "Dealer bust! Player wins!"
        elif self.playerHand.handValue() > self.dealerHand.handValue():
            return "Player wins!"
        elif self.playerHand.handValue() < self.dealerHand.handValue():
            return "Dealer wins!"
        else:
            return "It's a tie!"

    async def send(self, interaction: discord.Interaction):
            await interaction.response.send_message(embed=self.embed, view=self)

    async def endGame(self, interaction: discord.Interaction):
        self.update_hands()
        self.embed.add_field(name="Result:", value=self.pickWinner(), inline=False)
        await interaction.response.edit_message(embed=self.embed, view=None)
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.playerHand.addCard(self.deck.drawCard())
        if self.playerHand.isBust() or self.playerHand.isBlackjack():
            await self.endGame(interaction)
            return
        self.update_hands()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.primary)
    async def stand(self, interaction: discord.Interaction, _: discord.ui.Button):
        while self.dealerHand.handValue() < 17:
            self.dealerHand.addCard(self.deck.drawCard())
            if self.dealerHand.isBust():
                break
        await self.endGame(interaction)

class Gambling(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client

    @app_commands.command(name="blackjack", description="Play a game of blackjack")
    async def blackjack(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user.name} issued /blackjack, ({interaction.channel})")
        view = BlackjackView()
        await view.send(interaction)

async def setup(client: MiniSigma):
    await client.add_cog(Gambling(client))