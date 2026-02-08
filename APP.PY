from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, LoginManager, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import os
from sqlalchemy.sql import func

app = Flask(__name__, template_folder='TEMPLATES', static_folder='STATIC')
app.config['SECRET_KEY'] = 'dev-key-change-later'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'DATABASE.DB')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy(app)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    release_year = db.Column(db.Integer)
    cover_url = db.Column(db.String(255))

    reviews = db.relationship('Review', backref='game', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref='reviews')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_review'),
    )

login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_pjax_request():
    return request.headers.get('X-PJAX') == 'true'


@app.route('/')
def index():
    user = current_user if current_user.is_authenticated else None
    hide_hero_lead = session.pop('hide_hero_lead', False)
    return render_template('INDEX.HTML', user=user, hide_hero_lead=hide_hero_lead)

@app.route('/games', methods=['GET', 'POST'])
@login_required
def games():
    user = current_user

    if request.method == 'POST':
        game_id = request.form.get('game_id', type=int)
        rating = request.form.get('rating', type=int)
        content = (request.form.get('content') or '').strip()

        if not game_id or not rating or rating < 1 or rating > 5:
            flash('Please select a valid rating.', 'error')
            return redirect(url_for('games'))

        existing = Review.query.filter_by(
            user_id=user.id,
            game_id=game_id
        ).first()

        if existing:
            existing.rating = rating
            existing.content = content
            flash('Your review was updated.', 'success')
        else:
            review = Review(
                user_id=user.id,
                game_id=game_id,
                rating=rating,
                content=content
            )
            db.session.add(review)
            flash('Review submitted. Thanks!', 'success')

        db.session.commit()
        return redirect(url_for('games'))

    games = Game.query.all()

    for game in games:
        reviews = Review.query.filter_by(game_id=game.id).all()
        game.review_count = len(reviews)
        game.avg_rating = (
            round(sum(r.rating for r in reviews) / len(reviews), 1)
            if reviews else None
        )

    return render_template(
        "CATALOGUE.HTML",
        user=user,
        games=games,
        popular_games=games[:6],
        new_games=games[6:12]
    )

@app.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)

    if review.user_id != current_user.id:
        flash("You can't delete someone else's review.", "error")
        return redirect(url_for('games'))

    db.session.delete(review)
    db.session.commit()

    flash("Your review was deleted.", "success")
    return redirect(url_for('games'))

@app.route("/games/<int:game_id>")
def game_detail(game_id):
    user = current_user if current_user.is_authenticated else None

    game = Game.query.get_or_404(game_id)

    reviews = (
        Review.query
        .filter_by(game_id=game.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    avg_rating = (
        db.session.query(db.func.avg(Review.rating))
        .filter(Review.game_id == game.id)
        .scalar()
    )

    avg_rating = round(avg_rating, 1) if avg_rating else None

    return render_template(
        "GAME_DETAIL.HTML",
        user=user,
        game=game,
        reviews=reviews,
        avg_rating=avg_rating,
        review_count=len(reviews)
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('REGISTER.HTML')

        password_hash = generate_password_hash(password)

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'error')
            return render_template('REGISTER.HTML')

        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Account created. You are now signed in.', 'success')
        return redirect(url_for('index'))

    return render_template('REGISTER.HTML')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier")
        password = request.form.get("password")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username/email or password", "error")
            return render_template("LOGIN.HTML")

        login_user(user)
        flash("Welcome back!", "success")
        return redirect(url_for("index"))

    return render_template("LOGIN.HTML")

from flask_login import logout_user

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

def seed_games():
    if Game.query.first():
        return

    games = [
        ("Minecraft", "A sandbox game about placing blocks and adventures.", None, "covers/minecraft.jpg"),
        ("Subnautica", "An underwater survival adventure on an alien ocean planet.", 2018, "covers/subnautica.jpg"),
        ("Geometry Dash", "A fast-paced rhythm platformer.", None, "covers/geometry-dash.jpg"),
        ("Elden Ring", "An open-world action RPG.", 2022, "covers/elden-ring.jpg"),
        ("Stardew Valley", "A relaxing farming and life simulation game.", None, "covers/stardew-valley.jpg"),
        ("Hollow Knight", "A beautifully animated metroidvania.", None, "covers/hollow-knight.jpg"),
        ("Celeste", "A challenging platformer.", None, "covers/celeste.jpg"),
        ("Terraria", "A 2D sandbox adventure.", None, "covers/terraria.jpg"),
        ("Dead Cells", "A fast-paced roguelike action platformer.", None, "covers/dead-cells.jpg"),
        ("Undertale", "A story-driven RPG.", None, "covers/undertale.jpg"),
        ("Hades", "A roguelike dungeon crawler.", None, "covers/hades.jpg"),
        ("Cuphead", "A run-and-gun game with hand-drawn animation.", None, "covers/cuphead.jpg"),
        ("Portal 2", "A puzzle game involving portals.", None, "covers/portal-2.jpg"),
        ("DOOM Eternal", "A fast-paced FPS.", None, "covers/doom-eternal.jpg"),
        ("The Witcher 3", "A massive open-world RPG.", None, "covers/the-witcher-3.jpg"),
        ("Skyrim", "An open-world fantasy RPG.", None, "covers/skyrim.jpg"),
        ("Red Dead Redemption 2", "A cinematic western adventure.", None, "covers/red-dead-redemption-2.jpg"),
        ("Dark Souls III", "A challenging action RPG.", None, "covers/dark-souls-3.jpg"),
        ("Sekiro", "A brutal precision-based action game.", None, "covers/sekiro.jpg"),
        ("Slay the Spire", "A roguelike deck builder.", None, "covers/slay-the-spire.jpg"),
        ("Factorio", "A game about building factories.", None, "covers/factorio.jpg"),
    ]

    for title, desc, year, cover in games:
        db.session.add(Game(
            title=title,
            description=desc,
            release_year=year,
            cover_url=cover
        ))

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_games()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)