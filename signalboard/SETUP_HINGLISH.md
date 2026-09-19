# Setup guide (Hinglish): permanent keys, database, local run

Order: **1 local chalao → 2 permanent keys → 3 local pe verify → 4 Neon DB → 5 Render → 6 Vercel → 7 video**

---

## 1. Apne system pe chalao (DB setup ki zarurat nahi)

Local pe koi database install nahi karna. `DATABASE_URL` khali ho to Django apne aap `backend/db.sqlite3` file bana leta hai.

Requirements: Python 3.11+ aur Node 18+.

```
python3 --version
node --version
```

### Terminal 1: backend

```
cd signalboard/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Ab `backend/.env` kholo aur shuru mein sirf ye 4 lines aise set karo:

```
DEBUG=True
DATABASE_URL=
FRONTEND_URL=http://localhost:5173
EMAIL_PROVIDER=console
```

`EMAIL_PROVIDER=console` ka matlab hai ki email bheje nahi jaate, terminal mein print hote hain.

Phir ye commands chalao:

```
python manage.py migrate
python manage.py seed_notifications
python manage.py test notifications
python manage.py runserver
```

- `migrate` tables banata hai.
- `seed_notifications` admin user aur 6 triggers banata hai.
- `test` ke end mein "Ran 20 tests ... OK" aana chahiye.

Check karne ke liye naye tab mein ye chalao. Jawab mein `{"status":"ok"}` aana chahiye.

```
curl http://127.0.0.1:8000/api/health/
```

### Terminal 2: frontend

```
cd signalboard/frontend
npm install
cp .env.example .env
npm run dev
```

`frontend/.env` mein `VITE_API_URL=http://localhost:8000` hona chahiye.

### Browser mein check karo

1. http://localhost:5173 kholo, phir **Sign in** karo: `admin@signalboard.dev` / `Admin@12345`.
2. Admin table dikhni chahiye jisme 6 rows aur 3 channel columns hon.
3. Kisi Email cell pe click karo, text badlo, **Save changes** dabao, phir **Send test**. Terminal 1 mein email print hona chahiye.
4. Naye incognito window mein **Create account** karo, phir **Place a demo order**, phir **Sign out**. Har baar Terminal 1 mein email print hoga.
5. Admin panel ke **Activity** page pe saari entries dikhengi.

Yahan tak chal gaya to code sahi hai. Ab real channels jodte hain.

---

## 2. Permanent keys (hamesha ke liye)

| Channel | Expire hota hai? |
|---|---|
| WhatsApp System User token | Nahi, expiry "Never" |
| Postmark server token | Nahi |
| Brevo API key | Nahi |
| OneSignal App ID + REST API key | Nahi (jab tak khud delete na karo) |

### WhatsApp: permanent token

**Step A: app banao**
1. developers.facebook.com → My Apps → Create App → Business type.
2. App ko ek **Business portfolio** se link karo. Na ho to wahin naya bana lo.
3. App mein **WhatsApp** product add karo.
4. WhatsApp → **API Setup** page se do cheezein copy karo:
   - Phone number ID → `PHONE_NUMBER_ID`
   - WhatsApp Business Account ID → `WHATSAPP_BUSINESS_ACCOUNT_ID`
5. Usi page pe "To" mein apna WhatsApp number add karke verify karo. Test mode mein sirf wahi numbers message receive karte hain.

**Step B: permanent token banao**
1. business.facebook.com → Settings (gear icon) → Users → **System users** → **Add**.
2. Naam kuch bhi do (jaise `signalboard-bot`), role **Admin** rakho, Create karo.
3. Us system user pe **Assign assets** karo:
   - Apps → apni app → **Full control**
   - WhatsApp accounts → apna WhatsApp account → **Full control**
4. **Generate new token** dabao:
   - apni app select karo
   - Token expiration: **Never**
   - Permissions: `whatsapp_business_messaging` aur `whatsapp_business_management`. Meta `business_management` maange to wo bhi tick kar do.
5. Token turant copy karo, Meta dobara nahi dikhata. Ye `EAA...` se shuru hota hai aur `WHATSAPP_ACCESS_TOKEN` mein jaayega.

Ye token tabhi band hoga jab tum khud revoke karo ya system user delete karo.

### Email

**Option 1: Postmark**
1. postmarkapp.com → Server banao → API Tokens → Server token copy karo → `POSTMARKAPP_TOKEN`.
2. Sender Signatures mein apna email verify karo → `POSTMARK_FROM_EMAIL`.
3. Dhyan do: account approve hone tak Postmark sirf sender ke apne domain wale addresses pe hi deliver karta hai.

**Option 2: Brevo** (kisi bhi Gmail pe bhejna ho to ye easy hai)
1. brevo.com → SMTP & API → API Keys → key banao → `BREVO_API_KEY`.
2. Senders mein apna email verify karo → `BREVO_FROM_EMAIL`.
3. `.env` mein `EMAIL_PROVIDER=brevo` set karo.

### OneSignal (Web Push)

Do apps banao: ek local ke liye, ek Vercel ke liye. Site URL alag hota hai, isliye alag app chahiye.

1. onesignal.com → New App → **Web** → **Typical Site**.
2. Site URL daalo:
   - local app: `http://localhost:5173`, aur "treat HTTP localhost as HTTPS" wala option ON karo
   - live app: apna Vercel URL
3. Settings → **Keys & IDs** se copy karo:
   - App ID → backend ke `ONESIGNAL_APP_ID` aur frontend ke `VITE_ONESIGNAL_APP_ID`, dono mein same
   - REST API key → `ONESIGNAL_REST_API_KEY`

---

## 3. Local pe real keys verify karo

