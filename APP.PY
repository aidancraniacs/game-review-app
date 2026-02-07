from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

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

    conn.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            release_year INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, game_id)
        )
    ''')

    conn.commit()
    conn.close()

def is_pjax_request():
    return request.headers.get('X-PJAX') == 'true'

@app.route('/')
def index():
    user = session.get('user')
    hide_hero_lead = session.pop('hide_hero_lead', False)
    return render_template('INDEX.HTML', user=user, hide_hero_lead=hide_hero_lead)


@app.route('/games')
def games():
    user = session.get('user')

    if not user:
        flash('Please sign in to browse games.', 'info')
        if is_pjax_request():
            return render_template('LOGIN.HTML', user=None)
        return redirect(url_for('login'))

    games = [
        {"id": 1, "title": "Minecraft", "description": "A sandbox game about placing blocks and going on adventures.", "cover_url": url_for("static", filename="covers/minecraft.jpg")},
        {"id": 2, "title": "Geometry Dash", "description": "A fast-paced rhythm platformer with challenging levels.", "cover_url": url_for("static", filename="covers/geometry-dash.jpg")},
        {"id": 3, "title": "Elden Ring", "description": "An open-world action RPG from FromSoftware.", "cover_url": url_for("static", filename="covers/elden-ring.jpg")},
        {"id": 4, "title": "Stardew Valley", "description": "A relaxing farming and life simulation game.", "cover_url": url_for("static", filename="covers/stardew-valley.jpg")},
        {"id": 5, "title": "Hollow Knight", "description": "A beautifully animated metroidvania set in Hallownest.", "cover_url": url_for("static", filename="covers/hollow-knight.jpg")},
        {"id": 6, "title": "Celeste", "description": "A challenging platformer about climbing a mountain.", "cover_url": url_for("static", filename="covers/celeste.jpg")},
        {"id": 7, "title": "Terraria", "description": "A 2D sandbox adventure with crafting and exploration.", "cover_url": url_for("static", filename="covers/terraria.jpg")},
        {"id": 8, "title": "Dead Cells", "description": "A fast-paced roguelike action platformer.", "cover_url": url_for("static", filename="covers/dead-cells.jpg")},
        {"id": 9, "title": "Undertale", "description": "A story-driven RPG where your choices matter.", "cover_url": url_for("static", filename="covers/undertale.jpg")},
        {"id": 10, "title": "Hades", "description": "A roguelike dungeon crawler based on Greek mythology.", "cover_url": url_for("static", filename="covers/hades.jpg")},
        {"id": 11, "title": "Cuphead", "description": "A run-and-gun game with hand-drawn animation.", "cover_url": url_for("static", filename="covers/cuphead.jpg")},
        {"id": 12, "title": "Portal 2", "description": "A puzzle game involving portals and physics.", "cover_url": url_for("static", filename="covers/portal-2.jpg")},
        {"id": 13, "title": "DOOM Eternal", "description": "A fast-paced first-person shooter.", "cover_url": url_for("static", filename="covers/doom-eternal.jpg")},
        {"id": 14, "title": "The Witcher 3", "description": "A massive open-world RPG with deep storytelling.", "cover_url": url_for("static", filename="covers/the-witcher-3.jpg")},
        {"id": 15, "title": "Skyrim", "description": "An open-world fantasy RPG.", "cover_url": url_for("static", filename="covers/skyrim.jpg")},
        {"id": 16, "title": "Red Dead Redemption 2", "description": "A cinematic open-world western adventure.", "cover_url": url_for("static", filename="covers/red-dead-redemption-2.jpg")},
        {"id": 17, "title": "Dark Souls III", "description": "A challenging action RPG.", "cover_url": url_for("static", filename="covers/dark-souls-3.jpg")},
        {"id": 18, "title": "Sekiro", "description": "A brutal action game focused on precision combat.", "cover_url": url_for("static", filename="covers/sekiro.jpg")},
        {"id": 19, "title": "Slay the Spire", "description": "A roguelike deck-building game.", "cover_url": url_for("static", filename="covers/slay-the-spire.jpg")},
        {"id": 20, "title": "Factorio", "description": "A game about building and optimising factories.", "cover_url": url_for("static", filename="covers/factorio.jpg")}
    ]

    return render_template(
        "CATALOGUE.HTML",
        user=user,
        games=games,
        popular_games=games[:6],
        new_games=games[6:12]
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''

            password_hash = generate_password_hash(password)

            conn = get_db_connection()
            conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            conn.close()

            session['user'] = {'username': username}
            flash('Account created. You are now signed in.', 'success')
            return redirect(url_for('index'))

        except sqlite3.IntegrityError:
            flash('Username or email already exists.', 'error')

    return render_template('REGISTER.HTML')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip().lower()
        password = request.form.get('password') or ''

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE lower(username)=? OR email=?',
            (identifier, identifier)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user'] = {'id': user['id'], 'username': user['username']}
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('index'))

        flash('Invalid credentials.', 'error')

    return render_template('LOGIN.HTML')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

init_db()

if __name__ == '__main__':
    app.run(debug=True)