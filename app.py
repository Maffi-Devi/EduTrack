from dotenv import load_dotenv
load_dotenv()

from flask import Flask, session, request, redirect, flash, jsonify
from database.db import init_db
from controllers.auth_controller import auth
from controllers.dashboard_controller import dashboard
from controllers.admin_controller import admin
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
if not os.environ.get('SECRET_KEY'):
    print("WARNING: SECRET_KEY is not set - everyone will be logged out whenever the app restarts.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # Set SESSION_COOKIE_SECURE=true on an HTTPS host so the cookie is never sent over plain HTTP
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '').lower() == 'true',
)


# ── CSRF protection ───────────────────────────────────────────────────────────
def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(16)
    return session['_csrf']

app.jinja_env.globals['csrf_token'] = csrf_token

@app.before_request
def check_csrf():
    """Every POST (forms and the chat request) must carry the session's token."""
    if request.method != 'POST':
        return
    sent = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    if not sent or not secrets.compare_digest(sent, session.get('_csrf', '')):
        if request.is_json:
            return jsonify({'reply': 'Your session expired. Please refresh the page and try again.'}), 400
        flash("Your session expired. Please try again.", 'error')
        return redirect(request.referrer or '/login')


@app.get('/health')
def health():
    """Lightweight public endpoint for external uptime checks."""
    return {'status': 'ok'}, 200, {'Cache-Control': 'no-store'}


# Register blueprints (MVC Controllers)
app.register_blueprint(auth)
app.register_blueprint(dashboard)
app.register_blueprint(admin)

# Initialize database on startup
with app.app_context():
    init_db()
    # Create default admin account
    from database.db import get_connection
    from werkzeug.security import generate_password_hash
    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    admin_password = os.environ.get('ADMIN_PASSWORD', '').strip()
    if not existing and admin_password:
        conn.execute(
            "INSERT INTO users (username, password, name, email, role) VALUES (?, ?, ?, ?, ?)",
            ('admin', generate_password_hash(admin_password), 'Administrator', 'admin@edutrack.com', 'admin')
        )
        conn.commit()
        print("Default admin created: username=admin")
    elif not existing:
        print("WARNING: ADMIN_PASSWORD is not set - no admin account exists, so /admin cannot be used.")
    conn.close()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', '').lower() == 'true'
    )
