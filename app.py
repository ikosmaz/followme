from datetime import datetime, date, timedelta
from functools import wraps
import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "followme.db"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "static" / "uploads")

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    avatar_color = db.Column(db.String(20), default="#2d7d46", nullable=False)
    avatar_icon = db.Column(db.String(20), default="boot", nullable=False)
    avatar_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    activity_type = db.Column(db.String(30), nullable=False)
    km = db.Column(db.Float, nullable=False)
    workout_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Destination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(120), nullable=False)
    distance_km = db.Column(db.Float, nullable=False)
    fact = db.Column(db.String(300), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    rule_type = db.Column(db.String(20), nullable=False)  # total_km or workouts
    threshold = db.Column(db.Float, nullable=False)


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievement.id"), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="accepted", nullable=False)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)


class ActivityType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    icon_class = db.Column(db.String(80), nullable=False, default="fa-star")


class UserGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)


class GroupPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permission.id"), nullable=False)


class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    target_km = db.Column(db.Float, nullable=False)
    activity_type = db.Column(db.String(30), nullable=True)


class ChallengeMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenge.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_activity_types():
    return ActivityType.query.order_by(ActivityType.name.asc()).all()


def get_activity_icon_map():
    return {a.name: a.icon_class for a in get_activity_types()}


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = db.session.get(User, session["user_id"])
        if not user:
            session.clear()
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


def get_current_user():
    if "user_id" not in session:
        return None
    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return None
    return user


def user_total_km(user_id):
    total = db.session.query(db.func.coalesce(db.func.sum(Workout.km), 0)).filter_by(user_id=user_id).scalar()
    return float(total or 0)


def user_workout_count(user_id):
    count = db.session.query(db.func.count(Workout.id)).filter_by(user_id=user_id).scalar()
    return int(count or 0)


def calculate_level(total_km):
    if total_km <= 10:
        return 1
    elif total_km <= 50:
        return 2
    elif total_km <= 100:
        return 3
    elif total_km <= 500:
        return 4
    elif total_km <= 1000:
        return 5
    elif total_km <= 5000:
        return 6
    else:
        return int(total_km // 5000) + 6


def next_level_target(total_km):
    thresholds = [10, 50, 100, 500, 1000, 5000]
    for threshold in thresholds:
        if total_km < threshold:
            return threshold
    return (int(total_km // 5000) + 1) * 5000


def sum_km_between(user_id, start_date, end_date, activity_type=None):
    query = db.session.query(db.func.coalesce(db.func.sum(Workout.km), 0)).filter(
        Workout.user_id == user_id,
        Workout.workout_date >= start_date,
        Workout.workout_date <= end_date,
    )
    if activity_type:
        query = query.filter(Workout.activity_type == activity_type)
    return float(query.scalar() or 0)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_achievements(user_id):
    total_km = user_total_km(user_id)
    workouts = user_workout_count(user_id)
    achievements = Achievement.query.all()
    earned_ids = {ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()}

    for achievement in achievements:
        if achievement.id in earned_ids:
            continue
        if achievement.rule_type == "total_km" and total_km >= achievement.threshold:
            db.session.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))
        if achievement.rule_type == "workouts" and workouts >= achievement.threshold:
            db.session.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))
    db.session.commit()


