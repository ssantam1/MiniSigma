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
        return f"[{self.symbol}{self.suit}]" if not self.down else "[??]"
    

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
    

class BlackjackHand:
    '''Represents a hand in a blackjack game.'''
    def __init__(self, deck: Deck):
        self.cards: list[Card] = []
        self.deck = deck
        self.hit()
        self.hit()

    def hit(self) -> None:
        self.cards.append(self.deck.drawCard())

    def value(self) -> int:
        cards = [card for card in self.cards if not card.down]
        total = sum(11 if card.symbol == 'A' else 10 if card.symbol in 'JQK' else int(card.value) for card in cards) # Good luck reading this one-liner lol
        aces = sum(1 for card in cards if card.symbol == 'A')
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
    
    def is_busted(self) -> bool:
        return self.value() > 21

    def __str__(self) -> str:
        hand_str = ""
        for card in self.cards:
            hand_str += str(card) + " "
        hand_str += f"\nTotal: {self.value()}"
        return hand_str


class BlackjackInactiveView(discord.ui.View):
    '''View for when the game has ended.'''
    def __init__(self, db: DB.Database, user: discord.User, bet: int):
        super().__init__(timeout=None)
        self.db = db
        self.active_user = user
        self.bet = bet

    @discord.ui.button(label="Go Again!", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def start(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.active_user = interaction.user
        if not self.db.is_valid_bet(self.active_user.id, self.bet):
            logger.info(f"{self.active_user.name} tried to bet {self.bet} points on blackjack, but had insufficient funds")
            await interaction.response.send_message(f"Invalid bet amount: {self.bet}! You need more points!", ephemeral=True)
            return
        
        self.stop()
        logger.info(f"{self.active_user.name} bet {self.bet} points on blackjack")
        view = BlackjackView(db=self.db, user=self.active_user, bet=self.bet)
        await view.update(interaction)

    @discord.ui.button(label="Change bet", style=discord.ButtonStyle.secondary, emoji="💵")
    async def change_bet(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(BlackjackBetModal(self))


class BlackjackBetModal(discord.ui.Modal):
    '''Modal for changing the bet amount. (Only used in BlackjackInactiveView)'''
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
        
        self.view.bet = selection
        await interaction.response.edit_message(content=f"Current Stakes: {selection}", view=self.view)
        
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(f'Oops! @theothermaurice is dumb!\nScreenshot this error and send it to him!\n`{error}`', ephemeral=True)


class BlackjackView(discord.ui.View):
    def __init__(self, db: DB.Database, user: discord.User, bet: int = 0):
        '''View for the blackjack game.'''
        super().__init__(timeout=None)
        self.db = db
        self.user = user
        self.bet = bet
        self.db.place_bet(user.id, bet, "blackjack")

        self.deck = Deck()
        self.playerHand = BlackjackHand(self.deck)
        self.dealerHand = BlackjackHand(self.deck)
        self.dealerHand.cards[1].down = True

        self.embed = discord.Embed(title="BlackJack", color=discord.Color.green())
        self.embed.add_field(name="Dealer's Hand:", value=f"```{self.dealerHand}```", inline=False)
        self.embed.add_field(name="Player's Hand:", value=f"```{self.playerHand}```", inline=False)

    def update_hands(self):
        self.embed.set_field_at(0, name="Dealer's Hand:", value=f"```{self.dealerHand}```", inline=False)
        self.embed.set_field_at(1, name="Player's Hand:", value=f"```{self.playerHand}```", inline=False)

    async def send(self, interaction: discord.Interaction):
        await interaction.response.send_message(content=f"Current Stakes: {self.bet}", embed=self.embed, view=self)

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=f"Current Stakes: {self.bet}", embed=self.embed, view=self)

    async def endGame(self, interaction: discord.Interaction):
        self.update_hands()
        
        player = self.playerHand.value()
        dealer = self.dealerHand.value()

        if player > dealer and player < 21: # Standard player win
            win_str, win_amount = "Player wins!", self.bet*2
        elif dealer > player and dealer < 21: # Standard dealer win
            win_str, win_amount = "Dealer wins!", 0
        elif dealer > 21: # Dealer bust
            win_str, win_amount = "Dealer busts! Player wins!", self.bet*2
        elif player > 21: # Player bust
            win_str, win_amount = "Player busts! Dealer wins!", 0
        elif player == dealer: # Push
            win_str, win_amount = "It's a tie!", self.bet
        elif player == 21: # Player blackjack
            win_str, win_amount = "Player wins! Blackjack!", int(self.bet*2.5)
        else: # dealer == 21: Dealer blackjack
            win_str, win_amount = "Dealer wins!", 0
        
        if win_amount != 0:
            self.db.win_bet(self.user.id, win_amount, "blackjack")
            self.embed.set_footer(text=f"Winnings: {win_amount-self.bet} points")
            logger.info(f"{self.user.name} won {win_amount-self.bet} points in blackjack")
        else:
            self.embed.set_footer(text=f"Loss: {self.bet} points")

        self.embed.add_field(name="Result:", value=win_str, inline=False)
        await interaction.response.edit_message(embed=self.embed, view=BlackjackInactiveView(self.db, self.user, self.bet))
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👊")
    async def hit(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user != self.user:
            return
        
        self.playerHand.hit()
        if self.playerHand.is_busted():
            await self.endGame(interaction)
            return
        self.update_hands()
        await self.update(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.blurple, emoji="👋")
    async def stand(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user != self.user:
            return
        
        self.dealerHand.cards[1].down = False
        while self.dealerHand.value() < 17:
            self.dealerHand.hit()
            if self.dealerHand.is_busted():
                break
        await self.endGame(interaction)

class Gambling(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

    @app_commands.command(name="blackjack", description="Play a game of blackjack")
    @app_commands.describe(bet="The amount of money you want to bet")
    async def blackjack(self, interaction: discord.Interaction, bet: int = 0):
        if self.db.is_valid_bet(interaction.user.id, bet):
            logger.info(f"{interaction.user.name} issued /blackjack {bet}, ({interaction.channel})")
            view = BlackjackView(self.db, interaction.user, bet)
            await view.send(interaction)
        else:
            logger.info(f"{interaction.user.name} issued /blackjack {bet}, but had insufficient funds ({interaction.channel})")
            await interaction.response.send_message("Invalid bet amount! You need more points!", ephemeral=True)

async def setup(client: MiniSigma):
    await client.add_cog(Gambling(client))