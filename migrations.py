from utility import database as DB

# reset everyones Users.offset to 100
def reset_users_offset():
    db = DB.Database()
    db.c.execute("UPDATE Users SET offset = 100")
    db.conn.commit()

# Erase every entry in Transactions table
def clear_transactions():
    db = DB.Database()
    db.c.execute("DELETE FROM Transactions")
    db.conn.commit()

# Reset all consequences of gambling
def reset_gambling():
    reset_users_offset()
    clear_transactions()