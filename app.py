from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On Vercel, filesystem is read-only except /tmp
IS_VERCEL = os.environ.get("VERCEL") == "1"
if IS_VERCEL:
    DB_PATH = "/tmp/yescourses_data.db"
    UPLOAD_FOLDER = "/tmp/yescourses_uploads"
else:
    DB_PATH = os.path.join(BASE_DIR, "data.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app = Flask(
    __name__,
    template_folder=BASE_DIR,
)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# Allow video uploads up to 500 MB
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
# So session cookie works after redirect (e.g. on Vercel)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

PUBLIC_DIR = os.path.join(BASE_DIR, "public")


@app.route("/styles.css")
def serve_css():
    path = os.path.join(BASE_DIR, "styles.css")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                css = f.read()
            r = Response(css, mimetype="text/css")
            r.headers["Cache-Control"] = "public, max-age=300"
            return r
        except Exception:
            pass
    path_public = os.path.join(PUBLIC_DIR, "styles.css")
    if os.path.isfile(path_public):
        try:
            with open(path_public, "r", encoding="utf-8", errors="replace") as f:
                css = f.read()
            return Response(css, mimetype="text/css")
        except Exception:
            pass
    return Response("/* styles.css not found */", mimetype="text/css", status=404)


@app.route("/main.js")
def serve_js():
    for directory in (BASE_DIR, PUBLIC_DIR):
        path = os.path.join(directory, "main.js")
        if os.path.isfile(path):
            r = send_from_directory(directory, "main.js", mimetype="application/javascript")
            r.headers["Cache-Control"] = "public, max-age=300"
            return r
    return "// JS not found", 404, {"Content-Type": "application/javascript"}


@app.route("/upload_video.css")
def serve_upload_video_css():
    path = os.path.join(BASE_DIR, "upload_video.css")
    if os.path.isfile(path):
        return send_from_directory(BASE_DIR, "upload_video.css", mimetype="text/css")
    return "/* upload_video.css not found */", 404, {"Content-Type": "text/css"}


@app.route("/upload_video.js")
def serve_upload_video_js():
    path = os.path.join(BASE_DIR, "upload_video.js")
    if os.path.isfile(path):
        return send_from_directory(BASE_DIR, "upload_video.js", mimetype="application/javascript")
    return "// upload_video.js not found", 404, {"Content-Type": "application/javascript"}