def seed_data():
    if Destination.query.count() == 0:
        db.session.add_all(
            [
                Destination(
                    name="Tromsø",
                    country="Norge",
                    distance_km=0,
                    fact="Tromsø kalles Porten til Arktis og har midnattssol om sommeren.",
                    image_url="https://images.unsplash.com/photo-1504730030853-eff311f57d3c?auto=format&fit=crop&w=1200&q=60",
                ),
                Destination(
                    name="Stockholm",
                    country="Sverige",
                    distance_km=1100,
                    fact="Stockholm er bygget på 14 øyer og har over 50 broer.",
                    image_url="https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=60",
                ),
                Destination(
                    name="London",
                    country="Storbritannia",
                    distance_km=2100,
                    fact="London har over 170 museer og 300 teatre.",
                    image_url="https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=60",
                ),
                Destination(
                    name="Marrakesh",
                    country="Marokko",
                    distance_km=4300,
                    fact="Marrakesh er kjent for sine fargerike basarer og Medinaen.",
                    image_url="https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=1200&q=60",
                ),
                Destination(
                    name="Cape Town",
                    country="Sør-Afrika",
                    distance_km=10500,
                    fact="Table Mountain ruver over byen og har en av verdens flotteste utsikter.",
                    image_url="https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=60",
                ),
            ]
        )

    if Achievement.query.count() == 0:
        db.session.add_all(
            [
                Achievement(
                    code="first_km",
                    name="Første kilometer",
                    description="Logg minst 1 km.",
                    rule_type="total_km",
                    threshold=1,
                ),
                Achievement(
                    code="ten_km",
                    name="På vei",
                    description="Nå 10 km totalt.",
                    rule_type="total_km",
                    threshold=10,
                ),
                Achievement(
                    code="fifty_km",
                    name="Eventyrer",
                    description="Nå 50 km totalt.",
                    rule_type="total_km",
                    threshold=50,
                ),
                Achievement(
                    code="workouts_5",
                    name="Fem økter",
                    description="Fullfør 5 treningsøkter.",
                    rule_type="workouts",
                    threshold=5,
                ),
            ]
        )

    if Challenge.query.count() == 0:
        today = date.today()
        weekday = today.weekday()
        if weekday <= 4:
            next_friday = today + timedelta(days=(4 - weekday))
        else:
            next_friday = today + timedelta(days=(7 - weekday + 4))
        next_sunday = next_friday + timedelta(days=2)
        month_start = date(today.year, today.month, 1)
        next_month = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
        month_end = next_month - timedelta(days=1)
        db.session.add_all(
            [
                Challenge(
                    name="Helgeboost",
                    description="Samle 20 km i neste helg (fre–søn).",
                    start_date=next_friday,
                    end_date=next_sunday,
                    target_km=20,
                ),
                Challenge(
                    name="Månedens eventyr",
                    description="Gå på ski 30 km denne måneden.",
                    start_date=month_start,
                    end_date=month_end,
                    target_km=30,
                    activity_type="Ski",
                ),
                Challenge(
                    name="Sprint 10",
                    description="Samle 10 km på 3 dager.",
                    start_date=today,
                    end_date=today + timedelta(days=2),
                    target_km=10,
                ),
            ]
        )

    if ActivityType.query.count() == 0:
        db.session.add_all(
            [
                ActivityType(name="Gå", icon_class="fa-person-walking"),
                ActivityType(name="Jogge", icon_class="fa-person-running"),
                ActivityType(name="Sykle", icon_class="fa-person-biking"),
                ActivityType(name="Ski", icon_class="fa-person-skiing"),
                ActivityType(name="Svømme", icon_class="fa-person-swimming"),
                ActivityType(name="Annet", icon_class="fa-star"),
            ]
        )

    if Group.query.count() == 0:
        db.session.add_all(
            [
                Group(name="Administratorer", description="Full tilgang til admin-funksjoner."),
                Group(name="Trenere", description="Kan følge opp deltakere og se rapporter."),
            ]
        )

    if Permission.query.count() == 0:
        db.session.add_all(
            [
                Permission(code="manage_users", description="Administrere brukere"),
                Permission(code="manage_groups", description="Administrere grupper"),
                Permission(code="view_reports", description="Se rapporter"),
            ]
        )

    db.session.commit()


