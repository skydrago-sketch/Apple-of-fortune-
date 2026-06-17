
import sqlite3
import time
import json

DATABASE_NAME = 'bot_data.db'

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            melbet_id TEXT,
            state TEXT,
            free_rounds_remaining INTEGER,
            active_package TEXT,
            package_expiry_time INTEGER, -- Unix timestamp
            lang TEXT DEFAULT 'ar',
            is_admin BOOLEAN DEFAULT FALSE,
            last_activity INTEGER -- Unix timestamp
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activation_codes (
            code TEXT PRIMARY KEY,
            package_name TEXT,
            duration_minutes INTEGER,
            is_used BOOLEAN DEFAULT FALSE,
            used_by_user_id INTEGER,
            activation_time INTEGER -- Unix timestamp
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_name TEXT UNIQUE,
            stat_value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        # Convert tuple to dictionary for easier access
        keys = ['user_id', 'melbet_id', 'state', 'free_rounds_remaining', 'active_package', 'package_expiry_time', 'lang', 'is_admin', 'last_activity']
        return dict(zip(keys, user_data))
    return None

def create_or_update_user(user_id, **kwargs):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    user = get_user(user_id)
    if user:
        updates = ', '.join([f'{k} = ?' for k in kwargs])
        values = list(kwargs.values()) + [user_id]
        cursor.execute(f'UPDATE users SET {updates} WHERE user_id = ?', tuple(values))
    else:
        # Default values for new user
        default_data = {
            'user_id': user_id,
            'melbet_id': None,
            'state': 'waiting_for_melbet_id',
            'free_rounds_remaining': 2,
            'active_package': None,
            'package_expiry_time': 0,
            'lang': 'ar',
            'is_admin': False,
            'last_activity': int(time.time())
        }
        default_data.update(kwargs)
        columns = ', '.join(default_data.keys())
        placeholders = ', '.join(['?' for _ in default_data.values()])
        cursor.execute(f'INSERT INTO users ({columns}) VALUES ({placeholders})', tuple(default_data.values()))
    conn.commit()
    conn.close()

def get_activation_code(code):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM activation_codes WHERE code = ?', (code,))
    code_data = cursor.fetchone()
    conn.close()
    if code_data:
        keys = ['code', 'package_name', 'duration_minutes', 'is_used', 'used_by_user_id', 'activation_time']
        return dict(zip(keys, code_data))
    return None

def create_activation_code(code, package_name, duration_minutes):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO activation_codes (code, package_name, duration_minutes) VALUES (?, ?, ?)',
                       (code, package_name, duration_minutes))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Code already exists
    finally:
        conn.close()

def use_activation_code(code, user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE activation_codes SET is_used = TRUE, used_by_user_id = ?, activation_time = ? WHERE code = ?',
                   (user_id, int(time.time()), code))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_all_active_codes():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT code, package_name, duration_minutes, is_used, used_by_user_id, activation_time FROM activation_codes WHERE is_used = FALSE')
    codes = []
    for row in cursor.fetchall():
        keys = ['code', 'package_name', 'duration_minutes', 'is_used', 'used_by_user_id', 'activation_time']
        codes.append(dict(zip(keys, row)))
    conn.close()
    return codes

def get_bot_stat(stat_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT stat_value FROM bot_stats WHERE stat_name = ?', (stat_name,))
    result = cursor.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def set_bot_stat(stat_name, stat_value):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    value_json = json.dumps(stat_value)
    cursor.execute('INSERT OR REPLACE INTO bot_stats (stat_name, stat_value) VALUES (?, ?)', (stat_name, value_json))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print("Database initialized and tables created.")
    # Example usage:
    # create_or_update_user(12345, melbet_id='test12345', state='active')
    # user = get_user(12345)
    # print(user)
    # create_activation_code('TESTCODE1', 'Bronze', 30)
    # code = get_activation_code('TESTCODE1')
    # print(code)
    # use_activation_code('TESTCODE1', 12345)
    # code = get_activation_code('TESTCODE1')
    # print(code)
    # set_bot_stat('total_users', 100)
    # print(get_bot_stat('total_users'))
