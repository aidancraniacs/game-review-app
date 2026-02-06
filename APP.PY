from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import traceback

app = Flask(__name__, template_folder='TEMPLATES', static_folder='STATIC')
app.secret_key = os.urandom(24)
DB_PATH = 'DATABASE.DB'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_pjax_request():
    return request.headers.get('X-PJAX') == 'true'

@app.route('/')
def index():
    user = session.get('user')
    hide_hero_lead = session.pop('HIDE HERO LEAD', False)
    return render_template('INDEX.HTML', user=user, hide_hero_lead=hide_hero_lead)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            app.logger.debug("REGISTER POST headers: %s", dict(request.headers))
            app.logger.debug("REGISTER POST form: %s", dict(request.form))

            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''

            if not username or not email or not password:
                flash('Please fill out all fields.', 'error')
                if is_pjax_request():
                    return render_template('REGISTER.HTML', user=session.get('user'))
                return redirect(url_for('register'))

            if '@' not in email or '.' not in email.split('@')[-1]:
                flash('Please enter a valid email address.', 'error')
                if is_pjax_request():
                    return render_template('REGISTER.HTML', user=session.get('user'))
                return redirect(url_for('register'))

            password_hash = generate_password_hash(password)
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, password_hash))
            conn.commit()
            conn.close()

            conn = get_db_connection()
            row = conn.execute('SELECT id, username FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()
            if row:
                session['user'] = {'id': row['id'], 'username': row['username']}

            session['HIDE HERO LEAD'] = True
            flash('Account created. You are now signed in.', 'success')

            if is_pjax_request():
                user_session = session.get('user')
                hide_hero_lead = session.pop('HIDE HERO LEAD', False)
                return render_template('INDEX.HTML', user=user_session, hide_hero_lead=hide_hero_lead)

            return redirect(url_for('index'))

        except sqlite3.IntegrityError as e:
            app.logger.warning('IntegrityError during register: %s', e)
            flash('Username or email already exists.', 'error')
            if is_pjax_request():
                return render_template('REGISTER.HTML', user=session.get('user'))
            return redirect(url_for('register'))

        except Exception:
            app.logger.error('Exception during register:\n%s', traceback.format_exc())
            flash('An unexpected error occurred. Try again.', 'error')
            if is_pjax_request():
                return render_template('REGISTER.HTML', user=session.get('user'))
            return redirect(url_for('register'))

    return render_template('REGISTER.HTML')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            identifier = (request.form.get('identifier') or '').strip().lower()
            password = request.form.get('password') or ''
            if not identifier or not password:
                flash('Please enter username/email and password.', 'error')
                if is_pjax_request():
                    return render_template('LOGIN.HTML', user=session.get('user'))
                return redirect(url_for('login'))

            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE lower(username)=? OR email=?',
                                (identifier, identifier)).fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                session['user'] = {'id': user['id'], 'username': user['username']}
                flash(f"Welcome back, {user['username']}!", 'success')
                if is_pjax_request():
                    user_session = session.get('user')
                    hide_hero_lead = session.pop('HIDE HERO LEAD', False)
                    return render_template('INDEX.HTML', user=user_session, hide_hero_lead=hide_hero_lead)
                return redirect(url_for('index'))

            flash('Invalid credentials.', 'error')
            if is_pjax_request():
                return render_template('LOGIN.HTML', user=session.get('user'))
            return redirect(url_for('login'))

        except Exception:
            app.logger.error('Exception during login:\n%s', traceback.format_exc())
            flash('An unexpected error occurred. Try again.', 'error')
            if is_pjax_request():
                return render_template('LOGIN.HTML', user=session.get('user'))
            return redirect(url_for('login'))

    return render_template('LOGIN.HTML')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    if is_pjax_request():
        return render_template('INDEX.HTML', user=session.get('user'), hide_hero_lead=session.pop('HIDE HERO LEAD', False))
    return redirect(url_for('index'))

init_db()

if __name__ == '__main__':
    app.logger.setLevel('DEBUG')
    app.run(debug=True)