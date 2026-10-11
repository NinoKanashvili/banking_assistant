import sqlite3

conn = sqlite3.connect("banking.db")
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    balance INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    category TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    CHECK (amount > 0),
    CHECK (transaction_type IN ('income', 'expense'))
)
""")

cursor.executemany("""
INSERT OR IGNORE INTO users (id, name)
VALUES (?, ?)
""", [
    (1, "Nino"),
    (2, "Giorgi"),
    (3, "Mariam")
])

cursor.executemany("""
INSERT OR IGNORE INTO accounts (id, user_id, balance)
VALUES (?, ?, ?)
""", [
    (1, 1, 150000),
    (2, 2, 85000),
    (3, 3, 230000)
])

cursor.executemany("""
INSERT OR IGNORE INTO transactions
(id, account_id, amount, category, transaction_type, transaction_date)
VALUES (?, ?, ?, ?, ?, ?)
""", [
    (1, 1, 2500, "Food", "expense", "2026-10-01"),
    (2, 1, 5000, "Shopping", "expense", "2026-10-02"),
    (3, 1, 200000, "Salary", "income", "2026-10-03"),
    (4, 2, 3000, "Transport", "expense", "2026-10-04"),
    (5, 2, 12000, "Food", "expense", "2026-10-05"),
    (6, 3, 8000, "Shopping", "expense", "2026-10-06")
])

conn.commit()

conn.close()