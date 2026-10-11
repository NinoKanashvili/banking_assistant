
import sqlite3
import pytest

from banking_tools import (
    get_balance,
    get_transactions,
    calculate_expenses
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test_banking.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            balance INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER,
            amount INTEGER,
            transaction_type TEXT,
            category TEXT,
            transaction_date TEXT
        )
    """)

    cursor.execute(
        "INSERT INTO accounts VALUES (1, 1, 150000)"
    )

    cursor.executemany(
        "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 200000, "income", "Salary", "2026-10-01"),
            (2, 1, 5000, "expense", "Shopping", "2026-10-02"),
            (3, 1, 2500, "expense", "Food", "2026-10-03")
        ]
    )

    conn.commit()
    conn.close()

    original_connect = sqlite3.connect

    def test_connect(database, *args, **kwargs):
        if str(database) == "banking.db":
            database = db_path

        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", test_connect)

    return db_path


def test_get_balance(test_database):
    assert get_balance(1) == 1500.0


def test_get_balance_unknown_user(test_database):
    assert get_balance(999) == "Account not found"


def test_get_transactions(test_database):
    transactions = get_transactions(1)

    assert len(transactions) == 3
    assert transactions[0]["amount"] == 25.0
    assert transactions[0]["category"] == "Food"
    assert transactions[1]["amount"] == 50.0
    assert transactions[2]["amount"] == 2000.0


def test_get_transactions_unknown_user(test_database):
    assert get_transactions(999) == []


def test_calculate_all_expenses(test_database):
    assert calculate_expenses(1) == 75.0


def test_calculate_food_expenses(test_database):
    assert calculate_expenses(1, "Food") == 25.0


def test_calculate_category_case_insensitive(test_database):
    assert calculate_expenses(1, "food") == 25.0


def test_calculate_unknown_category(test_database):
    assert calculate_expenses(1, "Travel") == 0.0


def test_calculate_unknown_user(test_database):
    assert calculate_expenses(999) == 0.0