`backend/.env` mein saari keys bhar do. `EMAIL_PROVIDER` ko `postmark` ya `brevo` kar do.

Phir server rok ke (Ctrl+C) ye chalao. Ye sirf read-only check hai, kuch bhejta nahi:

```
python manage.py verify_channels
```

Output kuch aisa aana chahiye:

```
WhatsApp Cloud API
  ✔ Token works — sending from +1 555 ...
  ✔ Token never expires (System User token) ✅
  ✔ Can read templates — ... approved: hello_world
Email (postmark)
  ✔ API key works — sender you@...
Web Push (OneSignal)
  ✔ App ID + REST API key accepted
All checks passed.
```

Real message bhej ke dekhna ho to apna number aur email daalo:

```
python manage.py verify_channels --phone 919876543210 --email tumhara@gmail.com
```

Is command se phone pe WhatsApp ka `hello_world` message aayega aur inbox mein test email aayega.

Koi ✘ aaye to uske saath likha reason padho, wahi fix batata hai. Samajh na aaye to output mujhe paste kar do.

Phir `python manage.py runserver` karke browser mein ye check karo:
- Top pe **Allow alerts** dabao, phir kisi Web Push cell pe **Send test**. Browser pop-up aana chahiye.
- WhatsApp cell mein toggle ON karo aur Save. Template Meta ko submit ho jaayega. **Sync** dabate raho jab tak "Approved" na dikhe, phir **Send test**.

---

## 4. Database hamesha ke liye: Neon

**Render ka free Postgres 30 din baad expire hota hai.** Uske 14 din baad data delete ho jaata hai. Isliye DB Neon pe rakhenge, uska free tier expire nahi hota.

1. neon.tech pe signup karo (GitHub login chalega) → **Create project**.
   - Postgres version default rakho.
   - Region wahi lo jo Render service ka hai, jaise Singapore ya US.
2. Dashboard → **Connect** → connection string copy karo. **Pooled connection wala toggle OFF** rakhna. String aisi dikhegi:
   ```
   postgresql://neondb_owner:xxxx@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
3. Yahi string Render pe `DATABASE_URL` mein jaayegi. Tables Render build ke waqt `migrate` se apne aap ban jaayengi, manually kuch nahi banana.

Optional: local se bhi Neon wala DB use karna ho to `backend/.env` mein `DATABASE_URL=` ke aage yahi string daal do aur ye chalao:

```
python manage.py migrate
python manage.py seed_notifications
python manage.py verify_channels
```

Output mein "Database ✔ Connected (postgresql, ep-xxxx...)" aana chahiye.

---

## 5. Render (backend)

1. Code GitHub pe push karo. `.env` push nahi hogi kyunki wo gitignore mein hai.
2. render.com → **New → Blueprint** → repo select karo.
3. Render jo env vars maange, wo bhar do:
   - `DATABASE_URL`: Neon string
   - `FRONTEND_URL`: abhi `http://localhost:5173` daal do, Vercel ke baad update karna
   - `ADMIN_EMAIL`, `ADMIN_PASSWORD` (strong rakhna), `ADMIN_PHONE`
   - WhatsApp ki teen keys, Postmark/Brevo ki keys, OneSignal ki do keys
4. Deploy hone ke baad ye khulna chahiye aur `ok` dikhna chahiye: `https://<service>.onrender.com/api/health/`
5. Render → apni service → **Shell** tab mein bhi ye command chala sakte ho:
   ```
   python manage.py verify_channels
   ```

**Server ko jagaye rakhna:** free Render service 15 minute bina traffic ke so jaati hai.
1. cron-job.org pe free account banao.
2. Job 1: har 10 minute pe GET `https://<service>.onrender.com/api/health/`. Isse server jaaga rahega.
3. Job 2: har ghante POST `https://<service>.onrender.com/api/cron/inactivity/`, header `X-Cron-Secret` ke saath. Isse "not logged in" wale triggers chalenge. `CRON_SECRET` ki value Render → Environment mein dikhegi.

---

## 6. Vercel (frontend)

1. vercel.com → Add New Project → repo → **Root Directory: `frontend`**.
2. Env vars daalo:
   - `VITE_API_URL=https://<service>.onrender.com` (end mein slash nahi)
   - `VITE_ONESIGNAL_APP_ID`: live wale OneSignal app ki ID
3. Deploy karo, phir jo Vercel URL mile use do jagah daalo:
   - Render ke `FRONTEND_URL` mein, uske baad Render service redeploy karo
   - live OneSignal app ke Site URL mein

---

## 7. Final live check → video

1. Vercel URL pe admin login karo. **Channel setup** page pe teeno channel ✔ dikhne chahiye.
2. Script `docs/VIDEO_SCRIPT.md` mein hai. Task D ke answers `docs/TASK_D_ANSWERS.md` mein hain. Unhe apne words mein bolna, padhna nahi.

## Common problems

| Problem | Fix |
|---|---|
| Frontend pe "Can't reach the server" | Render so raha tha, 1 minute ruko. Ya `VITE_API_URL` galat hai. |
| Browser console mein CORS error | Render ka `FRONTEND_URL` exactly Vercel URL hona chahiye (https ke saath, end mein slash nahi) |
| WhatsApp: "not approved" | Admin mein **Sync** dabao. Jaldi chahiye to `hello_world` link karo. |
| WhatsApp: message nahi aaya | Number Meta API Setup mein test recipient list mein add hai? |
| Email nahi aaya | Spam folder dekho. Postmark ka account abhi pending hai to Brevo use karo. |
| Push nahi aaya | OneSignal ka Site URL exactly Vercel URL ho, aur browser mein notifications allowed hon |
