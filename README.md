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

### Deploy on Vercel

- Connect the repo to Vercel. Flask is detected automatically.
- On Vercel, DB and uploads use `/tmp` (ephemeral between invocations). For persistent storage use a database (e.g. Vercel Postgres) and blob storage (e.g. Vercel Blob) and swap in `app.py`.

### Next steps for real payments

- Replace the fake `/buy/<pack_id>` logic with your Georgian bank payment integration.
- After successful callback from the bank, call the same DB insert that currently happens directly in `/buy/<pack_id>` so purchases and admin stats stay correct.