@app.route("/")
@login_required
def index():
    user = get_current_user()
    total_km = user_total_km(user.id)
    level = calculate_level(total_km)
    next_level_km = next_level_target(total_km)
    km_to_next_level = max(0, next_level_km - total_km)

    destinations = Destination.query.order_by(Destination.distance_km).all()
    current = destinations[0]
    next_dest = None
    for dest in destinations:
        if total_km >= dest.distance_km:
            current = dest
        else:
            next_dest = dest
            break

    unlocked = [d for d in destinations if total_km >= d.distance_km]

    ensure_achievements(user.id)
    achievement_count = UserAchievement.query.filter_by(user_id=user.id).count()

    today = date.today()
    active_challenges = (
        Challenge.query.filter(Challenge.start_date <= today, Challenge.end_date >= today)
        .order_by(Challenge.end_date.asc())
        .all()
    )
    member_ids = {
        cm.challenge_id for cm in ChallengeMember.query.filter_by(user_id=user.id).all()
    }
    challenge_cards = []
    for ch in active_challenges:
        joined = ch.id in member_ids
        progress_km = (
            sum_km_between(user.id, ch.start_date, ch.end_date, ch.activity_type)
            if joined
            else 0.0
        )
        percent = min(100, int((progress_km / ch.target_km) * 100)) if ch.target_km > 0 else 0
        challenge_cards.append(
            {
                "challenge": ch,
                "joined": joined,
                "progress_km": progress_km,
                "percent": percent,
            }
        )

    return render_template(
        "dashboard.html",
        user=user,
        total_km=total_km,
        level=level,
        current=current,
        next_dest=next_dest,
        unlocked=unlocked,
        achievement_count=achievement_count,
        challenges=challenge_cards,
        km_to_next_level=km_to_next_level,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Brukernavn eller e-post finnes allerede.")
            return redirect(url_for("register"))

        user = User(
            username=username,
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        flash("Velkommen til FollowMe!")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Feil brukernavn eller passord.")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/workouts")
@login_required
def workouts():
    user = get_current_user()
    workouts = Workout.query.filter_by(user_id=user.id).order_by(Workout.workout_date.desc()).all()
    activity_types = get_activity_types()
    activity_icons = {a.name: a.icon_class for a in activity_types}
    return render_template(
        "workouts.html",
        user=user,
        workouts=workouts,
        activity_types=activity_types,
        activity_icons=activity_icons,
        today=date.today(),
    )


@app.route("/workouts/<int:workout_id>/edit", methods=["GET", "POST"])
@login_required
def edit_workout(workout_id):
    user = get_current_user()
    workout = db.session.get(Workout, workout_id)
    if not workout or workout.user_id != user.id:
        flash("Fant ikke økten.")
        return redirect(url_for("workouts"))

    if request.method == "POST":
        workout.activity_type = request.form["activity_type"]
        workout.km = float(request.form["km"])
        workout.workout_date = datetime.strptime(request.form["workout_date"], "%Y-%m-%d").date()
        db.session.commit()
        flash("Økten er oppdatert.")
        return redirect(url_for("workouts"))

    activity_types = get_activity_types()
    activity_icons = {a.name: a.icon_class for a in activity_types}
    return render_template(
        "edit_workout.html",
        user=user,
        workout=workout,
        activity_types=activity_types,
        activity_icons=activity_icons,
    )


@app.route("/workouts/<int:workout_id>/delete", methods=["POST"])
@login_required
def delete_workout(workout_id):
    user = get_current_user()
    workout = db.session.get(Workout, workout_id)
    if not workout or workout.user_id != user.id:
        flash("Fant ikke økten.")
        return redirect(url_for("workouts"))
    db.session.delete(workout)
    db.session.commit()
    flash("Økten er slettet.")
    return redirect(url_for("workouts"))


def delete_user_and_data(user_id):
    UserGroup.query.filter_by(user_id=user_id).delete()
    Workout.query.filter_by(user_id=user_id).delete()
    Friend.query.filter_by(user_id=user_id).delete()
    Friend.query.filter_by(friend_id=user_id).delete()
    UserAchievement.query.filter_by(user_id=user_id).delete()
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
    db.session.commit()


@app.route("/workouts/add", methods=["POST"])
@login_required
def add_workout():
    user = get_current_user()
    activity_type = request.form["activity_type"]
    km = float(request.form["km"])
    workout_date = datetime.strptime(request.form["workout_date"], "%Y-%m-%d").date()

    db.session.add(Workout(user_id=user.id, activity_type=activity_type, km=km, workout_date=workout_date))
    db.session.commit()
    ensure_achievements(user.id)
    flash("Økten er lagret.")
    return redirect(url_for("workouts"))


@app.route("/destinations")
@login_required
def destinations():
    user = get_current_user()
    total_km = user_total_km(user.id)
    destinations = Destination.query.order_by(Destination.distance_km).all()
    return render_template("destinations.html", user=user, destinations=destinations, total_km=total_km)


@app.route("/achievements")
@login_required
def achievements():
    user = get_current_user()
    ensure_achievements(user.id)
    earned_ids = {ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user.id).all()}
    achievements = Achievement.query.all()
    return render_template("achievements.html", user=user, achievements=achievements, earned_ids=earned_ids)


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    user = get_current_user()

    if request.method == "POST":
        friend_username = request.form["username"].strip()
        friend = User.query.filter_by(username=friend_username).first()
        if not friend:
            flash("Fant ingen med det brukernavnet.")
            return redirect(url_for("friends"))
        if friend.id == user.id:
            flash("Du kan ikke legge til deg selv.")
            return redirect(url_for("friends"))

        existing = Friend.query.filter_by(user_id=user.id, friend_id=friend.id).first()
        if existing:
            flash("Denne vennen er allerede lagt til.")
        else:
            db.session.add(Friend(user_id=user.id, friend_id=friend.id))
            db.session.commit()
            flash("Venn lagt til!")
        return redirect(url_for("friends"))

    friend_links = Friend.query.filter_by(user_id=user.id).all()
    friend_users = [db.session.get(User, link.friend_id) for link in friend_links]

    leaderboard = []
    for friend_user in friend_users:
        leaderboard.append(
            {
                "username": friend_user.username,
                "total_km": user_total_km(friend_user.id),
            }
        )
    leaderboard = sorted(leaderboard, key=lambda x: x["total_km"], reverse=True)

    return render_template("friends.html", user=user, friends=friend_users, leaderboard=leaderboard)


