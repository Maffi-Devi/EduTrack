from database.db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
import re

class UserModel:

    @staticmethod
    def validate_registration(username, password, name, email):
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append("Username can only contain letters, numbers, underscores.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if not name or len(name.strip()) < 2:
            errors.append("Full name must be at least 2 characters.")
        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append("Please enter a valid email address.")
        return errors

    @staticmethod
    def create(username, password, name, email):
        conn = get_connection()
        try:
            hashed = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                (username.strip(), hashed, name.strip(), email.strip().lower())
            )
            conn.commit()
            return True, "Registration successful!"
        except Exception as e:
            if "UNIQUE" in str(e):
                if "username" in str(e):
                    return False, "Username already taken. Please choose another."
                if "email" in str(e):
                    return False, "Email already registered. Please login."
            return False, "Registration failed. Please try again."
        finally:
            conn.close()

    @staticmethod
    def get_by_username(username):
        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        return user

    @staticmethod
    def get_by_id(user_id):
        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return user

    @staticmethod
    def verify_password(username, password):
        user = UserModel.get_by_username(username)
        if user and check_password_hash(user['password'], password):
            return user
        return None

    @staticmethod
    def update_password(user_id, new_password):
        conn = get_connection()
        try:
            hashed = generate_password_hash(new_password)
            conn.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (hashed, user_id)
            )
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_all_students():
        conn = get_connection()
        users = conn.execute(
            "SELECT id, username, name, email, created_at FROM users WHERE role = 'student'"
        ).fetchall()
        conn.close()
        return users
