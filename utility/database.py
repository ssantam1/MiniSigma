import sqlite3
from datetime import datetime

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
            CREATE TABLE IF NOT EXISTS Reactions (
                voter_id INTEGER,
                author_id INTEGER,
                message_id INTEGER,
                channel_id INTEGER,
                guild_id INTEGER,
                vote_type INTEGER,
                timestamp TEXT,
                PRIMARY KEY (voter_id, message_id, vote_type),
                FOREIGN KEY (voter_id) REFERENCES Users(id),
                FOREIGN KEY (author_id) REFERENCES Users(id),
                FOREIGN KEY (guild_id) REFERENCES Emojis(guild_id)
            )''')
        
        self.conn.commit()

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
        
    def leaderboard(self, num: int) -> list[tuple[int, str, int]]:
        '''Returns top scoring users as a list of tuples (user_id, username, upvotes-downvotes)'''
        self.c.execute("SELECT id, username, upvotes-downvotes FROM Users ORDER BY upvotes-downvotes DESC LIMIT ?", (num,))
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

    def add_reaction(self, voter_id: int, author_id: int, message_id: int, channel_id: int, guild_id: int, vote_type: int, timestamp: str):
        self.c.execute("INSERT OR IGNORE INTO Reactions (voter_id, author_id, message_id, channel_id, guild_id, vote_type, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)", (voter_id, author_id, message_id, channel_id, guild_id, vote_type, timestamp))
        self.conn.commit()

    def remove_reaction(self, voter_id: int, message_id: int, vote_type: int):
        self.c.execute("DELETE FROM Reactions WHERE voter_id = ? AND message_id = ? AND vote_type = ?", (voter_id, message_id, vote_type))
        self.conn.commit()

    def list_reactions(self) -> list[tuple[int, int, int, int, int, int, str]]:
        self.c.execute("SELECT * FROM Reactions")
        return self.c.fetchall()
    
    def user_reactions(self, id: int) -> list[tuple[int, int, int, int, int, str]]:
        self.c.execute("SELECT * FROM Reactions WHERE voter_id = ?", (id,))
        return self.c.fetchall()
    
    def user_messages(self, id: int) -> list[tuple[int, int, int, int, int, str]]:
        self.c.execute("SELECT * FROM Reactions WHERE author_id = ?", (id,))
        return self.c.fetchall()
    
    def best_of(self, id: int, num: int) -> list[tuple[int, int, int, int]]:
        self.c.execute("SELECT message_id, channel_id, guild_id, SUM(vote_type) FROM Reactions WHERE author_id = ? GROUP BY message_id ORDER BY SUM(vote_type) DESC LIMIT ?", (id, num))
        return self.c.fetchall()
    
    def worst_of(self, id: int, num: int) -> list[tuple[int, int, int, int]]:
        self.c.execute("SELECT message_id, channel_id, guild_id, SUM(vote_type) FROM Reactions WHERE author_id = ? GROUP BY message_id ORDER BY SUM(vote_type) ASC LIMIT ?", (id, num))
        return self.c.fetchall()
    