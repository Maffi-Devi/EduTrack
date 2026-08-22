from flask import Flask
from database.db import init_db
from controllers.auth_controller import auth
from controllers.dashboard_controller import dashboard
from controllers.admin_controller import admin
import os

app = Flask(__name__)
app.secret_key = "edutrack_mvc_secret_2024"

# Register blueprints (MVC Controllers)
app.register_blueprint(auth)
app.register_blueprint(dashboard)
app.register_blueprint(admin)

# Initialize database on startup
with app.app_context():
    init_db()
    # Create default admin account
    from models.user_model import UserModel
    from database.db import get_connection
    from werkzeug.security import generate_password_hash
    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (username, password, name, email, role) VALUES (?, ?, ?, ?, ?)",
            ('admin', generate_password_hash('admin123'), 'Administrator', 'admin@edutrack.com', 'admin')
        )
        conn.commit()
        print("Default admin created: username=admin, password=admin123")
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)
