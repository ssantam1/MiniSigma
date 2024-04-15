import sqlite3
from datetime import datetime
from discord import Message

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("database.db")
        self.c = self.conn.cursor()
        self.create_tables()
    
    def version(self):
        self.c.execute("select sqlite_version();")
        return self.c.fetchall()
    
    def create_tables(self):
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                upvotes INTEGER,
                downvotes INTEGER,
                offset INTEGER
            )''')
        
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS FansAndHaters (
                user_id INTEGER,
                fan_or_hater_id INTEGER,
                upvotes INTEGER,
                downvotes INTEGER,
                PRIMARY KEY (user_id, fan_or_hater_id),
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (fan_or_hater_id) REFERENCES Users(id)
            )''')
        
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS Emojis (
                guild_id INTEGER PRIMARY KEY,
                upvote TEXT,
                downvote TEXT
            )''')
        
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS Messages (
                id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                guild_id INTEGER,
                author_id INTEGER,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY (author_id) REFERENCES Users(id),
                FOREIGN KEY (guild_id) REFERENCES Emojis(guild_id)
            )''')
        
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS Reactions (
                voter_id INTEGER,
                message_id INTEGER,
                vote_type INTEGER,
                timestamp TEXT,
                PRIMARY KEY (voter_id, message_id, vote_type),
                FOREIGN KEY (voter_id) REFERENCES Users(id),
                FOREIGN KEY (message_id) REFERENCES Messages(id)
            )''')
        
        self.conn.commit()

        self.create_gambling()

    # ========== USER MANAGEMENT ==========
    
    def add_user(self, id: int, name: str):
        self.c.execute("INSERT OR IGNORE INTO Users (id, username, upvotes, downvotes, offset) VALUES (?, ?, ?, ?, ?)", (id, name, 0, 0, 100))
        self.conn.commit()

    def update_username(self, id: int, new_username: str):
        self.add_user(id, new_username)
        self.c.execute("UPDATE Users SET username = ? WHERE id = ?", (new_username, id))
        self.conn.commit()

    def get_user(self, id: int) -> tuple[int, str, int, int, int]:
        self.c.execute("SELECT * FROM Users WHERE id = ?", (id,))
        result = self.c.fetchone()
        if result is None:
            self.add_user(id, "Unknown")
            return self.get_user(id)
        return result
    
    def list_users(self) -> list[tuple[int, str, int, int, int]]:
        self.c.execute("SELECT * FROM Users")
        return self.c.fetchall()
    
    def upvote_user(self, id: int, change: int, voter_id: int) -> int:
        user = self.get_user(id)
        self.c.execute("UPDATE Users SET upvotes = ? WHERE id = ?", (user[2] + change, id))
        self.conn.commit()
        self.update_fans(id, change, voter_id)
        return self.get_iq(id)
    
    def downvote_user(self, id: int, change: int, voter_id: int) -> int:
        user = self.get_user(id)
        self.c.execute("UPDATE Users SET downvotes = ? WHERE id = ?", (user[3] + change, id))
        self.conn.commit()
        self.update_haters(id, change, voter_id)
        return self.get_iq(id)
    
    # ========== FANS AND HATERS ==========

    def update_fans(self, id: int, change: int, voter_id: int):
        self.c.execute("SELECT * FROM FansAndHaters WHERE user_id = ? AND fan_or_hater_id = ?", (id, voter_id))
        result = self.c.fetchone()
        if result is None:
            self.c.execute("INSERT INTO FansAndHaters (user_id, fan_or_hater_id, upvotes, downvotes) VALUES (?, ?, ?, ?)", (id, voter_id, change, 0))
        else:
            new_score = result[2] + change
            self.c.execute("UPDATE FansAndHaters SET upvotes = ? WHERE user_id = ? AND fan_or_hater_id = ?", (new_score, id, voter_id))
        self.conn.commit()

    def update_haters(self, id: int, change: int, voter_id: int):
        self.c.execute("SELECT * FROM FansAndHaters WHERE user_id = ? AND fan_or_hater_id = ?", (id, voter_id))
        result = self.c.fetchone()
        if result is None:
            self.c.execute("INSERT INTO FansAndHaters (user_id, fan_or_hater_id, upvotes, downvotes) VALUES (?, ?, ?, ?)", (id, voter_id, 0, change))
        else:
            new_score = result[3] + change
            self.c.execute("UPDATE FansAndHaters SET downvotes = ? WHERE user_id = ? AND fan_or_hater_id = ?", (new_score, id, voter_id))
        self.conn.commit()

    def list_fans(self) -> list[tuple[int, int, int, int]]:
        self.c.execute("SELECT * FROM FansAndHaters")
        return self.c.fetchall()

    # ========== STATISTICS ==========
        
    def leaderboard(self) -> list[tuple[int, str, int]]:
        '''Returns users in order of score as a list of tuples (user_id, username, upvotes-downvotes)'''
        self.c.execute("SELECT id, username, upvotes-downvotes+offset FROM Users ORDER BY upvotes-downvotes+offset DESC")
        return self.c.fetchall()

    def fans(self, id: int, num: int) -> list[tuple[int, str, int]]:
        '''Returns top fans of a user as a list of tuples (user_id, username, upvotes)'''
        self.c.execute("SELECT FansAndHaters.fan_or_hater_id, Users.username, FansAndHaters.upvotes FROM FansAndHaters JOIN Users ON FansAndHaters.fan_or_hater_id = Users.id WHERE FansAndHaters.user_id = ? ORDER BY FansAndHaters.upvotes DESC LIMIT ?", (id, num))
        return self.c.fetchall()
    
    def haters(self, id: int, num: int) -> list[tuple[int, str, int]]:
        '''Returns top haters of a user as a list of tuples (user_id, username, downvotes)'''
        self.c.execute("SELECT FansAndHaters.fan_or_hater_id, Users.username, FansAndHaters.downvotes FROM FansAndHaters JOIN Users ON FansAndHaters.fan_or_hater_id = Users.id WHERE FansAndHaters.user_id = ? ORDER BY FansAndHaters.downvotes DESC LIMIT ?", (id, num))
        return self.c.fetchall()
    
    def get_iq(self, id: int) -> int:
        '''Returns the IQ of a user'''
        self.c.execute("SELECT upvotes-downvotes+offset FROM Users WHERE id = ?", (id,))
        return self.c.fetchone()[0]
    
    def get_iq_in_guild(self, id: int, guild_id: int) -> int:
        '''Returns the IQ of a user just from reacts in a specific guild'''
        self.c.execute("SELECT SUM(Reactions.vote_type) FROM Reactions JOIN Messages ON Reactions.message_id = Messages.id WHERE Messages.author_id = ? AND Messages.guild_id = ?", (id, guild_id))
        return self.c.fetchone()[0]
    
    # ========== EMOJI MANAGEMENT ==========

    def add_guild(self, id: int) -> tuple[str, str]:
        self.c.execute("INSERT OR IGNORE INTO Emojis (guild_id, upvote, downvote) VALUES (?, ?, ?)", (id, "👍", "👎"))
        self.conn.commit()
        return ("👍", "👎")

    def get_emojis(self, id: int) -> tuple[str, str]:
        self.c.execute("SELECT upvote, downvote FROM Emojis WHERE guild_id = ?", (id,))
        return self.c.fetchone() or self.add_guild(id)
    
    def set_upvote(self, id: int, emoji: str):
        self.add_guild(id)
        self.c.execute("UPDATE Emojis SET upvote = ? WHERE guild_id = ?", (emoji, id))
        self.conn.commit()

    def set_downvote(self, id: int, emoji: str):
        self.add_guild(id)
        self.c.execute("UPDATE Emojis SET downvote = ? WHERE guild_id = ?", (emoji, id))
        self.conn.commit()

    def list_emojis(self) -> list[tuple[int, str, str]]:
        self.c.execute("SELECT * FROM Emojis")
        return self.c.fetchall()

    # ========== REACTION MANAGEMENT ==========

    def add_reaction(self, voter_id: int, message: Message, vote_type: int, timestamp: str) -> None:
        '''Adds a reaction to the database if it doesn't exist already.'''
        self.add_message(message)
        self.c.execute("INSERT OR IGNORE INTO Reactions (voter_id, message_id, vote_type, timestamp) VALUES (?, ?, ?, ?)", (voter_id, message.id, vote_type, timestamp))
        self.conn.commit()

    def remove_reaction(self, voter_id: int, message: Message, vote_type: int):
        '''Removes a reaction from the database.'''
        self.c.execute("DELETE FROM Reactions WHERE voter_id = ? AND message_id = ? AND vote_type = ?", (voter_id, message.id, vote_type))
        self.conn.commit()

    def list_reactions(self) -> list[tuple[int, int, int, int, int, int, str]]:
        '''Returns all reactions in the database as a list of tuples (voter_id, message_id, vote_type, channel_id, guild_id, author_id, timestamp)'''
        self.c.execute("SELECT * FROM Reactions")
        return self.c.fetchall()
    
    def best_of(self, id: int, num: int = None) -> list[tuple[int, int, int, int]]:
        '''Returns the top num messages of a user as a list of tuples (message_id, channel_id, guild_id, SUM(vote_type))'''
        if num is None:
            self.c.execute("SELECT Reactions.message_id, Messages.channel_id, Messages.guild_id, SUM(Reactions.vote_type) FROM Reactions JOIN Messages on Reactions.message_id = Messages.id WHERE Messages.author_id = ? GROUP BY Reactions.message_id ORDER BY SUM(Reactions.vote_type) DESC", (id,))
        else:
            self.c.execute("SELECT Reactions.message_id, Messages.channel_id, Messages.guild_id, SUM(Reactions.vote_type) FROM Reactions JOIN Messages on Reactions.message_id = Messages.id WHERE Messages.author_id = ? GROUP BY Reactions.message_id ORDER BY SUM(Reactions.vote_type) DESC LIMIT ?", (id, num))
        
        return self.c.fetchall()
    
    def top_messages(self, guild_id: int = None) -> list[tuple[str, int, int, int, int]]:
        '''Returns the top 5 messages as a list of tuples (author_id, message_id, channel_id, guild_id, SUM(vote_type))'''
        if guild_id is None:
            self.c.execute("SELECT Messages.author_id, Reactions.message_id, Messages.channel_id, Messages.guild_id, SUM(Reactions.vote_type), Messages.content FROM Reactions JOIN Messages ON Reactions.message_id = Messages.id GROUP BY Reactions.message_id ORDER BY SUM(Reactions.vote_type) DESC")
        else:
            self.c.execute("SELECT Messages.author_id, Reactions.message_id, Messages.channel_id, Messages.guild_id, SUM(Reactions.vote_type), Messages.content FROM Reactions JOIN Messages ON Reactions.message_id = Messages.id WHERE guild_id = ? GROUP BY Reactions.message_id ORDER BY SUM(Reactions.vote_type) DESC", (guild_id,))
            
        return self.c.fetchall()
    
    def add_message(self, message: Message) -> None:
        '''Adds a message to the database if it doesn't exist already.'''
        self.c.execute("INSERT OR IGNORE INTO Messages (id, channel_id, guild_id, author_id, content, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (message.id, message.channel.id, message.guild.id, message.author.id, message.clean_content, message.created_at.isoformat()))
        self.conn.commit()

    def list_messages(self) -> list[tuple[int, int, int, int, str, str]]:
        '''Returns all messages in the database as a list of tuples (id, channel_id, guild_id, author_id, content, timestamp)'''
        self.c.execute("SELECT * FROM Messages")
        return self.c.fetchall()
    
    def get_message(self, id: int) -> tuple[int, int, int, int, str, str]:
        '''Returns a message from the database as a tuple (id, channel_id, guild_id, author_id, content, timestamp)'''
        self.c.execute("SELECT * FROM Messages WHERE id = ?", (id,))
        return self.c.fetchone()
    
    def reset_for_scan(self):
        '''Resets the database for a new scan'''
        self.c.execute("DROP TABLE Users")
        self.c.execute("DROP TABLE FansAndHaters")
        self.c.execute("DROP TABLE Reactions")
        self.conn.commit()
        self.create_tables()

    # ========== GAMBLING ==========

    def create_gambling(self):
        '''Creates the Gambling tables'''

        self.c.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            game TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        
        self.conn.commit()

    def add_transaction(self, user_id: int, amount: int, game: str):
        '''Adds a transaction to the database'''

        # Add transaction to database
        self.c.execute("INSERT INTO Transactions (user_id, amount, game, timestamp) VALUES (?, ?, ?, ?)", (user_id, amount, game, datetime.now().isoformat()))

        # Modify user's offset in Users table
        self.c.execute("SELECT offset FROM Users WHERE id = ?", (user_id,))
        offset = self.c.fetchone()[0]
        self.c.execute("UPDATE Users SET offset = ? WHERE id = ?", (offset + amount, user_id))

        self.conn.commit()

    def is_valid_bet(self, user_id: int, amount: int) -> bool:
        '''Checks if the user has enough money (IQ) to place a bet'''
        iq = self.get_iq(user_id)
        return iq >= amount

    def place_bet(self, user_id: int, amount: int, game: str):
        '''Places a bet on a game'''
        self.add_transaction(user_id, -amount, game)

    def win_bet(self, user_id: int, amount: int, game: str):
        '''Wins a bet on a game'''
        self.add_transaction(user_id, amount, game)

    def gambling_stats(self, user_id: int) -> tuple[int, int]:
        '''Returns the total amount won and lost by a user'''
        self.c.execute("SELECT SUM(amount) FROM Transactions WHERE user_id = ? AND amount > 0", (user_id,))
        won = self.c.fetchone()[0] or 0
        self.c.execute("SELECT SUM(amount) FROM Transactions WHERE user_id = ? AND amount < 0", (user_id,))
        lost = self.c.fetchone()[0] or 0
        return (won, -lost)

    # ========== GACHA ==========

    def create_gacha(self):
        '''Creates the Gacha tables'''
        self.c.execute("""
        CREATE TABLE GachaInventory (
            user_id INTEGER NOT NULL,
            card_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            PRIMARY KEY(user_id, card_id),
            FOREIGN KEY(user_id) REFERENCES Users(id)
        )
        """)
        
        self.conn.commit()

    def pull(self) -> tuple[int, str, int, int, int]:
        '''Pulls a character from the gacha (Return random user from Users table)'''
        self.c.execute("SELECT * FROM Users ORDER BY RANDOM() LIMIT 1")
        card = self.c.fetchone()
        return card
    
    def add_card_to_inv(self, user_id: int, card_id: int):
        '''Adds a card to a user's inventory'''
        self.c.execute("SELECT * FROM GachaInventory WHERE user_id = ? AND card_id = ?", (user_id, card_id))
        result = self.c.fetchone()
        if result is None:
            self.c.execute("INSERT INTO GachaInventory (user_id, card_id, quantity) VALUES (?, ?, ?)", (user_id, card_id, 1))
        else:
            self.c.execute("UPDATE GachaInventory SET quantity = ? WHERE user_id = ? AND card_id = ?", (result[2] + 1, user_id, card_id))
        self.conn.commit()
    
    def list_inventory(self, user_id: int) -> list[tuple[int, str, int]]:
        '''Lists all cards in a user's inventory'''
        self.c.execute("SELECT GachaInventory.card_id, Users.username, GachaInventory.quantity FROM GachaInventory JOIN Users ON GachaInventory.card_id = Users.id WHERE user_id = ?", (user_id,))
        return self.c.fetchall()