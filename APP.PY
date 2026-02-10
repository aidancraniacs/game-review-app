from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import (
    login_user, LoginManager, current_user,
    login_required, logout_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy

#app setup with configuration for secret key and database URI and SQLAlchemy initialisation
app = Flask(__name__, template_folder='TEMPLATES', static_folder='STATIC')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'DATABASE.DB')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

#models for users, games, reviews and review likes
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
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref='reviews')
    likes = db.relationship('ReviewLike', backref='review', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_review'),
    )

class ReviewLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)  #1 for like, -1 for dislike

    __table_args__ = (
        db.UniqueConstraint('review_id', 'user_id', name='unique_review_like'),
    )


#login manager setup for handling user sessions and authentication
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#routes for homepage, game catalogue, game detail, user registration, login/logout, review submission and review reactions
@app.route('/')
def index():
    user = current_user if current_user.is_authenticated else None
    hide_hero_lead = session.pop('hide_hero_lead', False)
    games = Game.query.all()

    return render_template(
        'INDEX.HTML',
        user=user,
        hide_hero_lead=hide_hero_lead,
        games=games
    )


@app.route('/games', methods=['GET', 'POST'])
@login_required
def games():
    user = current_user

    if request.method == 'POST':
        game_id = request.form.get('game_id', type=int)
        rating = request.form.get('rating', type=int)
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()

        if not game_id or not rating or not (1 <= rating <= 5):
            flash('Please select a valid rating.', 'error')
            return redirect(url_for('games'))

        existing = Review.query.filter_by(
            user_id=user.id,
            game_id=game_id
        ).first()

        if existing:
            existing.rating = rating
            existing.title = title
            existing.content = content
            flash('Your review was updated.', 'success')
        else:
            db.session.add(Review(
                user_id=user.id,
                game_id=game_id,
                rating=rating,
                title=title,
                content=content
            ))
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


#like/dislike reviews and return updated counts and user reaction
from flask import jsonify

@app.route('/reviews/<int:review_id>/react', methods=['POST'])
@login_required
def react_review(review_id):
    value = request.form.get('value', type=int)

    if value not in (1, -1):
        return {"error": "invalid reaction"}, 400

    existing = ReviewLike.query.filter_by(
        review_id=review_id,
        user_id=current_user.id
    ).first()

    if existing:
        if existing.value == value:
            #clicking the same reaction again removes it
            db.session.delete(existing)
        else:
            #switching from like to dislike or vice versa
            existing.value = value
    else:
        db.session.add(ReviewLike(
            review_id=review_id,
            user_id=current_user.id,
            value=value
        ))

    db.session.commit()

    likes = ReviewLike.query.filter_by(review_id=review_id, value=1).count()
    dislikes = ReviewLike.query.filter_by(review_id=review_id, value=-1).count()

    existing = ReviewLike.query.filter_by(
        review_id=review_id,
        user_id=current_user.id
    ).first()

    return {
        "likes": likes,
        "dislikes": dislikes,
        "user_reaction": existing.value if existing else 0
    }


#delete review route with permission check to ensure users can only delete own reviews
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


#game detail page showing game info, reviews, avg rating and review count
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
        db.session.query(func.avg(Review.rating))
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


#authentication routes for user registration, login and logout with form validation and feedback messages
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('REGISTER.HTML')

        if User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            flash('Username or email already exists.', 'error')
            return render_template('REGISTER.HTML')

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
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

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


