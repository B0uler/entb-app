import bcrypt
from code.db_helpers import get_db_connection

def hash_password(password):
    """Хеширует пароль."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def add_user(username, password, name="", admin=0):
    """Добавляет нового пользователя."""
    with get_db_connection() as conn:
        hashed_password = hash_password(password)
        conn.cursor().execute("INSERT INTO users (username, password, name, admin) VALUES (?, ?, ?, ?)", (username, hashed_password, name, admin))
        conn.commit()

def check_password(username, password):
    """Проверяет пароль пользователя."""
    with get_db_connection() as conn:
        result = conn.cursor().execute("SELECT password, name, admin FROM users WHERE username = ?", (username,)).fetchone()
    if result:
        hashed_password_db, name, admin_status = result
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password_db.encode('utf-8')):
            return True, name, bool(admin_status)
    return False, None, False
