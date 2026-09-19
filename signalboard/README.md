# Signalboard — Notification System

One admin screen to manage every website notification across **WhatsApp**, **Email** and **Web Push**.
Rows are triggers (Login, Logout, Not logged in for 1 day / 1 week, Password reset, Order placed), columns are channels, and each cell is one template the admin can create, edit, switch on/off and test-send.

| Part | Tech | Hosted on |
|---|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework | Render |
| Database | PostgreSQL (SQLite locally) | Neon (free, no expiry) |
| Frontend | React 18 + Vite (website + admin panel) | Vercel |
| WhatsApp | WhatsApp Cloud API (Meta sandbox test number) | — |
| Email | Postmark (Brevo / Resend also supported, one env switch) | — |
| Web Push | OneSignal Web SDK v16 (web only, no iOS/Android) | — |

**Live backend:** `https://<your-service>.onrender.com`  
**Live frontend:** `https://<your-app>.vercel.app`  
**Walkthrough video:** `<Loom / YouTube unlisted link>`

---

## Log in as admin

The admin account is created automatically on every deploy by `python manage.py seed_notifications`, using these env vars on Render:

| Env var | Default |
|---|---|
| `ADMIN_EMAIL` | `admin@signalboard.dev` |
| `ADMIN_PASSWORD` | `Admin@12345` (change it on Render) |
| `ADMIN_PHONE` | your WhatsApp test number, e.g. `919876543210` |

Open the frontend, click **Sign in**, and use those credentials — admins land on `/admin` (Notification settings).

---

## Triggers built

