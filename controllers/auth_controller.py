from flask import Blueprint, render_template, request, redirect, session
from models.user_model import UserModel

auth = Blueprint('auth', __name__)

@auth.route('/')
def home():
    return redirect('/login')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            error = "Please enter both username and password."
        else:
            user = UserModel.verify_password(username, password)
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['name'] = user['name']
                session['role'] = user['role']
                if user['role'] == 'admin':
                    return redirect('/admin')
                return redirect('/dashboard')
            else:
                error = "Invalid username or password. Please try again."
    return render_template('login.html', error=error)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect('/dashboard')
    errors = []
    form_data = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        form_data = {'username': username, 'name': name, 'email': email}

        errors = UserModel.validate_registration(username, password, name, email)
        if not errors:
            success, message = UserModel.create(username, password, name, email)
            if success:
                return redirect('/login?registered=1')
            else:
                errors.append(message)
    return render_template('register.html', errors=errors, form_data=form_data)

@auth.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@auth.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')
    current  = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm  = request.form.get('confirm_password', '')

    user = UserModel.verify_password(session['username'], current)
    if not user:
        return redirect('/dashboard?pwd_error=wrong')
    if len(new_pass) < 6:
        return redirect('/dashboard?pwd_error=short')
    if new_pass != confirm:
        return redirect('/dashboard?pwd_error=mismatch')

    UserModel.update_password(session['user_id'], new_pass)
    return redirect('/dashboard?pwd_success=1')