PACKS = {
    "basic": {
        "id": "basic",
        "name": "საწყისი პაკეტი",
        "price": 65,
        "old_price": 90,
        "description": [
            "ონლაინ ტუტორიალები",
            "ბილეთების ყიდვა",
            "ჯავშნების გაკეთება",
            "დაძღვევა",
            "სახლების დაჯავშნა",
        ],
    },
    "plus": {
        "id": "plus",
        "name": "პლუს პაკეტი",
        "price": 107,
        "old_price": 190,
        "description": [
            "კვირაში 2-3 ლექცია",
            "წვდომა საუკეთესო დახურულ ჯგუფზე",
            "პირდაპირი კონტაქტი მენტორებთან",
        ],
    },
    "premium": {
        "id": "premium",
        "name": "პრემიუმ პაკეტი",
        "price": 400,
        "old_price": None,
        "description": [
            "კვირაში ორი Private ლექცია",
            "ყველასთვის ინდივიდუალური მიდგომა",
            "პროგრესის მონიტორინგი",
            "მუდმივი მხარდაჭერა",
        ],
    },
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pack_id TEXT NOT NULL,
            purchased_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pack_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 1,
            uploaded_at TEXT NOT NULL
        )
        """
    )

    conn.commit()

    # Ensure admin user can always log in (matebedeladze@gmail.com / Matebedeladze1)
    cur.execute("SELECT id FROM users WHERE email = ?", ("matebedeladze@gmail.com",))
    if cur.fetchone() is None:
        cur.execute(
            """
            INSERT INTO users (email, name, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                "matebedeladze@gmail.com",
                "Admin",
                generate_password_hash("Matebedeladze1"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    conn.close()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


def user_has_pack(user_id, pack_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM purchases WHERE user_id = ? AND pack_id = ?",
        (user_id, pack_id),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_user_purchased_pack_ids(user_id):
    if not user_id:
        return set()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT pack_id FROM purchases WHERE user_id = ?", (user_id,))
    ids = {row["pack_id"] for row in cur.fetchall()}
    conn.close()
    return ids


@app.route("/admin.html")
@app.route("/admin_login.html")
def redirect_old_admin():
    return redirect(url_for("admin_page"))


@app.route("/course.html")
def redirect_old_course():
    return redirect(url_for("index"))


@app.route("/")
def index():
    user = get_current_user()
    purchased = get_user_purchased_pack_ids(user["id"] if user else None)
    return render_template(
        "index.html", packs=PACKS, user=user, purchased_pack_ids=purchased
    )


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        flash("გთხოვ, შეავსე ყველა ველი.", "error")
        return redirect(request.referrer or url_for("index"))

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (
                email,
                name,
                generate_password_hash(password),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        flash("ამ ელფოსტით მომხმარებელი უკვე არსებობს.", "error")
        return redirect(request.referrer or url_for("index"))

    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    session["user_id"] = user["id"]
    flash("რეგისტრაცია წარმატებით დასრულდა!", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        flash("არასწორი ელფოსტა ან პაროლი.", "error")
        return redirect(request.referrer or url_for("index"))

    session["user_id"] = user["id"]
    if user["email"] == "matebedeladze@gmail.com":
        session["is_admin"] = True
    flash("შესვლა წარმატებულია! შენ ადმინი ხარ — შეგიძლია ვიდეოს ატვირთვა კურსის გვერდიდან.", "success")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    flash("თქვი გამოსვლა ანგარიშიდან.", "info")
    return redirect(url_for("index"))


@app.route("/buy/<pack_id>", methods=["POST"])
def buy_pack(pack_id):
    if pack_id not in PACKS:
        flash("ასეთი პაკეტი არ არსებობს.", "error")
        return redirect(url_for("index"))

    user = get_current_user()
    if not user:
        flash("პაკეტის შესაძენად გთხოვ, ჯერ დარეგისტრირდი ან შედი ანგარიშზე.", "error")
        return redirect(url_for("index"))

    if user_has_pack(user["id"], pack_id):
        flash("ეს პაკეტი უკვე გაქვს შეძენილი.", "info")
        return redirect(url_for("course", pack_id=pack_id))

    # TODO: connect real bank payment here later.
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO purchases (user_id, pack_id, purchased_at) VALUES (?, ?, ?)",
        (user["id"], pack_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    flash("გილოცავ! პაკეტი წარმატებით შეიძინე.", "success")
    return redirect(url_for("course", pack_id=pack_id))


@app.route("/course/<pack_id>")
def course(pack_id):
    if pack_id not in PACKS:
        flash("ასეთი პაკეტი არ არსებობს.", "error")
        return redirect(url_for("index"))

    user = get_current_user()
    if not user:
        flash("კურსზე წვდომისთვის საჭიროა ავტორიზაცია.", "error")
        return redirect(url_for("index"))

    is_admin = session.get("is_admin") or (user and user.get("email") == ADMIN_EMAIL)
    if not is_admin and not user_has_pack(user["id"], pack_id):
        flash("ამ პაკეტზე წვდომა არ გაქვს. გთხოვ, ჯერ შეიძინე.", "error")
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM videos WHERE pack_id = ? ORDER BY order_index ASC, uploaded_at ASC",
        (pack_id,),
    )
    videos = cur.fetchall()
    conn.close()

    return render_template(
        "course.html",
        pack=PACKS[pack_id],
        pack_id=pack_id,
        videos=videos,
        user=user,
        is_admin=is_admin,
    )


@app.route("/course/<pack_id>/upload", methods=["POST"])
def course_upload_video(pack_id):
    if pack_id not in PACKS:
        flash("ასეთი პაკეტი არ არსებობს.", "error")
        return redirect(url_for("index"))
    user = get_current_user()
    if not user:
        flash("შესვლა საჭიროა.", "error")
        return redirect(url_for("index"))
    if not is_admin_user():
        flash("მხოლოდ ადმინს შეუძლია ვიდეოს ატვირთვა.", "error")
        return redirect(url_for("course", pack_id=pack_id))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    order_index = request.form.get("order_index", "1")
    file = request.files.get("video_file")

    if not title:
        flash("სათაური სავალდებულოა.", "error")
        return redirect(url_for("course", pack_id=pack_id))
    if not file or not getattr(file, "filename", None) or not (file.filename or "").strip():
        flash("გთხოვ აირჩიო ვიდეო ფაილი.", "error")
        return redirect(url_for("course", pack_id=pack_id))

    try:
        order_index = int(order_index)
    except (ValueError, TypeError):
        order_index = 1

    base_name = secure_filename(file.filename)
    if not base_name:
        base_name = "video"
    name, ext = os.path.splitext(base_name)
    if not ext or ext.lower() not in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"):
        ext = ".mp4"
    filename = f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    try:
        file.save(save_path)
    except Exception:
        flash("ვიდეოს შენახვა ვერ მოხერხდა.", "error")
        return redirect(url_for("course", pack_id=pack_id))

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO videos (pack_id, title, description, filename, order_index, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pack_id, title, description, filename, order_index, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        flash("ბაზაში ჩაწერა ვერ მოხერხდა.", "error")
        return redirect(url_for("course", pack_id=pack_id))

    flash("ვიდეო წარმატებით აიტვირთა.", "success")
    return redirect(url_for("course", pack_id=pack_id))


ADMIN_USERNAME = "admins"
ADMIN_PASSWORD = "admins"
ADMIN_EMAIL = "matebedeladze@gmail.com"


def is_admin_user():
    if session.get("is_admin"):
        return True
    user = get_current_user()
    return user and user.get("email") == ADMIN_EMAIL


def require_admin():
    if not is_admin_user():
        flash("ადმინისტრატორის წვდომა შეზღუდულია.", "error")
        return False
    return True


def get_admin_data():
    conn = get_db()
    cur = conn.cursor()
    stats = {}
    for pid in PACKS.keys():
        cur.execute("SELECT COUNT(*) AS c FROM purchases WHERE pack_id = ?", (pid,))
        row = cur.fetchone()
        stats[pid] = row["c"] if row else 0
    cur.execute(
        "SELECT * FROM videos ORDER BY pack_id ASC, order_index ASC, uploaded_at ASC"
    )
    videos = cur.fetchall()
    conn.close()
    return {"stats": stats, "videos": videos}


@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_page"))

        flash("არასწორი მომხმარებელი ან პაროლი.", "error")
        return redirect(url_for("admin_page"))

    if session.get("is_admin"):
        data = get_admin_data()
        return render_template(
            "admin.html",
            packs=PACKS,
            stats=data["stats"],
            videos=data["videos"],
            show_dashboard=True,
        )

    return render_template("admin.html", show_dashboard=False)


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(e):
    flash("ვიდეო ძალიან დიდია. მაქსიმუმ 500 MB.", "error")
    return redirect(url_for("admin_page"))


@app.route("/admin/upload_video.html")
def admin_upload_video_page():
    if not session.get("is_admin"):
        flash("ადმინისტრატორის შესვლა საჭიროა.", "error")
        return redirect(url_for("admin_page"))
    return render_template("upload_video.html", packs=PACKS)


@app.route("/admin/upload_video", methods=["GET", "POST"])
def admin_upload_video():
    if request.method == "GET":
        return redirect(url_for("admin_page"))
    if not require_admin():
        return redirect(url_for("admin_page"))

    pack_id = request.form.get("pack_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    order_index = request.form.get("order_index", "1")
    file = request.files.get("video_file")

    if pack_id not in PACKS:
        flash("არასწორი პაკეტი.", "error")
        return redirect(url_for("admin_page"))

    if not title:
        flash("სათაური სავალდებულოა.", "error")
        return redirect(url_for("admin_page"))

    if not file or not getattr(file, "filename", None) or not (file.filename or "").strip():
        flash("გთხოვ აირჩიო ვიდეო ფაილი.", "error")
        return redirect(url_for("admin_page"))

    try:
        order_index = int(order_index)
    except (ValueError, TypeError):
        order_index = 1

    base_name = secure_filename(file.filename)
    if not base_name:
        base_name = "video"
    name, ext = os.path.splitext(base_name)
    if not ext or ext.lower() not in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"):
        ext = ".mp4"
    filename = f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    try:
        file.save(save_path)
    except Exception as e:
        flash("ვიდეოს შენახვა ვერ მოხერხდა.", "error")
        return redirect(url_for("admin_page"))

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO videos (pack_id, title, description, filename, order_index, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pack_id, title, description, filename, order_index, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        flash("ბაზაში ჩაწერა ვერ მოხერხდა.", "error")
        return redirect(url_for("admin_page"))

    flash("ვიდეო წარმატებით აიტვირთა.", "success")
    return redirect(url_for("course", pack_id=pack_id))


@app.route("/admin/delete_video/<int:video_id>", methods=["POST"])
def admin_delete_video(video_id):
    if not require_admin():
        return redirect(url_for("admin_page"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()
    if video:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], video["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
        cur.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.commit()
    conn.close()

    flash("ვიდეო წაიშალა.", "info")
    return redirect(url_for("admin_page"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_page"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Ensure DB exists when app is loaded (e.g. on Vercel serverless)
init_db()

if __name__ == "__main__":
    app.run(debug=True)

