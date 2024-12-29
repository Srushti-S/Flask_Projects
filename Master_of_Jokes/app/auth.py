# app/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from .models import get_user_by_email_or_nickname, add_user, is_nickname_unique, get_joke_balance, add_user, set_user_role, get_user_role, get_user_by_email
import re
from flask.cli import with_appcontext
import click


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_valid_email(email):
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(email_regex, email)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        nickname = request.form.get('nickname')

        if not is_valid_email(email):
            flash('Invalid email format. Please enter a valid email address.', 'danger')
            return redirect(url_for('auth.register'))

        if not is_nickname_unique(nickname):
            flash('Nickname already taken. Please choose another nickname.', 'danger')
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)
        if add_user(email, nickname, hashed_password):
            user = get_user_by_email(email)
            set_user_role(user['id'], 'User')  
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        else:
            flash('Email already in use. Please choose another email.', 'danger')
            return redirect(url_for('auth.register'))         

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identity = request.form.get('identity')  
        password = request.form.get('password')

        user = get_user_by_email_or_nickname(identity)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['joke_balance'] = get_joke_balance(user['id']) 
            session['role'] = user['role'] 

            flash('You have successfully logged in!', 'success')

            if session['role'] == 'Moderator':
                return redirect(url_for('jokes.manage_roles'))  
            else:
                return redirect(url_for('jokes.leave_joke'))  

        else:
            flash('Invalid email/nickname or password', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))     

@click.command('init-moderator')
@click.argument('email')
@click.argument('password')
@with_appcontext
def init_moderator(email, password):
    """
    CLI command to initialize a moderator.
    Usage: flask init-moderator <email> <password>
    """
    user = get_user_by_email(email)
    if user:
        print(f"User with email {email} already exists. Assigning Moderator role...")
        set_user_role(user['id'], 'Moderator')  
        print(f"User with email {email} updated to Moderator.")
        return

    hashed_password = generate_password_hash(password)
    success = add_user(email, email, hashed_password)
    if success:
        user = get_user_by_email(email)
        set_user_role(user['id'], 'Moderator')
        print(f"Moderator {email} created successfully!")
    else:
        print(f"Failed to create Moderator with email {email}. Email might already exist.")
