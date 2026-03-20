## Yescourses

Single Flask app: landing, course pages, and admin. One codebase for local and Vercel.

### Features

- **Landing** (`/` or `/index.html`): hero, 3 pricing packs, FAQ, auth modal (register/login), purchase flow
- **Course** (`/course.html?pack=basic|plus|premium`): logged-in users see **uploaded videos** from admin  
  - Old URL `/course/basic` **301 redirects** to `/course.html?pack=basic` so the address bar shows `.html`.
- **Admin** (`/admin.html`, also `/admin` and `/admin_login.html`): login then dashboard (stats, video upload, list/delete)
  - Credentials: **admin** / **yestour111**
- **Upload** (`/upload_video.html`), form POST to `/admin/upload_video.html`

### Running locally

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Upload videos at `http://127.0.0.1:5000/upload_video.html` (after admin login); they appear on `/course.html?pack=basic` for users who bought that pack.

### Deploy on Vercel (important)

Serverless **does not share** SQLite or `/tmp` between requests. **You** may see videos after upload, but **other people** often see an empty course — they hit a different instance with an empty database and no file.

Do this:

1. **Vercel Postgres** (or Neon / Supabase): create a database, copy **`DATABASE_URL`**, add it to the project **Environment Variables** and redeploy.  
   The app uses Postgres when `DATABASE_URL` is set, SQLite otherwise.

2. **Videos for everyone** (pick one):
   - **Recommended:** On `/upload_video.html`, use **„საჯარო ვიდეოს ბმული“** — paste a direct **HTTPS link to an MP4** (e.g. public URL from Cloudflare R2, S3, Bunny CDN, etc.).  
     That URL is stored in the shared database and every user plays the same file.
   - **File upload** on Vercel: only reliable for tiny tests; large uploads also hit Vercel’s **~4.5 MB** serverless request limit. For production, prefer the **public MP4 link** above.

3. After adding Postgres, **re-upload** or **re-add** video rows (old `/tmp` data is not migrated).

Local development unchanged: SQLite + `static/uploads/` when `DATABASE_URL` is unset.

### Supabase Postgres

1. In Supabase: **Project Settings → Database** → copy the **URI** (direct or session pooler).
2. In Vercel (or `.env` locally): set **`DATABASE_URL`** to that URI — **not** `NEXT_PUBLIC_*`.  
   Database passwords must stay **server-only**; `NEXT_PUBLIC_` vars are exposed to browsers.
3. The app also checks **`SUPABASE_DATABASE_URL`**, **`POSTGRES_URL`**, or **`POSTGRES_URL_NON_POOLING`** if `DATABASE_URL` is empty (same rules: no `NEXT_PUBLIC_` for secrets).
4. After first deploy with Postgres, open the site once so **`init_db()`** creates tables (`users`, `purchases`, `videos`).
5. See **`env.example`** for a template.

**If you pasted DB keys or service-role keys in chat or GitHub, rotate them in Supabase** (reset DB password, regenerate JWT secret, roll API keys).

**Debug from another phone:** open `https://YOUR_DOMAIN/healthz` — if `"database":"sqlite"` on Vercel, `DATABASE_URL` is not set for the Python app. You should see `"postgres"` after fixing env + redeploy.

### Next steps for real payments

- Replace the fake `/buy/<pack_id>` logic with your Georgian bank payment integration.
- After successful callback from the bank, call the same DB insert that currently happens directly in `/buy/<pack_id>` so purchases and admin stats stay correct.
