# Walkthrough video script (~6–8 min)

Record with Loom or OBS. Keep WhatsApp Web (or your phone on screen), your email inbox and the site visible. Share the link as unlisted.

**Before recording**

- Render and Vercel are both deployed.
- Open the backend `/api/health/` once so the free Render instance is awake.
- At least one WhatsApp template is **Approved**. Press Sync, or link `hello_world`.
- Your admin browser has **Allow alerts** on.
- Close the other tabs.

**1. Intro (30 s)**

"This is Signalboard, a notification system. Django backend on Render, React frontend on Vercel. When something happens on the website, it sends messages on WhatsApp, Email and Web Push. The admin controls everything from one table."

**2. Admin login and the table (1 min)**

1. Sign in as admin.
2. Show the matrix: "Rows are triggers, columns are channels, and each cell is one template."
3. Point out the stats and the channel status banner.
4. Open **Channel setup** and show that all three providers say *connected*.

**3. Create or edit a template (1.5 min)**

1. Open the **Login** row's Email cell.
2. Edit the subject and insert `{{first_name}}` with a variable chip. Show the live preview.
3. Click **Save changes**.
4. Click **Send test** and show the email arriving.
5. Open the WhatsApp cell. Show the Meta template name, category and status, press **Sync**, and show *Approved*.
6. Explain: "Saving submits the template to Meta from here, and `{{first_name}}` is mapped to Meta's `{{1}}`."
7. Send a test and show the phone.
8. Open the Web Push cell. Show iOS and Android locked off, send a test, and show the browser pop-up.

**4. Toggle (30 s)**

Turn **Logout → Email** off and on again. "An off channel is simply skipped."

**5. Fire every trigger as a real user (2–3 min)**

1. In an incognito window, register a user with your WhatsApp test number.
2. Click **Turn on browser alerts** and allow.
3. **Login:** sign out, then sign back in. Show WhatsApp, email and the browser pop-up.
4. **Order placed:** click **Place a demo order** and show the three messages. Point at the "Messages sent to you" feed.
5. **Logout:** click **Sign out** and show the three messages.
6. **Password reset:** use Forgot password and show the messages.
7. **Inactivity:** back in admin, go to **Users**, click **Mark 8 days away**, then **Run inactivity check now**. Show the "we miss you" messages. Mention that production runs this hourly through a cron.

**6. Activity log (30 s)**

Open **Activity**, filter by channel, and expand a row to show the rendered text and provider id. Show a *skipped* or *failed* row and its reason if there is one.

**7. Wrap up (20 s)**

"Two repos folders, backend and frontend, with a README covering admin login, triggers and env vars. Thanks!"
