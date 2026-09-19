# Task D — explained simply

**What is a trigger? Three examples.**

A trigger is anything that happens on the website that should send the user a message.

- **Order placed:** the user finishes a purchase.
- **Not logged in for 1 week:** the user hasn't visited for 7 days. Nobody clicks anything; a scheduled check notices it.
- **Password reset:** the user asks to reset their password.

Login and logout are triggers too. Each trigger is one row in the admin table.

**What are the three channels?**

- **WhatsApp:** a message on the user's WhatsApp, sent through the WhatsApp Cloud API.
- **Email:** an email in their inbox, sent through Postmark (or another transactional email API).
- **Web Push:** a pop-up notification in their browser, sent through OneSignal.

**Why create templates in the admin panel instead of on the Postmark or WhatsApp sites?**

- One place for everything: the admin sees every trigger and channel in one table.
- The admin doesn't need logins for three provider dashboards.
- The system knows which template belongs to which trigger.
- The system fills in variables like the user's name and order number.
- It keeps the on/off switches.
- It logs every send.
- Switching providers later (e.g. Postmark to Brevo) doesn't change the admin's workflow.
- For WhatsApp, the panel still submits the template to Meta for approval and syncs its status. The admin just never has to open Meta's site.

**What is Web Push?**

A notification the website sends to the browser. It pops up on the screen even when the site's tab isn't open.

- The user first clicks "Allow" once.
- The browser then gives us a subscription ID, and we send to that ID through OneSignal.
- In this project it is browser only. There are no mobile app notifications.
