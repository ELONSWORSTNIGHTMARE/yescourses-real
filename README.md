## Yescourses

Single Flask app: landing, course pages, and admin. One codebase for local and Vercel.

### Features

- **Landing** (`/`): hero, 3 pricing packs, FAQ, auth modal (register/login), purchase flow
- **Course** (`/course/<pack_id>`): only for logged-in users who bought that pack; shows **uploaded videos** from admin
- **Admin** (`/admin`): login then dashboard (stats, video upload, list/delete)
  - Credentials: **ADMIN** / **yestour111**
- All HTML is served by Flask from `templates/`. Static assets in `static/` (CSS, JS, uploads). No duplicate root HTML files.

### Running locally

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Upload videos at `http://127.0.0.1:5000/admin`; they appear on `/course/basic` for users who bought that pack.

### Deploy on Vercel

- Connect the repo to Vercel. Flask is detected automatically.
- On Vercel, DB and uploads use `/tmp` (ephemeral between invocations). For persistent storage use a database (e.g. Vercel Postgres) and blob storage (e.g. Vercel Blob) and swap in `app.py`.

### Next steps for real payments

- Replace the fake `/buy/<pack_id>` logic with your Georgian bank payment integration.
- After successful callback from the bank, call the same DB insert that currently happens directly in `/buy/<pack_id>` so purchases and admin stats stay correct.

