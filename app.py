"""Knjižnica — majhna knjižnica z rezervacijami (Flask + SQLite)."""
import os
import secrets
import sqlite3
from functools import wraps
from hashlib import sha1

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("KNJIZNICA_DB", os.path.join(BASE_DIR, "knjiznica.db"))
ADMIN_CODE = os.environ.get("KNJIZNICA_ADMIN_CODE", "KNJIZNICA-ADMIN")

app = Flask(__name__)
app.secret_key = os.environ.get("KNJIZNICA_SECRET", "dev-" + sha1(BASE_DIR.encode()).hexdigest())

# --------------------------------------------------------------------------- #
# Baza
# --------------------------------------------------------------------------- #
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    year INTEGER,
    cover_url TEXT NOT NULL DEFAULT '',
    total_copies INTEGER NOT NULL CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL CHECK (available_copies >= 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    cancelled_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_res_user ON reservations(user_id, status);
CREATE INDEX IF NOT EXISTS idx_res_book ON reservations(book_id, status);
"""

SEED_BOOKS = [
    ("Alamut", "Vladimir Bartol", "Roman", 1938, 4,
     "Zgodba o trdnjavi Alamut in Hasanu ibn Sabi, ki z mitom o raju ustvari vojsko brezpogojno vdanih fedajinov. Roman o moči ideje, manipulaciji in ceni absolutne vere."),
    ("Na klancu", "Ivan Cankar", "Roman", 1902, 3,
     "Francka teče za vozom celo življenje. Pretresljiva podoba revščine, upanja in materinske žrtve na slovenskem podeželju na prelomu stoletja."),
    ("Čefurji raus!", "Goran Vojnović", "Roman", 2008, 2,
     "Marko Đorđić odrašča v Fužinah med dvema identitetama. Duhovit, glasen in boleče iskren roman o pripadnosti in predsodkih."),
    ("Sapiens", "Yuval Noah Harari", "Zgodovina", 2011, 3,
     "Kratka zgodovina človeštva — od kognitivne revolucije do dobe znanosti. Kako je ena vrsta z zgodbami in miti zavladala planetu."),
    ("Clean Code", "Robert C. Martin", "Računalništvo", 2008, 5,
     "Priročnik obrti programiranja: imena, funkcije, komentarji, testi. Kako pisati kodo, ki jo bo naslednji razvijalec z veseljem bral."),
    ("Design Patterns", "Gamma, Helm, Johnson, Vlissides", "Računalništvo", 1994, 2,
     "Klasični katalog 23 načrtovalskih vzorcev objektno usmerjenega programiranja, ki je oblikoval jezik, s katerim razvijalci govorijo o arhitekturi."),
    ("Introduction to Algorithms", "Cormen, Leiserson, Rivest, Stein", "Računalništvo", 1990, 4,
     "Obsežen pregled algoritmov in podatkovnih struktur — od urejanja do grafov in dinamičnega programiranja. Biblija vsakega študenta računalništva."),
    ("Kratka zgodovina časa", "Stephen Hawking", "Znanost", 1988, 2,
     "Od velikega poka do črnih lukenj: kozmologija razložena brez enačb, za vsakega radovednega bralca."),
    ("Sebični gen", "Richard Dawkins", "Znanost", 1976, 1,
     "Evolucija skozi oči gena. Knjiga, ki je spremenila razumevanje naravne selekcije in prvič predstavila pojem mema."),
    ("1984", "George Orwell", "Roman", 1949, 3,
     "Veliki brat te opazuje. Distopija o nadzoru, jeziku in resnici, ki je danes aktualnejša kot kdajkoli."),
    ("Mali princ", "Antoine de Saint-Exupéry", "Mladinska", 1943, 4,
     "Pripoved o dečku z majhnega planeta, vrtnici in lisici. Bistveno je očem nevidno."),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "Psihologija", 2011, 2,
     "Dva sistema mišljenja — hitri, intuitivni in počasni, premišljeni. Kako napake v presoji oblikujejo naše odločitve."),
    ("Pesmi", "France Prešeren", "Poezija", 1847, 3,
     "Poezije največjega slovenskega pesnika, od Sonetnega venca do Zdravljice in Krsta pri Savici."),
    ("Kitajska dekleta", "Drago Jančar", "Kratka proza", 2020, 1,
     "Zbirka kratke proze o ljudeh na robu, spominu in zgodovini, ki se tiho vtisne v vsakdanja življenja."),
    ("The Pragmatic Programmer", "Andrew Hunt, David Thomas", "Računalništvo", 1999, 3,
     "Nasveti za razvijalca, ki želi postati mojster: od DRY in ortogonalnosti do tega, kako ne pustiti razbitih oken v kodi."),
    ("Gospodar prstanov", "J. R. R. Tolkien", "Fantazija", 1954, 2,
     "Frodo, Prstan in dolga pot v Mordor. Epska fantazija, ki je zaznamovala žanr za vedno."),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Administrator", "admin@knjiznica.si", generate_password_hash("admin123"), "admin"))
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Ana Študentka", "ana@student.si", generate_password_hash("student123"), "student"))
    if db.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO books (title, author, category, year, total_copies, available_copies, description)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(t, a, c, y, n, n, d) for t, a, c, y, n, d in SEED_BOOKS])
    db.commit()
    db.close()


# --------------------------------------------------------------------------- #
# Avtentikacija, CSRF, pomožne funkcije
# --------------------------------------------------------------------------- #
def current_user():
    if "user" not in g:
        uid = session.get("uid")
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Za to dejanje se moraš prijaviti.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def deco(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user()["role"] != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return deco


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        token = request.form.get("csrf")
        if not token or token != session.get("csrf"):
            abort(400, "Neveljaven CSRF žeton.")


COVER_PALETTE = [
    ("#E8452C", "#141210"), ("#1F4D3A", "#F3EEE3"), ("#2B3FD6", "#F3EEE3"),
    ("#F2C230", "#141210"), ("#141210", "#F2C230"), ("#C9B8F0", "#141210"),
    ("#8A2C1E", "#F3EEE3"), ("#9FD4C4", "#141210"), ("#F08FB0", "#141210"),
]


def cover_style(book):
    h = int(sha1(f"{book['title']}{book['author']}".encode()).hexdigest(), 16)
    bg, fg = COVER_PALETTE[h % len(COVER_PALETTE)]
    return {"bg": bg, "fg": fg, "pattern": (h >> 8) % 5}


@app.context_processor
def inject_globals():
    return {"me": current_user(), "csrf_token": csrf_token}


app.jinja_env.globals["cover_style"] = cover_style


def categories():
    return [r[0] for r in get_db().execute("SELECT DISTINCT category FROM books ORDER BY category")]


def safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


# --------------------------------------------------------------------------- #
# Javne strani
# --------------------------------------------------------------------------- #
@app.route("/")
def catalog():
    db = get_db()
    q = request.args.get("q", "").strip()
    field = request.args.get("field", "all")
    category = request.args.get("category", "")
    only_available = request.args.get("available") == "1"
    sort = request.args.get("sort", "title")

    where, params = [], []
    if q:
        like = f"%{q}%"
        if field == "title":
            where.append("title LIKE ?"); params.append(like)
        elif field == "author":
            where.append("author LIKE ?"); params.append(like)
        elif field == "category":
            where.append("category LIKE ?"); params.append(like)
        else:
            where.append("(title LIKE ? OR author LIKE ? OR category LIKE ?)"); params += [like] * 3
    if category:
        where.append("category = ?"); params.append(category)
    if only_available:
        where.append("available_copies > 0")
    order = {"title": "title COLLATE NOCASE", "author": "author COLLATE NOCASE",
             "new": "id DESC", "available": "available_copies DESC, title"}.get(sort, "title")

    sql = "SELECT * FROM books"
    if where:
        sql += " WHERE " + " AND ".join(where)
    books = db.execute(sql + " ORDER BY " + order, params).fetchall()

    stats = db.execute(
        "SELECT COUNT(*) AS titles, COALESCE(SUM(total_copies),0) AS copies,"
        " COALESCE(SUM(available_copies),0) AS available FROM books").fetchone()
    my_ids = set()
    if current_user() and current_user()["role"] == "student":
        my_ids = {r[0] for r in db.execute(
            "SELECT book_id FROM reservations WHERE user_id = ? AND status = 'active'",
            (current_user()["id"],))}
    return render_template("catalog.html", books=books, categories=categories(), stats=stats,
                           q=q, field=field, category=category, only_available=only_available,
                           sort=sort, my_ids=my_ids)


@app.route("/knjiga/<int:book_id>")
def book_detail(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        abort(404)
    my_res = None
    if current_user() and current_user()["role"] == "student":
        my_res = db.execute(
            "SELECT * FROM reservations WHERE user_id = ? AND book_id = ? AND status = 'active'",
            (current_user()["id"], book_id)).fetchone()
    related = db.execute(
        "SELECT * FROM books WHERE category = ? AND id != ? ORDER BY RANDOM() LIMIT 4",
        (book["category"], book_id)).fetchall()
    return render_template("book.html", book=book, my_res=my_res, related=related)


# --------------------------------------------------------------------------- #
# Registracija / prijava
# --------------------------------------------------------------------------- #
@app.route("/registracija", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("catalog"))
    form = {}
    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        email = form.get("email", "").strip().lower()
        password = form.get("password", "")
        role = form.get("role", "student")
        errors = []
        if len(name) < 2:
            errors.append("Vnesi ime in priimek.")
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Vnesi veljaven e-poštni naslov.")
        if len(password) < 6:
            errors.append("Geslo mora imeti vsaj 6 znakov.")
        if password != form.get("password2", ""):
            errors.append("Gesli se ne ujemata.")
        if role not in ("student", "admin"):
            errors.append("Neveljavna vloga.")
        if role == "admin" and form.get("admin_code", "") != ADMIN_CODE:
            errors.append("Napačna administratorska koda.")
        if not errors:
            try:
                db = get_db()
                cur = db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (name, email, generate_password_hash(password), role))
                db.commit()
            except sqlite3.IntegrityError:
                errors.append("Uporabnik s tem e-naslovom že obstaja.")
            else:
                session.clear()
                session["uid"] = cur.lastrowid
                flash(f"Dobrodošel/-a, {name.split()[0]}! Račun je ustvarjen.", "ok")
                return redirect(url_for("admin_dashboard" if role == "admin" else "catalog"))
        for e in errors:
            flash(e, "error")
    return render_template("register.html", form=form)


@app.route("/prijava", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("catalog"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["uid"] = user["id"]
            flash(f"Pozdravljen/-a, {user['name'].split()[0]}.", "ok")
            default = url_for("admin_dashboard") if user["role"] == "admin" else url_for("catalog")
            return redirect(safe_next(request.args.get("next")) or default)
        flash("Napačen e-naslov ali geslo.", "error")
    return render_template("login.html", email=email)


@app.route("/odjava", methods=["POST"])
def logout():
    session.clear()
    flash("Odjavljen/-a si. Se vidimo!", "info")
    return redirect(url_for("catalog"))


# --------------------------------------------------------------------------- #
# Rezervacije (študent)
# --------------------------------------------------------------------------- #
@app.route("/knjiga/<int:book_id>/rezerviraj", methods=["POST"])
@role_required("student")
def reserve(book_id):
    db = get_db()
    uid = current_user()["id"]
    existing = db.execute(
        "SELECT 1 FROM reservations WHERE user_id = ? AND book_id = ? AND status = 'active'",
        (uid, book_id)).fetchone()
    if existing:
        flash("To knjigo si že rezerviral/-a.", "info")
    else:
        # atomarno zmanjšanje — uspe le, če je izvod na voljo
        cur = db.execute(
            "UPDATE books SET available_copies = available_copies - 1"
            " WHERE id = ? AND available_copies > 0", (book_id,))
        if cur.rowcount == 1:
            db.execute("INSERT INTO reservations (user_id, book_id) VALUES (?, ?)", (uid, book_id))
            db.commit()
            flash("Rezervirano! Knjigo te čaka na izposojnem pultu.", "ok")
        else:
            db.rollback()
            flash("Žal ni več prostih izvodov.", "error")
    return redirect(safe_next(request.form.get("next")) or url_for("book_detail", book_id=book_id))


def _cancel(res_id, owner_id=None):
    db = get_db()
    sql = "SELECT * FROM reservations WHERE id = ? AND status = 'active'"
    params = [res_id]
    if owner_id is not None:
        sql += " AND user_id = ?"; params.append(owner_id)
    res = db.execute(sql, params).fetchone()
    if res is None:
        return False
    db.execute("UPDATE reservations SET status = 'cancelled', cancelled_at = datetime('now','localtime')"
               " WHERE id = ?", (res_id,))
    db.execute("UPDATE books SET available_copies = MIN(total_copies, available_copies + 1) WHERE id = ?",
               (res["book_id"],))
    db.commit()
    return True


@app.route("/rezervacija/<int:res_id>/preklici", methods=["POST"])
@role_required("student")
def cancel_reservation(res_id):
    if _cancel(res_id, current_user()["id"]):
        flash("Rezervacija preklicana. Izvod je spet na voljo.", "ok")
    else:
        flash("Rezervacije ni mogoče preklicati.", "error")
    return redirect(safe_next(request.form.get("next")) or url_for("my_reservations"))


@app.route("/moje-rezervacije")
@role_required("student")
def my_reservations():
    rows = get_db().execute(
        "SELECT r.*, b.title, b.author, b.category, b.cover_url, b.available_copies, b.total_copies"
        " FROM reservations r JOIN books b ON b.id = r.book_id"
        " WHERE r.user_id = ? ORDER BY r.status = 'active' DESC, r.created_at DESC, r.id DESC",
        (current_user()["id"],)).fetchall()
    active = [r for r in rows if r["status"] == "active"]
    history = [r for r in rows if r["status"] != "active"]
    return render_template("my_reservations.html", active=active, history=history)


# --------------------------------------------------------------------------- #
# Administracija
# --------------------------------------------------------------------------- #
@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    db = get_db()
    books = db.execute(
        "SELECT b.*, (SELECT COUNT(*) FROM reservations r WHERE r.book_id = b.id AND r.status = 'active')"
        " AS active_res FROM books b ORDER BY b.title COLLATE NOCASE").fetchall()
    status = request.args.get("status", "active")
    sql = ("SELECT r.*, u.name AS user_name, u.email AS user_email, b.title, b.author"
           " FROM reservations r JOIN users u ON u.id = r.user_id JOIN books b ON b.id = r.book_id")
    if status in ("active", "cancelled"):
        sql += " WHERE r.status = ?"
        reservations = db.execute(sql + " ORDER BY r.created_at DESC, r.id DESC", (status,)).fetchall()
    else:
        reservations = db.execute(sql + " ORDER BY r.created_at DESC, r.id DESC").fetchall()
    stats = db.execute(
        "SELECT (SELECT COUNT(*) FROM books) AS titles,"
        " (SELECT COALESCE(SUM(total_copies),0) FROM books) AS copies,"
        " (SELECT COUNT(*) FROM reservations WHERE status='active') AS active,"
        " (SELECT COUNT(*) FROM users WHERE role='student') AS students").fetchone()
    return render_template("admin/dashboard.html", books=books, reservations=reservations,
                           stats=stats, status=status)


def _book_form_data(form):
    data = {
        "title": form.get("title", "").strip(),
        "author": form.get("author", "").strip(),
        "category": form.get("category", "").strip(),
        "description": form.get("description", "").strip(),
        "cover_url": form.get("cover_url", "").strip(),
        "year": form.get("year", "").strip(),
        "total_copies": form.get("total_copies", "").strip(),
    }
    errors = []
    for key, label in (("title", "Naslov"), ("author", "Avtor"), ("category", "Kategorija")):
        if not data[key]:
            errors.append(f"{label} je obvezen podatek.")
    try:
        data["total_copies"] = int(data["total_copies"])
        if data["total_copies"] < 0:
            raise ValueError
    except ValueError:
        errors.append("Število izvodov mora biti nenegativno celo število.")
    if data["year"]:
        try:
            data["year"] = int(data["year"])
        except ValueError:
            errors.append("Leto mora biti število.")
    else:
        data["year"] = None
    if data["cover_url"] and not data["cover_url"].startswith(("http://", "https://")):
        errors.append("URL naslovnice mora se začeti s http:// ali https://.")
    return data, errors


@app.route("/admin/knjiga/nova", methods=["GET", "POST"])
@role_required("admin")
def admin_book_new():
    form = {"total_copies": 1}
    if request.method == "POST":
        data, errors = _book_form_data(request.form)
        if not errors:
            db = get_db()
            cur = db.execute(
                "INSERT INTO books (title, author, category, description, cover_url, year,"
                " total_copies, available_copies) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (data["title"], data["author"], data["category"], data["description"],
                 data["cover_url"], data["year"], data["total_copies"], data["total_copies"]))
            db.commit()
            flash(f"Knjiga »{data['title']}« dodana v katalog.", "ok")
            return redirect(url_for("book_detail", book_id=cur.lastrowid))
        for e in errors:
            flash(e, "error")
        form = request.form
    return render_template("admin/book_form.html", form=form, book=None, categories=categories())


@app.route("/admin/knjiga/<int:book_id>/uredi", methods=["GET", "POST"])
@role_required("admin")
def admin_book_edit(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        abort(404)
    active = db.execute("SELECT COUNT(*) FROM reservations WHERE book_id = ? AND status = 'active'",
                        (book_id,)).fetchone()[0]
    form = dict(book)
    if request.method == "POST":
        data, errors = _book_form_data(request.form)
        if not errors and data["total_copies"] < active:
            errors.append(f"Izvodov ne more biti manj kot aktivnih rezervacij ({active}).")
        if not errors:
            db.execute(
                "UPDATE books SET title=?, author=?, category=?, description=?, cover_url=?, year=?,"
                " total_copies=?, available_copies=? WHERE id=?",
                (data["title"], data["author"], data["category"], data["description"], data["cover_url"],
                 data["year"], data["total_copies"], data["total_copies"] - active, book_id))
            db.commit()
            flash("Spremembe shranjene.", "ok")
            return redirect(url_for("book_detail", book_id=book_id))
        for e in errors:
            flash(e, "error")
        form = request.form
    return render_template("admin/book_form.html", form=form, book=book, active=active,
                           categories=categories())


@app.route("/admin/knjiga/<int:book_id>/izbrisi", methods=["POST"])
@role_required("admin")
def admin_book_delete(book_id):
    db = get_db()
    book = db.execute("SELECT title FROM books WHERE id = ?", (book_id,)).fetchone()
    if book:
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        flash(f"Knjiga »{book['title']}« izbrisana.", "ok")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/rezervacija/<int:res_id>/preklici", methods=["POST"])
@role_required("admin")
def admin_cancel_reservation(res_id):
    if _cancel(res_id):
        flash("Rezervacija zaključena, izvod vrnjen.", "ok")
    return redirect(url_for("admin_dashboard", status=request.form.get("status", "active")))


# --------------------------------------------------------------------------- #
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(400)
def http_error(err):
    messages = {403: "Za to stran nimaš dovoljenja.", 404: "Te strani na naših policah ni.",
                400: "Zahteva ni veljavna."}
    return render_template("error.html", code=err.code, message=messages.get(err.code, "")), err.code


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