@app.route("/friends/<int:friend_id>/delete", methods=["POST"])
@login_required
def delete_friend(friend_id):
    user = get_current_user()
    link = Friend.query.filter_by(user_id=user.id, friend_id=friend_id).first()
    if not link:
        flash("Fant ikke venn.")
        return redirect(url_for("friends"))
    db.session.delete(link)
    db.session.commit()
    flash("Venn fjernet.")
    return redirect(url_for("friends"))


@app.route("/reports")
@login_required
def reports():
    user = get_current_user()

    today = date.today()
    year_start = date(today.year, 1, 1)
    month_start = date(today.year, today.month, 1)
    week_start = date.fromordinal(today.toordinal() - today.weekday())

    km_week = sum_km_between(user.id, week_start, today)
    km_month = sum_km_between(user.id, month_start, today)
    km_year = sum_km_between(user.id, year_start, today)

    ensure_achievements(user.id)
    earned = (
        db.session.query(UserAchievement, Achievement)
        .join(Achievement, UserAchievement.achievement_id == Achievement.id)
        .filter(UserAchievement.user_id == user.id)
        .order_by(UserAchievement.earned_at.desc())
        .all()
    )

    friend_links = Friend.query.filter_by(user_id=user.id).all()
    friend_users = [db.session.get(User, link.friend_id) for link in friend_links]
    leaderboard = [{"username": user.username, "total_km": user_total_km(user.id)}]
    for friend_user in friend_users:
        leaderboard.append({"username": friend_user.username, "total_km": user_total_km(friend_user.id)})
    leaderboard = sorted(leaderboard, key=lambda x: x["total_km"], reverse=True)

    return render_template(
        "reports.html",
        user=user,
        km_week=km_week,
        km_month=km_month,
        km_year=km_year,
        earned=earned,
        leaderboard=leaderboard,
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()

    if request.method == "POST":
        user.full_name = request.form["full_name"].strip()
        user.email = request.form["email"].strip()
        user.avatar_color = request.form["avatar_color"].strip() or user.avatar_color
        remove_avatar = request.form.get("remove_avatar") == "1"

        if remove_avatar and user.avatar_image:
            old_path = Path(app.config["UPLOAD_FOLDER"]) / user.avatar_image
            if old_path.exists():
                old_path.unlink()
            user.avatar_image = None
            flash("Fjern bilde!")
        avatar_file = request.files.get("avatar_image")
        if avatar_file and avatar_file.filename:
            if not allowed_file(avatar_file.filename):
                flash("Ugyldig filtype for avatar. Bruk PNG/JPG/GIF/WEBP.")
                return redirect(url_for("profile"))
            filename = secure_filename(avatar_file.filename)
            unique_name = f"{uuid4().hex}_{filename}"
            upload_path = Path(app.config["UPLOAD_FOLDER"]) / unique_name
            avatar_file.save(upload_path)
            if user.avatar_image:
                old_path = Path(app.config["UPLOAD_FOLDER"]) / user.avatar_image
                if old_path.exists():
                    old_path.unlink()
            user.avatar_image = unique_name
        db.session.commit()
        flash("Profil oppdatert.")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


@app.route("/profile/delete", methods=["POST"])
@login_required
def profile_delete():
    user = get_current_user()
    delete_user_and_data(user.id)
    session.clear()
    flash("Kontoen er slettet.")
    return redirect(url_for("login"))


@app.route("/challenges")
@login_required
def challenges():
    user = get_current_user()
    today = date.today()
    challenges = Challenge.query.order_by(Challenge.start_date.desc()).all()
    member_ids = {
        cm.challenge_id for cm in ChallengeMember.query.filter_by(user_id=user.id).all()
    }
    rows = []
    for ch in challenges:
        if today < ch.start_date:
            status = "upcoming"
        elif today > ch.end_date:
            status = "ended"
        else:
            status = "active"
        joined = ch.id in member_ids
        progress_km = (
            sum_km_between(user.id, ch.start_date, ch.end_date, ch.activity_type)
            if joined
            else 0.0
        )
        percent = min(100, int((progress_km / ch.target_km) * 100)) if ch.target_km > 0 else 0
        rows.append(
            {
                "challenge": ch,
                "status": status,
                "joined": joined,
                "progress_km": progress_km,
                "percent": percent,
            }
        )
    return render_template("challenges.html", user=user, challenges=rows)


@app.route("/challenges/<int:challenge_id>/join", methods=["POST"])
@login_required
def join_challenge(challenge_id):
    user = get_current_user()
    challenge = db.session.get(Challenge, challenge_id)
    if not challenge:
        flash("Fant ikke challenge.")
        return redirect(request.form.get("next") or request.referrer or url_for("challenges"))
    existing = ChallengeMember.query.filter_by(challenge_id=challenge_id, user_id=user.id).first()
    if not existing:
        db.session.add(ChallengeMember(challenge_id=challenge_id, user_id=user.id))
        db.session.commit()
        flash("Du er med i challengen!")
    return redirect(request.form.get("next") or request.referrer or url_for("challenges"))


@app.route("/challenges/<int:challenge_id>/leave", methods=["POST"])
@login_required
def leave_challenge(challenge_id):
    user = get_current_user()
    link = ChallengeMember.query.filter_by(challenge_id=challenge_id, user_id=user.id).first()
    if link:
        db.session.delete(link)
        db.session.commit()
        flash("Du har meldt deg av challengen.")
    return redirect(request.form.get("next") or request.referrer or url_for("challenges"))


@app.route("/admin/users")
@login_required
def admin_users():
    user = get_current_user()
    if user.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", user=user, users=users)


@app.route("/admin")
@login_required
def admin_dashboard():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))
    user_count = User.query.count()
    group_count = Group.query.count()
    permission_count = Permission.query.count()
    destination_count = Destination.query.count()
    activity_count = ActivityType.query.count()
    challenge_count = Challenge.query.count()
    achievement_count = Achievement.query.count()
    return render_template(
        "admin_dashboard.html",
        user=admin,
        user_count=user_count,
        group_count=group_count,
        permission_count=permission_count,
        destination_count=destination_count,
        activity_count=activity_count,
        challenge_count=challenge_count,
        achievement_count=achievement_count,
    )


