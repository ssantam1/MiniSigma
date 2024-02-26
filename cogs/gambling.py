import discord
from discord import app_commands
from discord.ext import commands
from bot import MiniSigma
import config
import random

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

class blackjack:
    def __init__(self):
        self.deck = deck()
        self.deck.shuffle()
        self.playerHand: list[card] = []
        self.dealerHand: list[card] = []
        self.playerHand.append(self.deck.drawCard())
        self.dealerHand.append(self.deck.drawCard())
        self.playerHand.append(self.deck.drawCard())
        self.dealerHand.append(self.deck.drawCard())
        self.dealerHandIsSecret = True
    
    def handValue(self, hand: list[card]) -> int:
        total = 0
        aces = 0
        for card in hand:
            if card.value == 'A':
                total += 11
                aces += 1
            elif card.value in ['J', 'Q', 'K']:
                total += 10
            else:
                total += int(card.value)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
    
    def isPlayerBlackjack(self) -> bool:
        return self.handValue(self.playerHand) == 21
    
    def isDealerBlackjack(self) -> bool:
        return self.handValue(self.dealerHand) == 21
    
    def isPlayerBust(self) -> bool:
        return self.handValue(self.playerHand) > 21
    
    def isDealerBust(self) -> bool:
        return self.handValue(self.dealerHand) > 21

    def playerHit(self) -> int:
        self.playerHand.append(self.deck.drawCard())
        handValue = self.handValue(self.playerHand)
        return handValue
    
    def dealerHit(self) -> int:
        self.dealerHand.append(self.deck.drawCard())
        handValue = self.handValue(self.dealerHand)
        return handValue
    
    def pickWinner(self) -> str:
        if self.isPlayerBlackjack() and not self.isDealerBlackjack():
            return "BlackJack! Player wins!"
        elif self.isDealerBlackjack() and not self.isPlayerBlackjack():
            return "BlackJack! Dealer wins!"
        elif self.isPlayerBust():
            return "Player bust! Dealer wins!"
        elif self.isDealerBust():
            return "Dealer bust! Player wins!"
        elif self.handValue(self.playerHand) > self.handValue(self.dealerHand):
            return "Player wins!"
        elif self.handValue(self.playerHand) < self.handValue(self.dealerHand):
            return "Dealer wins!"
        else:
            return "It's a tie!"

    def showDealerHand(self) -> str:
        dealer_hand_str = ""
        if self.dealerHandIsSecret:
            dealer_hand_str += str(self.dealerHand[0]) + " "
            dealer_hand_str += "[? ?]\nTotal: ?"
        else:
            for card in self.dealerHand:
                dealer_hand_str += str(card) + " "
            dealer_hand_str += f"\nTotal: {self.handValue(self.dealerHand)}"
        return dealer_hand_str
    
    def showPlayerHand(self) -> str:
        player_hand_str = ""
        for card in self.playerHand:
            player_hand_str += str(card) + " "
        player_hand_str += f"\nTotal: {self.handValue(self.playerHand)}"
        return player_hand_str

class BlackjackView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.blackjack = blackjack()
        self.embed = discord.Embed(title="BlackJack", color=discord.Color.green())
        self.embed.add_field(name="Dealer's Hand:", value=self.blackjack.showDealerHand())
        self.embed.add_field(name="Player's Hand:", value=self.blackjack.showPlayerHand())

    async def send(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.embed, view=self)
        if self.blackjack.isPlayerBlackjack() or self.blackjack.isDealerBlackjack():
            await self.finish(interaction)

    async def finish(self, interaction: discord.Interaction):
        self.update_hands()
        self.embed.add_field(name="Result:", value=self.blackjack.pickWinner(), inline=False)
        await interaction.response.edit_message(embed=self.embed, view=None)
        self.stop()

    def update_hands(self):
        self.embed.set_field_at(0, name="Dealer's Hand:", value=self.blackjack.showDealerHand())
        self.embed.set_field_at(1, name="Player's Hand:", value=self.blackjack.showPlayerHand())

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.blackjack.playerHit()
        self.update_hands()
        if self.blackjack.isPlayerBust():
            await self.finish(interaction)
        else:
            await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.primary)
    async def stand(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.blackjack.dealerHandIsSecret = False
        while self.blackjack.handValue(self.blackjack.dealerHand) < 17:
            self.blackjack.dealerHit()
            if self.blackjack.isDealerBust():
                await self.finish(interaction)
                return
        await self.finish(interaction)

class Gambling(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client

    @app_commands.command(name="blackjack", description="Play a game of blackjack")
    async def blackjack(self, interaction: discord.Interaction):
        view = BlackjackView()
        await view.send(interaction)

async def setup(client: MiniSigma):
    await client.add_cog(Gambling(client))