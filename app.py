import mimetypes

from flask import (
    Flask,
    Response,
    flash,
    get_flashed_messages,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash, check_password_hash, safe_join
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import hashlib
import json
import os
from datetime import datetime

from db_helpers import ex, get_db, init_db as db_init_schema, is_unique_violation, row_to_dict, USE_POSTGRES
from storage_helpers import upload_video_to_blob


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On Vercel, filesystem is read-only except /tmp (not shared across instances — use DATABASE_URL + Blob)
IS_VERCEL = os.environ.get("VERCEL") == "1"
if IS_VERCEL:
    UPLOAD_FOLDER = "/tmp/yescourses_uploads"
else:
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
# Required on HTTPS (Vercel) or logins/sessions break or behave oddly across devices
if IS_VERCEL or os.environ.get("SESSION_COOKIE_SECURE") == "1":
    app.config["SESSION_COOKIE_SECURE"] = True

PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# Mobile browsers (esp. iOS Safari) need correct MIME + Range requests; guess_type is weak for .mp4.
_VIDEO_MIME = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
}

# Admin: panel login + site user that may upload / manage videos
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "yestour111"
ADMIN_EMAIL = "matebedeladze@gmail.com"


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
        "price": 149,
        "old_price": None,
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
        "name": "სრული მენტორშიპი",
        "price": 249,
        "old_price": None,
        "description": [
            "იდეალურია მათთვის, ვინც ნულიდან იწყებს.",
            "კვირაში 2-3 ლექცია",
            "წვდომა საუკეთესო დახურულ ჯგუფზე",
            "პირდაპირი კონტაქტი მენტორებთან",
        ],
    },
    "premium": {
        "id": "premium",
        "name": "1-1 Mentorship",
        "price": 399,
        "old_price": None,
        "description": [
            "იდეალურია მათთვის, ვისაც სურს 1-1 სწავლა პირად მენტორთან.",
            "კვირაში ორი Private ლექცია",
            "ყველასთვის ინდივიდუალური მიდგომა",
            "პროგრესის მონიტორინგი",
            "მუდმივი მხარდაჭერა",
        ],
    },
}


def video_play_src(row):
    """Public HTTPS URL if set, else same-origin /uploads/…"""
    r = row_to_dict(row)
    url = (r.get("remote_src") or "").strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    fn = (r.get("filename") or "").strip()
    if not fn:
        return ""
    return url_for("uploaded_file", filename=fn)