@app.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def admin_user_new():
    user = get_current_user()
    if user.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"].strip()
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Brukernavn eller e-post finnes allerede.")
            return redirect(url_for("admin_user_new"))

        new_user = User(
            username=username,
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Bruker opprettet.")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_new.html", user=user)


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def admin_user_edit(user_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    edit_user = db.session.get(User, user_id)
    if not edit_user:
        flash("Fant ikke bruker.")
        return redirect(url_for("admin_users"))

    groups = Group.query.order_by(Group.name.asc()).all()
    user_group_ids = {
        ug.group_id for ug in UserGroup.query.filter_by(user_id=edit_user.id).all()
    }

    if request.method == "POST":
        edit_user.full_name = request.form["full_name"].strip()
        edit_user.email = request.form["email"].strip().lower()
        edit_user.role = request.form["role"]

        selected_group_ids = {
            int(gid) for gid in request.form.getlist("groups")
        }
        # Update group links
        UserGroup.query.filter_by(user_id=edit_user.id).delete()
        for gid in selected_group_ids:
            db.session.add(UserGroup(user_id=edit_user.id, group_id=gid))

        db.session.commit()
        flash("Bruker oppdatert.")
        return redirect(url_for("admin_users"))

    return render_template(
        "admin_user_edit.html",
        user=admin,
        edit_user=edit_user,
        groups=groups,
        user_group_ids=user_group_ids,
    )


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def admin_user_delete(user_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    delete_user = db.session.get(User, user_id)
    if not delete_user:
        flash("Fant ikke bruker.")
        return redirect(url_for("admin_users"))

    delete_user_and_data(delete_user.id)
    flash("Bruker slettet.")
    return redirect(url_for("admin_users"))


@app.route("/admin/groups", methods=["GET", "POST"])
@login_required
def admin_groups():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form["description"].strip()
        if Group.query.filter_by(name=name).first():
            flash("Gruppen finnes allerede.")
            return redirect(url_for("admin_groups"))
        db.session.add(Group(name=name, description=description))
        db.session.commit()
        flash("Gruppe opprettet.")
        return redirect(url_for("admin_groups"))

    groups = Group.query.order_by(Group.name.asc()).all()
    return render_template("admin_groups.html", user=admin, groups=groups)


@app.route("/admin/groups/<int:group_id>/edit", methods=["GET", "POST"])
@login_required
def admin_group_edit(group_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Fant ikke gruppe.")
        return redirect(url_for("admin_groups"))

    permissions = Permission.query.order_by(Permission.code.asc()).all()
    group_perm_ids = {
        gp.permission_id for gp in GroupPermission.query.filter_by(group_id=group.id).all()
    }

    if request.method == "POST":
        group.name = request.form["name"].strip()
        group.description = request.form["description"].strip()

        selected_perm_ids = {int(pid) for pid in request.form.getlist("permissions")}
        GroupPermission.query.filter_by(group_id=group.id).delete()
        for pid in selected_perm_ids:
            db.session.add(GroupPermission(group_id=group.id, permission_id=pid))

        db.session.commit()
        flash("Gruppe oppdatert.")
        return redirect(url_for("admin_groups"))

    return render_template(
        "admin_group_edit.html",
        user=admin,
        group=group,
        permissions=permissions,
        group_perm_ids=group_perm_ids,
    )


@app.route("/admin/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def admin_group_delete(group_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Fant ikke gruppe.")
        return redirect(url_for("admin_groups"))

    UserGroup.query.filter_by(group_id=group.id).delete()
    GroupPermission.query.filter_by(group_id=group.id).delete()
    db.session.delete(group)
    db.session.commit()
    flash("Gruppe slettet.")
    return redirect(url_for("admin_groups"))


@app.route("/admin/permissions", methods=["GET", "POST"])
@login_required
def admin_permissions():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        code = request.form["code"].strip()
        description = request.form["description"].strip()
        if Permission.query.filter_by(code=code).first():
            flash("Rettighet finnes allerede.")
            return redirect(url_for("admin_permissions"))
        db.session.add(Permission(code=code, description=description))
        db.session.commit()
        flash("Rettighet opprettet.")
        return redirect(url_for("admin_permissions"))

    permissions = Permission.query.order_by(Permission.code.asc()).all()
    return render_template("admin_permissions.html", user=admin, permissions=permissions)


@app.route("/admin/permissions/<int:permission_id>/edit", methods=["GET", "POST"])
@login_required
def admin_permission_edit(permission_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    permission = db.session.get(Permission, permission_id)
    if not permission:
        flash("Fant ikke rettighet.")
        return redirect(url_for("admin_permissions"))

    if request.method == "POST":
        permission.code = request.form["code"].strip()
        permission.description = request.form["description"].strip()
        db.session.commit()
        flash("Rettighet oppdatert.")
        return redirect(url_for("admin_permissions"))

    return render_template("admin_permission_edit.html", user=admin, permission=permission)


@app.route("/admin/permissions/<int:permission_id>/delete", methods=["POST"])
@login_required
def admin_permission_delete(permission_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    permission = db.session.get(Permission, permission_id)
    if not permission:
        flash("Fant ikke rettighet.")
        return redirect(url_for("admin_permissions"))

    GroupPermission.query.filter_by(permission_id=permission.id).delete()
    db.session.delete(permission)
    db.session.commit()
    flash("Rettighet slettet.")
    return redirect(url_for("admin_permissions"))


@app.route("/admin/destinations", methods=["GET", "POST"])
@login_required
def admin_destinations():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        country = request.form["country"].strip()
        distance_km = float(request.form["distance_km"])
        fact = request.form["fact"].strip()
        image_url = request.form["image_url"].strip()
        db.session.add(
            Destination(
                name=name,
                country=country,
                distance_km=distance_km,
                fact=fact,
                image_url=image_url,
            )
        )
        db.session.commit()
        flash("Destinasjon opprettet.")
        return redirect(url_for("admin_destinations"))

    destinations = Destination.query.order_by(Destination.distance_km.asc()).all()
    return render_template("admin_destinations.html", user=admin, destinations=destinations)


@app.route("/admin/destinations/<int:dest_id>/edit", methods=["GET", "POST"])
@login_required
def admin_destination_edit(dest_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    destination = db.session.get(Destination, dest_id)
    if not destination:
        flash("Fant ikke destinasjon.")
        return redirect(url_for("admin_destinations"))

    if request.method == "POST":
        destination.name = request.form["name"].strip()
        destination.country = request.form["country"].strip()
        destination.distance_km = float(request.form["distance_km"])
        destination.fact = request.form["fact"].strip()
        destination.image_url = request.form["image_url"].strip()
        db.session.commit()
        flash("Destinasjon oppdatert.")
        return redirect(url_for("admin_destinations"))

    return render_template("admin_destination_edit.html", user=admin, destination=destination)


@app.route("/admin/destinations/<int:dest_id>/delete", methods=["POST"])
@login_required
def admin_destination_delete(dest_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    destination = db.session.get(Destination, dest_id)
    if not destination:
        flash("Fant ikke destinasjon.")
        return redirect(url_for("admin_destinations"))

    db.session.delete(destination)
    db.session.commit()
    flash("Destinasjon slettet.")
    return redirect(url_for("admin_destinations"))


@app.route("/admin/activity-types", methods=["GET", "POST"])
@login_required
def admin_activity_types():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        icon_class = request.form["icon_class"].strip() or "fa-star"
        if ActivityType.query.filter_by(name=name).first():
            flash("Treningstype finnes allerede.")
            return redirect(url_for("admin_activity_types"))
        db.session.add(ActivityType(name=name, icon_class=icon_class))
        db.session.commit()
        flash("Treningstype opprettet.")
        return redirect(url_for("admin_activity_types"))

    activity_types = ActivityType.query.order_by(ActivityType.name.asc()).all()
    return render_template(
        "admin_activity_types.html", user=admin, activity_types=activity_types
    )


@app.route("/admin/activity-types/<int:activity_id>/edit", methods=["GET", "POST"])
@login_required
def admin_activity_type_edit(activity_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    activity = db.session.get(ActivityType, activity_id)
    if not activity:
        flash("Fant ikke treningstype.")
        return redirect(url_for("admin_activity_types"))

    if request.method == "POST":
        activity.name = request.form["name"].strip()
        activity.icon_class = request.form["icon_class"].strip() or "fa-star"
        db.session.commit()
        flash("Treningstype oppdatert.")
        return redirect(url_for("admin_activity_types"))

    return render_template(
        "admin_activity_type_edit.html", user=admin, activity=activity
    )


@app.route("/admin/activity-types/<int:activity_id>/delete", methods=["POST"])
@login_required
def admin_activity_type_delete(activity_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    activity = db.session.get(ActivityType, activity_id)
    if not activity:
        flash("Fant ikke treningstype.")
        return redirect(url_for("admin_activity_types"))

    db.session.delete(activity)
    db.session.commit()
    flash("Treningstype slettet.")
    return redirect(url_for("admin_activity_types"))


@app.route("/admin/challenges", methods=["GET", "POST"])
@login_required
def admin_challenges():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    activity_types = ActivityType.query.order_by(ActivityType.name.asc()).all()
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form["description"].strip()
        start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
        target_km = float(request.form["target_km"])
        activity_type = request.form.get("activity_type") or None

        db.session.add(
            Challenge(
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                target_km=target_km,
                activity_type=activity_type,
            )
        )
        db.session.commit()
        flash("Challenge opprettet.")
        return redirect(url_for("admin_challenges"))

    challenges = Challenge.query.order_by(Challenge.start_date.desc()).all()
    return render_template(
        "admin_challenges.html",
        user=admin,
        challenges=challenges,
        activity_types=activity_types,
    )


@app.route("/admin/challenges/<int:challenge_id>/edit", methods=["GET", "POST"])
@login_required
def admin_challenge_edit(challenge_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    challenge = db.session.get(Challenge, challenge_id)
    if not challenge:
        flash("Fant ikke challenge.")
        return redirect(url_for("admin_challenges"))

    activity_types = ActivityType.query.order_by(ActivityType.name.asc()).all()
    if request.method == "POST":
        challenge.name = request.form["name"].strip()
        challenge.description = request.form["description"].strip()
        challenge.start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        challenge.end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
        challenge.target_km = float(request.form["target_km"])
        challenge.activity_type = request.form.get("activity_type") or None
        db.session.commit()
        flash("Challenge oppdatert.")
        return redirect(url_for("admin_challenges"))

    return render_template(
        "admin_challenge_edit.html",
        user=admin,
        challenge=challenge,
        activity_types=activity_types,
    )


@app.route("/admin/challenges/<int:challenge_id>/delete", methods=["POST"])
@login_required
def admin_challenge_delete(challenge_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    challenge = db.session.get(Challenge, challenge_id)
    if not challenge:
        flash("Fant ikke challenge.")
        return redirect(url_for("admin_challenges"))

    ChallengeMember.query.filter_by(challenge_id=challenge.id).delete()
    db.session.delete(challenge)
    db.session.commit()
    flash("Challenge slettet.")
    return redirect(url_for("admin_challenges"))


@app.route("/admin/achievements", methods=["GET", "POST"])
@login_required
def admin_achievements():
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        code = request.form["code"].strip()
        name = request.form["name"].strip()
        description = request.form["description"].strip()
        rule_type = request.form["rule_type"].strip()
        threshold = float(request.form["threshold"])

        if Achievement.query.filter_by(code=code).first():
            flash("Achievement-kode finnes allerede.")
            return redirect(url_for("admin_achievements"))

        db.session.add(
            Achievement(
                code=code,
                name=name,
                description=description,
                rule_type=rule_type,
                threshold=threshold,
            )
        )
        db.session.commit()
        flash("Achievement opprettet.")
        return redirect(url_for("admin_achievements"))

    achievements = Achievement.query.order_by(Achievement.id.desc()).all()
    return render_template(
        "admin_achievements.html", user=admin, achievements=achievements
    )


@app.route("/admin/achievements/<int:achievement_id>/edit", methods=["GET", "POST"])
@login_required
def admin_achievement_edit(achievement_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    achievement = db.session.get(Achievement, achievement_id)
    if not achievement:
        flash("Fant ikke achievement.")
        return redirect(url_for("admin_achievements"))

    if request.method == "POST":
        achievement.code = request.form["code"].strip()
        achievement.name = request.form["name"].strip()
        achievement.description = request.form["description"].strip()
        achievement.rule_type = request.form["rule_type"].strip()
        achievement.threshold = float(request.form["threshold"])
        db.session.commit()
        flash("Achievement oppdatert.")
        return redirect(url_for("admin_achievements"))

    return render_template(
        "admin_achievement_edit.html", user=admin, achievement=achievement
    )


@app.route("/admin/achievements/<int:achievement_id>/delete", methods=["POST"])
@login_required
def admin_achievement_delete(achievement_id):
    admin = get_current_user()
    if admin.role != "admin":
        flash("Du har ikke tilgang.")
        return redirect(url_for("index"))

    achievement = db.session.get(Achievement, achievement_id)
    if not achievement:
        flash("Fant ikke achievement.")
        return redirect(url_for("admin_achievements"))

    UserAchievement.query.filter_by(achievement_id=achievement.id).delete()
    db.session.delete(achievement)
    db.session.commit()
    flash("Achievement slettet.")
    return redirect(url_for("admin_achievements"))


def init_db():
    db.create_all()
    seed_data()
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