#seed the database with an initial set of games if its empty
def seed_games():
    if Game.query.first():
        return

    games = [
        ("Minecraft", "Minecraft is a sandbox game where you gather resources, craft tools, and build anything you can imagine while exploring a world made of blocks. You can survive against creatures in Survival mode or create freely without limits in Creative mode, with multiplayer and mods adding even more ways to play. ", None, "covers/minecraft.jpg"),
        ("Subnautica", "Subnautica is an underwater survival game where you explore an alien ocean filled with strange creatures, deep caves, and vibrant coral reefs. You gather resources, craft gear, and build bases while managing oxygen and navigating the dangers of the planet’s depths. The focus on exploration, atmosphere, and discovery makes each dive feel tense and rewarding.", 2018, "covers/subnautica.jpg"),
        ("Geometry Dash", "Geometry Dash is a fast-paced rhythm platformer where you guide a geometric icon through obstacle-filled levels synced to energetic music. Precision jumps and quick reflexes are key, and its simple controls make each attempt addictive as you push to master increasingly challenging stages.", None, "covers/geometry-dash.jpg"),
        ("Elden Ring", "Elden Ring is an open‑world action RPG where you explore the vast Lands Between, battle challenging enemies, and shape your own playstyle through weapons, magic, and character builds. Its mix of exploration, tough combat, and atmospheric storytelling creates a demanding but rewarding adventure.", 2022, "covers/elden-ring.jpg"),
        ("Stardew Valley", "Stardew Valley is a cozy farming RPG where you restore a rundown farm, grow crops, raise animals, and explore nearby caves while becoming part of a small rural community. Its mix of farming, crafting, relationships, and gentle exploration creates a relaxing, open‑ended experience.", 2016, "covers/stardew-valley.jpg"),
        ("Hollow Knight", "Hollow Knight is a hand‑drawn Metroidvania where you explore the ruined kingdom of Hallownest, battling corrupted creatures and uncovering its hidden history. Tight combat, atmospheric world‑building, and rewarding exploration make each descent into its depths feel tense and memorable.", 2017, "covers/hollow-knight.jpg"),
        ("Celeste", "Celeste is a precision platformer about climbing Celeste Mountain as Madeline, overcoming tough obstacles and her own inner struggles. Its tight controls, handcrafted levels, and emotional story create a challenging but uplifting experience.", 2018, "covers/celeste.jpg"),
        ("Terraria", "Terraria is a 2D sandbox adventure where you explore a procedurally generated world, gather resources, craft gear, and battle bosses as you shape and build the environment around you. Its mix of exploration, combat, and creative freedom lets you play to your preferences.", None, "covers/terraria.jpg"),
        ("Dead Cells", "Dead Cells is a fast, combat‑focused roguelike where you fight through ever‑changing levels, unlock new weapons and abilities, and learn from each run as you push deeper into a cursed island. Its blend of fluid action, tight controls, and “die‑and‑retry” progression keeps each attempt tense and addictive.", 2018, "covers/dead-cells.jpg"),
        ("Undertale", "Undertale is a quirky RPG where your choices truly matter as you guide a child through a monster‑filled underground world. You can fight or show mercy, and the game reacts in meaningful ways, blending humor, emotion, and memorable characters into a unique story-driven adventure.", 2015, "covers/undertale.jpg"),
        ("Hades", "Hades is a fast, combat‑driven roguelike where you play as Zagreus, battling your way out of the Underworld using a mix of weapons, upgrades, and god‑granted powers. Its quick action, evolving story, and replay‑friendly design make each escape attempt intense and satisfying.", 2020, "covers/hades.jpg"),
        ("Cuphead", "Cuphead is a run‑and‑gun action game inspired by 1930s cartoons, featuring hand‑drawn animation, jazzy music, and challenging boss‑focused gameplay. You play as Cuphead and face a series of tough, stylish battles as you try to repay a deal gone wrong with the Devil.", 2017, "covers/cuphead.jpg"),
        ("Portal 2", "Portal 2 is a first‑person puzzle game where you use a portal gun to solve clever physics‑based challenges inside the labs of Aperture Science. Its sharp writing, memorable characters, and inventive co‑op and single‑player puzzles make it a standout mix of humour and brain‑bending design.", 2011, "covers/portal-2.jpg"),
        ("DOOM Eternal", "DOOM Eternal is a high‑speed first‑person shooter where you become the Slayer, fighting through demon‑infested worlds with aggressive, momentum‑driven combat. Its mix of brutal action, mobility, and over‑the‑top weapons creates an intense, fast‑paced power fantasy.", 2020, "covers/doom-eternal.jpg"),
        ("Skyrim", "Skyrim is an open‑world fantasy RPG where you explore the vast province of Skyrim, battle dragons, develop your character through skills and gear, and shape your own path through quests and factions. Its freedom to roam, role‑play, and discover makes every playthrough feel different.", 2011, "covers/skyrim.jpg"),
        ("Red Dead Redemption 2", "Red Dead Redemption 2 is a cinematic open‑world western where you play as Arthur Morgan, an outlaw navigating the fading days of the Wild West. You take on heists, explore rugged frontier landscapes, and make choices that shape the fate of the Van der Linde gang.", 2018, "covers/red-dead-redemption-2.jpg"),
        ("Dark Souls III", "Dark Souls III is a dark fantasy action RPG where you battle through a decaying world filled with challenging enemies, atmospheric locations, and intense boss fights. Its fast, precise combat and interconnected environments create a demanding but rewarding journey through the series’ final chapter.", 2016, "covers/dark-souls-3.jpg"),
        ("Sekiro: Shadows Die Twice", "Sekiro: Shadows Die Twice is an action‑adventure game set in a brutal, war‑torn vision of late‑1500s Sengoku‑era Japan. You play as Wolf, a shinobi bound to protect a young lord, using stealth, precise swordplay, and a prosthetic arm equipped with versatile tools to overcome deadly enemies and towering bosses. ", 2019, "covers/sekiro.jpg"),
        ("Slay the Spire", "Slay the Spire is a single‑player roguelike deck‑builder where you climb a shifting tower, battle enemies, and build a card deck that evolves with every run. You choose from different characters, each with their own card pools and playstyles, and face procedurally generated paths filled with monsters, events, shops, and powerful relics that shape your strategy. ", 2019, "covers/slay-the-spire.jpg"),
        ("Factorio", "Factorio is a construction and management sim about landing on an alien planet, harvesting resources, and building an ever‑expanding automated factory. You mine ores, research technologies, set up production lines, defend against hostile creatures, and gradually scale your operation from hand‑crafted basics to massive industrial systems.", None, "covers/factorio.jpg"),

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