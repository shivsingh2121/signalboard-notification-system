import { useOutletContext } from "react-router-dom";
import { CheckCircle2, CircleDashed } from "lucide-react";
import { API_URL } from "../../api.js";
import { ChannelIcon, Spinner } from "../../components/ui.jsx";

const GUIDES = {
  whatsapp: {
    title: "WhatsApp — Meta sandbox",
    steps: [
      "Create an app at developers.facebook.com and add the WhatsApp product.",
      "Open WhatsApp > API Setup. Copy the Phone number ID and WhatsApp Business Account ID.",
      "Add your own phone as a test recipient — only those numbers receive messages.",
      "Set WHATSAPP_ACCESS_TOKEN, PHONE_NUMBER_ID and WHATSAPP_BUSINESS_ACCOUNT_ID on Render.",
      "For a token that never expires: Business Settings > System users > Add (Admin) > Assign assets (your app + WhatsApp account, full control) > Generate new token > expiry Never, with whatsapp_business_messaging and whatsapp_business_management.",
    ],
  },
  email: {
    title: "Email — Postmark (or Brevo / Resend)",
    steps: [
      "Sign up at postmarkapp.com and open your server's API Tokens tab.",
      "Verify the sender email under Sender Signatures.",
      "Set POSTMARKAPP_TOKEN and POSTMARK_FROM_EMAIL. While the account is pending approval, Postmark only delivers to your own domain's addresses.",
      "To use Brevo or Resend instead, set EMAIL_PROVIDER=brevo or resend and that provider's key and sender.",
    ],
  },
  webpush: {
    title: "Web Push — OneSignal",
    steps: [
      "Create a free OneSignal app and choose Web only (skip Android and iOS).",
      "Pick Typical Site and enter your Vercel URL as the site URL.",
      "Set ONESIGNAL_APP_ID and ONESIGNAL_REST_API_KEY on Render, and VITE_ONESIGNAL_APP_ID on Vercel.",
      "Press Allow alerts at the top of this panel to subscribe your browser, then send a test.",
    ],
  },
};

export default function Setup() {
  const { overview } = useOutletContext();
  if (!overview) return <div className="page-loading"><Spinner /> Checking channels…</div>;
  const p = overview.providers;
  const detail = {
    whatsapp: p.whatsapp.configured
      ? p.whatsapp.templates_configured ? `Sending and template management ready (${p.whatsapp.api_version})` : "Can send, but WHATSAPP_BUSINESS_ACCOUNT_ID is missing — templates can't be created"
      : "Keys missing",
    email: p.email.configured ? `Using ${p.email.provider} from ${p.email.from}` : `Provider "${p.email.provider}" is missing its key or sender`,
    webpush: p.webpush.configured ? "OneSignal connected" : "Keys missing",
  };
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Channel setup</h1>
          <p className="muted">All keys live in the backend environment. Nobody needs to open the provider websites to write messages.</p>
        </div>
      </div>
      <div className="setup-grid">
        {Object.entries(GUIDES).map(([ch, g]) => (
          <section className="panel setup-card" key={ch}>
            <div className="setup-head">
              <ChannelIcon channel={ch} size={18} />
              <h2>{g.title}</h2>
            </div>
            <p className={`setup-state ${p[ch].configured ? "ok" : ""}`}>
              {p[ch].configured ? <CheckCircle2 size={16} aria-hidden /> : <CircleDashed size={16} aria-hidden />}
              {detail[ch]}
            </p>
            <ol>
              {g.steps.map((s) => <li key={s}>{s}</li>)}
            </ol>
          </section>
        ))}
        <section className="panel setup-card">
          <div className="setup-head"><h2>Inactivity scheduler</h2></div>
          <p className="muted">
            "Not logged in for 1 day / 1 week" need a check that runs on a schedule. Pick one:
          </p>
          <ol>
            <li>Render Cron Job (paid) running <code>python manage.py check_inactivity</code> every hour.</li>
            <li>
              Free: a cron-job.org job that POSTs to <code>{API_URL}/api/cron/inactivity/</code> hourly with header{" "}
              <code>X-Cron-Secret</code> set to your CRON_SECRET.
            </li>
            <li>For a demo: Users &gt; Mark 8 days away &gt; Run inactivity check now.</li>
          </ol>
        </section>
      </div>
    </div>
  );
}
