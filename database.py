import sqlite3
from datetime import datetime, timedelta

DB_NAME = "restaurant.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu_items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL, price REAL DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS expense_items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL, stock_quantity REAL DEFAULT 0, unit TEXT DEFAULT 'unit')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, category TEXT NOT NULL, item_name TEXT, amount REAL NOT NULL, quantity REAL DEFAULT 1, unit TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # New Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, role TEXT NOT NULL)''')
    
    # Pre-register Admin
    cursor.execute('INSERT OR IGNORE INTO users (user_id, role) VALUES (?, ?)', (474393539, 'admin'))
    
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM users WHERE user_id = ? AND role = "admin"', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def is_staff(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def add_user(user_id, role='staff'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, role) VALUES (?, ?)', (user_id, role))
    conn.commit()
    conn.close()

# --- Rest of the functions remain same ---
def add_menu_item(name, category, price):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO menu_items (name, category, price) VALUES (?, ?, ?)', (name, category, price))
    conn.commit()
    conn.close()

def get_menu_items(category):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, price FROM menu_items WHERE category = ?', (category,))
    items = cursor.fetchall()
    conn.close()
    return items

def add_expense_item(name, category, unit='unit'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO expense_items (name, category, unit) VALUES (?, ?, ?)', (name, category, unit))
    conn.commit()
    conn.close()

def get_expense_items(category):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, stock_quantity, unit FROM expense_items WHERE category = ?', (category,))
    items = cursor.fetchall()
    conn.close()
    return items

def record_transaction(t_type, category, item_name, amount, quantity=1, unit=''):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transactions (type, category, item_name, amount, quantity, unit) VALUES (?, ?, ?, ?, ?, ?)', (t_type, category, item_name, amount, quantity, unit))
    if t_type == 'expense':
        cursor.execute('UPDATE expense_items SET stock_quantity = stock_quantity + ? WHERE name = ?', (quantity, item_name))
    conn.commit()
    conn.close()

def get_recent_transactions(limit=15):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, type, category, item_name, amount, quantity, unit, date FROM transactions ORDER BY date DESC LIMIT ?', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

def delete_transaction(t_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT type, item_name, quantity FROM transactions WHERE id = ?', (t_id,))
    res = cursor.fetchone()
    if res:
        t_type, item_name, qty = res
        if t_type == 'expense':
            cursor.execute('UPDATE expense_items SET stock_quantity = stock_quantity - ? WHERE name = ?', (qty, item_name))
        cursor.execute('DELETE FROM transactions WHERE id = ?', (t_id,))
    conn.commit()
    conn.close()

def get_detailed_report(period='rep_daily'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now()
    if period == 'rep_daily': start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'rep_weekly': start_date = now - timedelta(days=7)
    elif period == 'rep_monthly': start_date = now - timedelta(days=30)
    else: start_date = now - timedelta(days=365)
    cursor.execute('''SELECT type, category, item_name, SUM(amount), SUM(quantity), unit, strftime('%Y-%m-%d', date) as day FROM transactions WHERE date >= ? GROUP BY type, category, item_name, unit, day ORDER BY day DESC, category, type''', (start_date,))
    results = cursor.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    init_db()