| Trigger | Key | How it fires |
|---|---|---|
| Login | `login` | `POST /api/auth/login/` |
| Logout | `logout` | `POST /api/auth/logout/` |
| Not logged in for 1 day | `inactive_1d` | Inactivity scheduler (user's `last_seen` ≥ 1 day ago) |
| Not logged in for 1 week | `inactive_1w` | Inactivity scheduler (≥ 7 days) |
| Password reset | `password_reset` | `POST /api/auth/password-reset/` ("Forgot password" page) |
| Order placed | `order_placed` | `POST /api/events/order/` ("Place a demo order" on the dashboard) |

Admins can add more triggers from the panel (**Add trigger**). Two kinds are supported:

- **Website event:** code fires it with `fire_trigger("key", user, {...})`.
- **Inactivity:** fires after N days without a visit.

Every trigger works on all 3 channels when its template toggles are on.

---

## Features

**Admin panel (`/admin`)**

- **Notification settings:** the trigger × channel table.
  - Each cell has a toggle, a preview, Edit, Test send, and Sync (WhatsApp only).
  - Pausing a trigger pauses the whole row.
- **Template editor:**
  - Channel-specific fields.
  - Live preview for each channel: a WhatsApp bubble, an email card, and a browser notification.
  - Click-to-insert variables: `{{name}}`, `{{first_name}}`, `{{time}}`, `{{order_id}}` and more.
  - Test send to any number or email.
- **WhatsApp templates are created from the admin panel.** Saving submits the template to Meta (`POST /{WABA_ID}/message_templates`).
  - **Sync** pulls the approval status.
  - Named variables are mapped to Meta's `{{1}}, {{2}}` and the mapping is stored.
  - You can also link an existing Meta template such as `hello_world`.
- **Web Push:** web only. iOS and Android are shown locked off.
- **Activity:** every send attempt with its status (sent / failed / skipped), recipient, rendered text and provider error.
- **Users:** shows who is reachable on which channel. Two demo helpers:
  - Fire any trigger for a user.
  - "Mark 8 days away", then "Run inactivity check now".
- **Channel setup:** live check of which provider keys are configured, plus setup steps.

**Website**

- Register / sign in / sign out / forgot password.
- Dashboard:
  - Add a WhatsApp number.
  - Turn on browser alerts (Web Push subscribe).
  - Place a demo order.
  - "Messages sent to you" feed.

**Reliability**

- Sending runs in a background thread, so login and logout stay fast.
- One failing channel never blocks the others.
- Missing keys or phone numbers are logged as *skipped* with a clear reason.
- Readable errors for common failures: expired Meta tokens, unapproved templates, and unsubscribed browsers.

---

## Environment variables

### Backend (Render) — see `backend/.env.example`

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon Postgres connection string (`postgresql://...?sslmode=require`). Empty = local SQLite |
| `DJANGO_SECRET_KEY`, `DEBUG` | Django basics (Render Blueprint generates the secret key) |
| `FRONTEND_URL` | Vercel URL — used for CORS and links inside messages |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_PHONE` | First admin account |
| `WHATSAPP_ACCESS_TOKEN` | Permanent System User token (expiry: Never). A 24h temporary token also works for a quick test |
| `PHONE_NUMBER_ID` | Meta test phone number ID |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | WABA ID — needed to create/sync templates from the admin panel |
| `EMAIL_PROVIDER` | `postmark` (default), `brevo`, `resend`, or `console` for local dev |
| `POSTMARKAPP_TOKEN`, `POSTMARK_FROM_EMAIL` | Postmark server token + verified sender |
| `BREVO_API_KEY`, `BREVO_FROM_EMAIL` / `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | Only if you switch provider |
| `ONESIGNAL_APP_ID`, `ONESIGNAL_REST_API_KEY` | OneSignal web app |
| `CRON_SECRET` | Protects `POST /api/cron/inactivity/` |

### Frontend (Vercel) — see `frontend/.env.example`

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Render backend URL, no trailing slash |
| `VITE_ONESIGNAL_APP_ID` | Same OneSignal App ID |

`.env` files are git-ignored. Never commit tokens.

---

## Run locally

Backend:

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_notifications
python manage.py runserver
```

Tip: set `EMAIL_PROVIDER=console` in `.env` to print emails in the terminal instead of sending them. With `DEBUG=True`, `localhost:5173` and `localhost:4173` are allowed by CORS automatically.

Frontend (new terminal):

```
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

Check that the real keys work (read-only; add `--phone` / `--email` to send one real test):

```
python manage.py verify_channels
python manage.py verify_channels --phone 919876543210 --email you@example.com
```

Tests (20 backend tests; provider HTTP calls are mocked):

```
cd backend
python manage.py test notifications
```

---

## Deploy

### Database → Neon (permanent free Postgres)

Render's free Postgres is deleted after 30 days (+14 days grace), so the database lives on Neon instead.

1. Sign up at neon.tech and create a project (pick the region closest to your Render region).
2. Copy the connection string (direct, not pooled) — it looks like `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`.
3. Use it as `DATABASE_URL` on Render. Tables are created automatically by `migrate` during the build.

### Backend → Render

1. Push the repo to GitHub.
2. In Render, go to **New → Blueprint** and pick the repo. `render.yaml` creates the web service.
3. Fill in the secret env vars Render asks for: `FRONTEND_URL`, admin details, WhatsApp, Postmark and OneSignal keys.
4. Wait for the build. `build.sh` runs collectstatic, migrate and seed.
5. Check that `https://<service>.onrender.com/api/health/` returns `{"status": "ok"}`.

The free Render plan sleeps after 15 minutes without traffic, so the first request can take up to a minute. To keep it awake, add a cron-job.org job that GETs `/api/health/` every 10 minutes (one always-on free service fits in Render's 750 free hours a month).

### Frontend → Vercel

1. **New Project**, pick the repo, and set **Root Directory** to `frontend`. Vercel detects Vite.
2. Add `VITE_API_URL` and `VITE_ONESIGNAL_APP_ID`, then deploy.
3. Copy the Vercel URL into `FRONTEND_URL` on Render and redeploy the backend.
4. In OneSignal, set the site URL to the same Vercel URL.

### Inactivity scheduler

"Not logged in for 1 day / 1 week" need a periodic check. Pick one:

- **Free:** create a job on cron-job.org that runs every hour. It should POST to `https://<service>.onrender.com/api/cron/inactivity/` with the header `X-Cron-Secret: <CRON_SECRET>`.
- **Render Cron Job (paid):** run `python manage.py check_inactivity` every hour.
- **Demo:** in the admin panel, go to **Users**, click **Mark 8 days away**, then **Run inactivity check now**.

Each inactivity trigger fires once per absence. It won't repeat until the user comes back and leaves again.

---

## Sandbox setup (no production keys)

**WhatsApp**

1. Create an app at developers.facebook.com (linked to a Meta business portfolio) and add the WhatsApp product.
2. On **API Setup**, copy the Phone number ID and the WhatsApp Business Account ID, and add your phone as a test recipient.
3. Create a **permanent token**: business.facebook.com → Settings → Users → **System users** → Add (role Admin) → **Assign assets**: your app and your WhatsApp account, both with full control → **Generate new token** → pick the app → expiry **Never** → permissions `whatsapp_business_messaging` and `whatsapp_business_management` (add `business_management` if Meta asks). Copy it once — Meta won't show it again.
4. Run `python manage.py verify_channels` — it should say *Token never expires*.

Meta only delivers **approved** templates. After saving a template in the admin panel, press **Sync** until it shows *Approved*. For an instant demo, tick "Use a template that already exists in Meta" and enter `hello_world`.

**Email (Postmark)**

1. Create a server and copy its Server API token.
2. Verify the sender signature.

While a Postmark account is pending approval, it only delivers to addresses on the sender's own domain. Brevo is the easier free option if you need to send to any inbox (`EMAIL_PROVIDER=brevo`).

**Web Push (OneSignal)**

1. Create a web app with Web only, and choose **Typical Site** with your Vercel URL.
2. Copy the App ID and REST API key.
3. On the site, press **Allow alerts** to subscribe your browser.

`frontend/public/OneSignalSDKWorker.js` is the required service worker.

---

## API overview

| Method | Path | Who |
|---|---|---|
| POST | `/api/auth/register/`, `/api/auth/login/`, `/api/auth/logout/` | public / user |
| GET, PATCH | `/api/auth/me/` | user |
| POST, DELETE | `/api/auth/push-subscription/` | user |
| POST | `/api/auth/password-reset/` | public |
| POST | `/api/events/order/` | user |
| GET | `/api/me/notifications/` | user |
| GET, POST, PATCH, DELETE | `/api/admin/triggers/` | admin |
| POST, PATCH, DELETE | `/api/admin/templates/` | admin |
| POST | `/api/admin/templates/{id}/toggle/`, `/test/`, `/sync/` | admin |
| GET | `/api/admin/logs/`, `/api/admin/users/`, `/api/admin/overview/`, `/api/admin/events/` | admin |
| POST | `/api/admin/users/{id}/fire/`, `/api/admin/users/{id}/simulate-inactive/`, `/api/admin/run-inactivity-check/` | admin |
| POST | `/api/cron/inactivity/` | cron (secret header) |
| GET | `/api/health/`, `/api/variables/` | public |

Auth is DRF token auth: `Authorization: Token <key>`.

---

## Project structure

```
backend/
  config/                 settings, urls
  accounts/               register/login/logout, profile (phone, push id, last_seen)
  notifications/
    models.py             Trigger, Template, TriggerEvent, NotificationLog
    dispatcher.py         fire_trigger() + per-channel delivery + logging
    inactivity.py         "not logged in for N days" scanner
    renderer.py           {{variables}} and WhatsApp positional mapping
    services/             whatsapp.py, email.py, webpush.py
    management/commands/  seed_notifications, check_inactivity
    tests.py
frontend/
  src/pages/              Landing, auth pages, user Dashboard
  src/pages/admin/        Matrix, TemplateEditor, TriggerForm, Activity, Users, Setup
  src/components/         UI kit, channel previews, push toggle
  src/push.js             OneSignal integration
render.yaml               Render blueprint
docs/                     Task D answers, video script
```