def render_course_html_response(pack_id, videos_rows):
    """Serve course.html with embedded JSON (no Jinja in file — avoids raw {{ }} on static hosts)."""
    warnings = []
    if IS_VERCEL:
        for row in videos_rows:
            r = row_to_dict(row)
            if not (r.get("remote_src") or "").strip():
                warnings.append(
                    "ერთი ან მეტი ვიდეო ლოკალური ფაილია — სხვა მოწყობილობაზე ხშირად არ იტვირთება. "
                    "გამოიყენე „საჯარო ვიდეოს ბმული“ (HTTPS MP4) ატვირთვის გვერდზე."
                )
                break

    payload = {
        "pack_id": pack_id,
        "pack_name": PACKS[pack_id]["name"],
        "warnings": warnings,
        "videos": [
            {
                "title": row["title"],
                "description": (row["description"] or ""),
                "src": video_play_src(row),
            }
            for row in videos_rows
        ],
    }
    path = os.path.join(BASE_DIR, "course.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    payload_js = json.dumps(payload, ensure_ascii=False)
    # Safe inside <script>: avoid closing the script tag from user content
    payload_js = payload_js.replace("<", "\\u003c")
    marker = "window.__COURSE_PAYLOAD__ = null; /*__YES_COURSES_INJECT__*/"
    injected = f"window.__COURSE_PAYLOAD__ = {payload_js}; /*__YES_COURSES_INJECT__*/"
    if marker not in html:
        raise RuntimeError("course.html is missing __YES_COURSES_INJECT__ marker")
    html = html.replace(marker, injected, 1)
    r = Response(html, mimetype="text/html; charset=utf-8")
    # Stop CDN/browser serving another user's cached course HTML
    r.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    return r


def admin_videos_to_json(videos_rows):
    out = []
    for row in videos_rows:
        r = row_to_dict(row)
        out.append(
            {
                "id": int(r["id"]),
                "title": r["title"],
                "description": r["description"] or "",
                "pack_id": r["pack_id"],
                "order_index": int(r["order_index"] or 1),
                "filename": r["filename"],
                "remote_src": (r.get("remote_src") or ""),
            }
        )
    return out


def build_admin_payload(show_dashboard, stats, videos_json_list):
    flashes = get_flashed_messages(with_categories=True)
    vids = videos_json_list or []
    file_only = sum(
        1 for v in vids if not (str(v.get("remote_src") or "").strip())
    )
    diag = {
        "database": "postgres" if USE_POSTGRES else "sqlite",
        "vercel": bool(IS_VERCEL),
        "fileOnlyVideoCount": file_only,
    }
    if IS_VERCEL and not USE_POSTGRES:
        diag["alert"] = (
            "არ გამოიყენება Postgres (DATABASE_URL). სხვა მოწყობილობაზე ბაზა ცარიელია — "
            "დაამატე DATABASE_URL Vercel-ში და გადააწყვე."
        )
    elif IS_VERCEL and file_only > 0:
        diag["alert"] = (
            f"{file_only} ვიდეო ფაილადაა (არა HTTPS ბმული) — სხვა მოწყობილობაზე შეიძლება არ იტვირთოს. "
            "შეცვალი ბმულით ან ხელახლა დაამატე „საჯარო ვიდეოს ბმული“."
        )
    else:
        diag["alert"] = ""

    return {
        "showDashboard": bool(show_dashboard),
        "stats": stats or {},
        "videos": vids,
        "diag": diag,
        "flashes": [
            {"category": str(cat or "message"), "message": str(msg or "")}
            for cat, msg in flashes
        ],
    }


def render_admin_html_response(payload_dict):
    """admin.html without Jinja — payload drives dashboard (same pattern as course page)."""
    path = os.path.join(BASE_DIR, "admin.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    payload_js = json.dumps(payload_dict, ensure_ascii=False)
    payload_js = payload_js.replace("<", "\\u003c")
    marker = "window.__ADMIN_PAYLOAD__ = null; /*__ADMIN_INJECT__*/"
    injected = f"window.__ADMIN_PAYLOAD__ = {payload_js}; /*__ADMIN_INJECT__*/"
    if marker not in html:
        raise RuntimeError("admin.html is missing __ADMIN_INJECT__ marker")
    html = html.replace(marker, injected, 1)
    r = Response(html, mimetype="text/html; charset=utf-8")
    r.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    return r


def ensure_admin_user():
    conn = get_db()
    cur = conn.cursor()
    ex(cur, "SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,))
    if cur.fetchone() is None:
        ex(
            cur,
            """
            INSERT INTO users (email, name, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                ADMIN_EMAIL,
                "Admin",
                generate_password_hash("Matebedeladze1"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    conn.close()


def init_db():
    db_init_schema()
    ensure_admin_user()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    cur = conn.cursor()
    ex(cur, "SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


def user_has_pack(user_id, pack_id):
    conn = get_db()
    cur = conn.cursor()
    ex(
        cur,
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
    ex(cur, "SELECT pack_id FROM purchases WHERE user_id = ?", (user_id,))
    ids = {row["pack_id"] for row in cur.fetchall()}
    conn.close()
    return ids


def serve_course_page(pack_id):
    """Render course.html with video payload (requires user account or admin session)."""
    if pack_id not in PACKS:
        flash("ასეთი პაკეტი არ არსებობს.", "error")
        return redirect(url_for("index"))

    user = get_current_user()
    # Admin panel login only set is_admin until now — allow preview after video upload.
    if not user and not is_admin_user():
        flash("კურსზე წვდომისთვის საჭიროა ავტორიზაცია.", "error")
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()
    ex(
        cur,
        "SELECT * FROM videos WHERE pack_id = ? ORDER BY order_index ASC, uploaded_at ASC",
        (pack_id,),
    )
    videos = cur.fetchall()
    conn.close()

    return render_course_html_response(pack_id, videos)


@app.route("/course.html")
def course_html():
    pack_id = request.args.get("pack", "basic")
    return serve_course_page(pack_id)


@app.route("/course/<pack_id>")
def course_canonical_redirect(pack_id):
    """Old-style /course/basic → /course.html?pack=basic (visible .html URL)."""
    return redirect(url_for("course_html", pack=pack_id), code=301)


@app.route("/")
@app.route("/index.html")
def index():
    user = get_current_user()
    purchased = get_user_purchased_pack_ids(user["id"] if user else None)
    html = render_template(
        "index.html", packs=PACKS, user=user, purchased_pack_ids=purchased
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/healthz")
def healthz():
    """Quick check from any device: is Postgres configured? (no secrets returned)"""
    return jsonify(
        {
            "ok": True,
            "database": "postgres" if USE_POSTGRES else "sqlite",
            "vercel": bool(IS_VERCEL),
        }
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
    uid = None
    try:
        if USE_POSTGRES:
            ex(
                cur,
                """
                INSERT INTO users (email, name, password_hash, created_at)
                VALUES (?, ?, ?, ?) RETURNING id
                """,
                (
                    email,
                    name,
                    generate_password_hash(password),
                    datetime.utcnow().isoformat(),
                ),
            )
            uid = cur.fetchone()["id"]
        else:
            ex(
                cur,
                """
                INSERT INTO users (email, name, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    email,
                    name,
                    generate_password_hash(password),
                    datetime.utcnow().isoformat(),
                ),
            )
            uid = cur.lastrowid
        conn.commit()
    except Exception as e:
        if is_unique_violation(e):
            conn.close()
            flash("ამ ელფოსტით მომხმარებელი უკვე არსებობს.", "error")
            return redirect(request.referrer or url_for("index"))
        conn.close()
        raise
    conn.close()

    session["user_id"] = uid
    if email.lower() == ADMIN_EMAIL.lower():
        session["is_admin"] = True
    flash("რეგისტრაცია წარმატებით დასრულდა!", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_db()
    cur = conn.cursor()
    ex(cur, "SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        flash("არასწორი ელფოსტა ან პაროლი.", "error")
        return redirect(request.referrer or url_for("index"))

    session["user_id"] = user["id"]
    user_email = (user["email"] or "").lower()
    if user_email == ADMIN_EMAIL.lower():
        session["is_admin"] = True
        flash(
            "შესვლა წარმატებულია! ადმინისტრატორად ხარ — შეგიძლია ვიდეოების ატვირთვა.",
            "success",
        )
    else:
        flash("შესვლა წარმატებულია!", "success")
    return redirect(request.referrer or url_for("index"))


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
        return redirect(url_for("course_html", pack=pack_id))

    # TODO: connect real bank payment here later.
    conn = get_db()
    cur = conn.cursor()
    ex(
        cur,
        "INSERT INTO purchases (user_id, pack_id, purchased_at) VALUES (?, ?, ?)",
        (user["id"], pack_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    flash("გილოცავ! პაკეტი წარმატებით შეიძინე.", "success")
    return redirect(url_for("course_html", pack=pack_id))


def insert_video_from_filestorage(pack_id, title, description, order_index, file_storage):
    """
    Upload to Vercel Blob when BLOB_READ_WRITE_TOKEN is set; otherwise save under UPLOAD_FOLDER.
    Returns None on success, or Georgian error message string.
    """
    base_name = secure_filename(file_storage.filename or "")
    if not base_name:
        base_name = "video"
    name, ext = os.path.splitext(base_name)
    ext_lower = ext.lower()
    if not ext_lower or ext_lower not in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"):
        ext = ".mp4"
        ext_lower = ".mp4"
    filename = f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"

    try:
        raw = file_storage.read()
    except OSError:
        return "ვიდეოს წაკითხვა ვერ მოხერხდა."

    if not raw:
        return "გთხოვ აირჩიო ვიდეო ფაილი."

    content_type = _VIDEO_MIME.get(ext_lower) or "application/octet-stream"
    remote_src = upload_video_to_blob(filename, raw, content_type)

    save_path = None
    if not remote_src:
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        try:
            with open(save_path, "wb") as f:
                f.write(raw)
        except OSError:
            return "ვიდეოს შენახვა ვერ მოხერხდა."

    try:
        conn = get_db()
        cur = conn.cursor()
        ex(
            cur,
            """
            INSERT INTO videos (pack_id, title, description, filename, order_index, uploaded_at, remote_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pack_id,
                title,
                description,
                filename,
                order_index,
                datetime.utcnow().isoformat(),
                remote_src,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        if save_path and os.path.isfile(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        return "ბაზაში ჩაწერა ვერ მოხერხდა."

    if IS_VERCEL and not remote_src:
        flash(
            "შენიშვნა: ფაილი ინახება მხოლოდ ამ სერვერის დროებით დისკზე — სხვა მომხმარებლებს ხშირად ვერ ჩანს. "
            "Vercel-ზე გამოიყენე „საჯარო ბმული“ (ქვემოთ) ან დაამატე DATABASE_URL (Postgres).",
            "warning",
        )
    return None


def insert_remote_video_row(pack_id, title, description, order_index, video_url: str):
    """Store a public HTTPS video URL so every user/device sees the same stream (works on Vercel)."""
    video_url = (video_url or "").strip()
    if not video_url.startswith("http://") and not video_url.startswith("https://"):
        return "დაუშვებელი ბმული (საჭიროა https:// ან http://)."

    fn = "remote_" + hashlib.sha256(video_url.encode("utf-8")).hexdigest()[:24] + ".mp4"

    try:
        conn = get_db()
        cur = conn.cursor()
        ex(
            cur,
            """
            INSERT INTO videos (pack_id, title, description, filename, order_index, uploaded_at, remote_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pack_id,
                title,
                description,
                fn,
                order_index,
                datetime.utcnow().isoformat(),
                video_url,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        return "ბაზაში ჩაწერა ვერ მოხერხდა."
    return None


def _course_upload_video_impl(pack_id):
    if pack_id not in PACKS:
        flash("ასეთი პაკეტი არ არსებობს.", "error")
        return redirect(url_for("index"))
    user = get_current_user()
    if not user:
        flash("შესვლა საჭიროა.", "error")
        return redirect(url_for("index"))
    if not is_admin_user():
        flash("მხოლოდ ადმინს შეუძლია ვიდეოს ატვირთვა.", "error")
        return redirect(url_for("course_html", pack=pack_id))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    order_index = request.form.get("order_index", "1")
    file = request.files.get("video_file")

    if not title:
        flash("სათაური სავალდებულოა.", "error")
        return redirect(url_for("course_html", pack=pack_id))
    if not file or not getattr(file, "filename", None) or not (file.filename or "").strip():
        flash("გთხოვ აირჩიო ვიდეო ფაილი.", "error")
        return redirect(url_for("course_html", pack=pack_id))

    try:
        order_index = int(order_index)
    except (ValueError, TypeError):
        order_index = 1

    err = insert_video_from_filestorage(pack_id, title, description, order_index, file)
    if err:
        flash(err, "error")
        return redirect(url_for("course_html", pack=pack_id))

    flash("ვიდეო წარმატებით აიტვირთა.", "success")
    return redirect(url_for("course_html", pack=pack_id))


@app.route("/course_upload.html", methods=["POST"])
def course_upload_video_html():
    """Same as legacy path but URL stays in the .html style namespace."""
    pack_id = (request.form.get("pack_id") or "basic").strip()
    return _course_upload_video_impl(pack_id)


@app.route("/course/<pack_id>/upload", methods=["POST"])
def course_upload_video(pack_id):
    return _course_upload_video_impl(pack_id)


def is_admin_user():
    """Admin capability is session-only so /admin/logout can revoke access."""
    return bool(session.get("is_admin"))


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
        ex(cur, "SELECT COUNT(*) AS c FROM purchases WHERE pack_id = ?", (pid,))
        row = cur.fetchone()
        stats[pid] = row["c"] if row else 0
    ex(
        cur,
        "SELECT * FROM videos ORDER BY pack_id ASC, order_index ASC, uploaded_at ASC",
    )
    videos = cur.fetchall()
    conn.close()
    return {"stats": stats, "videos": videos}


@app.route("/admin", methods=["GET", "POST"])
@app.route("/admin.html", methods=["GET", "POST"])
@app.route("/admin_login.html", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            # So /course.html after upload works (same session as „user“ for get_current_user).
            conn = get_db()
            cur = conn.cursor()
            ex(cur, "SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,))
            admin_row = cur.fetchone()
            conn.close()
            if admin_row:
                session["user_id"] = admin_row["id"]
            return redirect("/admin.html")

        flash("არასწორი მომხმარებელი ან პაროლი.", "error")
        return redirect("/admin.html")

    if is_admin_user():
        data = get_admin_data()
        payload = build_admin_payload(
            True,
            data["stats"],
            admin_videos_to_json(data["videos"]),
        )
        return render_admin_html_response(payload)

    return render_admin_html_response(build_admin_payload(False, {}, []))


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(e):
    flash("ვიდეო ძალიან დიდია. მაქსიმუმ 500 MB.", "error")
    return redirect("/admin.html")


@app.route("/upload_video.html")
def upload_video_page():
    if not is_admin_user():
        flash("ადმინისტრატორის შესვლა საჭიროა (საიტზე შესვლა ან ადმინ პანელი).", "error")
        return redirect("/admin.html")
    return render_template("upload_video.html", packs=PACKS)


@app.route("/admin/upload_video", methods=["GET", "POST"])
@app.route("/admin/upload_video.html", methods=["GET", "POST"])
def admin_upload_video():
    if request.method == "GET":
        return redirect("/upload_video.html")
    if not require_admin():
        return redirect("/admin.html")

    pack_id = request.form.get("pack_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    order_index = request.form.get("order_index", "1")
    video_url = request.form.get("video_url", "").strip()
    file = request.files.get("video_file")

    if pack_id not in PACKS:
        flash("არასწორი პაკეტი.", "error")
        return redirect("/admin.html")

    if not title:
        flash("სათაური სავალდებულოა.", "error")
        return redirect("/admin.html")

    try:
        order_index = int(order_index)
    except (ValueError, TypeError):
        order_index = 1

    if video_url:
        err = insert_remote_video_row(
            pack_id, title, description, order_index, video_url
        )
        if err:
            flash(err, "error")
            return redirect("/admin.html")
        flash("ვიდეოს ბმული შენახულია — ყველა მომხმარებელს ერთნაირად უნდა ჩანდეს.", "success")
        return redirect(url_for("course_html", pack=pack_id))

    if not file or not getattr(file, "filename", None) or not (file.filename or "").strip():
        flash("ჩასვი საჯარო ვიდეოს ბმული (https) ან აირჩიე ფაილი.", "error")
        return redirect("/admin.html")

    err = insert_video_from_filestorage(pack_id, title, description, order_index, file)
    if err:
        flash(err, "error")
        return redirect("/admin.html")

    flash("ვიდეო წარმატებით აიტვირთა.", "success")
    return redirect(url_for("course_html", pack=pack_id))


@app.route("/admin/update_video/<int:video_id>", methods=["POST"])
def admin_update_video(video_id):
    if not require_admin():
        return redirect("/admin.html")

    pack_id = request.form.get("pack_id", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    order_index = request.form.get("order_index", "1")

    if pack_id not in PACKS:
        flash("არასწორი პაკეტი.", "error")
        return redirect("/admin.html")
    if not title:
        flash("სათაური სავალდებულოა.", "error")
        return redirect("/admin.html")
    try:
        order_index = int(order_index)
    except (ValueError, TypeError):
        order_index = 1

    conn = get_db()
    cur = conn.cursor()
    ex(cur, "SELECT id FROM videos WHERE id = ?", (video_id,))
    if not cur.fetchone():
        conn.close()
        flash("ვიდეო ვერ მოიძებნა.", "error")
        return redirect("/admin.html")

    ex(
        cur,
        """
        UPDATE videos
        SET pack_id = ?, title = ?, description = ?, order_index = ?
        WHERE id = ?
        """,
        (pack_id, title, description, order_index, video_id),
    )
    conn.commit()
    conn.close()
    flash("ვიდეო განახლდა.", "success")
    return redirect("/admin.html")


@app.route("/admin/delete_video/<int:video_id>", methods=["POST"])
def admin_delete_video(video_id):
    if not require_admin():
        return redirect("/admin.html")

    conn = get_db()
    cur = conn.cursor()
    ex(cur, "SELECT filename, remote_src FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()
    if video:
        r = row_to_dict(video)
        remote = (r.get("remote_src") or "").strip()
        if not remote:
            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"], r.get("filename") or ""
            )
            if os.path.exists(filepath):
                os.remove(filepath)
        ex(cur, "DELETE FROM videos WHERE id = ?", (video_id,))
        conn.commit()
    conn.close()

    flash("ვიდეო წაიშალა.", "info")
    return redirect("/admin.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/admin.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """
    Stream video with correct Content-Type, Accept-Ranges, and 206 partial responses.
    Required for playback on many phones (especially iOS).
    """
    directory = app.config["UPLOAD_FOLDER"]
    path = safe_join(directory, filename)
    if path is None or not os.path.isfile(path):
        return Response("Not found", status=404, mimetype="text/plain")

    ext = os.path.splitext(filename)[1].lower()
    mimetype = _VIDEO_MIME.get(ext) or mimetypes.guess_type(filename)[0]
    if not mimetype:
        mimetype = "application/octet-stream"

    return send_file(
        path,
        mimetype=mimetype,
        conditional=True,
        max_age=3600,
        etag=True,
    )


# Ensure DB exists when app is loaded (e.g. on Vercel serverless)
init_db()

if IS_VERCEL and not USE_POSTGRES:
    app.logger.warning(
        "Vercel: SQLite lives in /tmp per instance — other users often see empty courses. "
        "Set DATABASE_URL (e.g. Supabase Postgres URI from Project Settings → Database)."
    )

if __name__ == "__main__":
    app.run(debug=True)

