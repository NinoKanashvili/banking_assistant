import sqlite3

def get_balance(user_id):
    conn = sqlite3.connect("banking.db")
    cursor = conn.cursor()

    cursor.execute(
        "select balance from accounts where user_id = ? ",
        (user_id,)
    )

    result = cursor.fetchone()
    conn.close()

    if result is None:
        return "Account not found"
    
    balance = result[0] / 100

    return balance


def get_transactions(user_id):
    conn = sqlite3.connect("banking.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT t.amount, t.transaction_type, t.category, t.transaction_date
        FROM transactions t join accounts a on t.account_id=a.id
        WHERE a.user_id = ?
        ORDER BY t.transaction_date desc
        """,
        (user_id,)
    )

    transactions = cursor.fetchall()
    conn.close()

    result = []

    for transaction in transactions:
        result.append({
            "amount": transaction[0] / 100,
            "type": transaction[1],
            "category": transaction[2],
            "date": transaction[3]
        })

    return result


def calculate_expenses(user_id, category=None):
    conn = sqlite3.connect("banking.db")
    cursor = conn.cursor()

    query = """
        SELECT SUM(t.amount)
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.user_id = ?
        AND t.transaction_type = 'expense'
    """

    params = [user_id]

    if category is not None:
        query +=    " AND LOWER(t.category) = LOWER(?)"
        params.append(category)

    cursor.execute(query, params)

    result = cursor.fetchone()
    conn.close()

    if result[0] is None:
        return 0.0

    return result[0] / 100
