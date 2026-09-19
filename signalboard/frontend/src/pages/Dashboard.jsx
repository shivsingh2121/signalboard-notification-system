import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { KeyRound, LogOut, Pencil, RefreshCw, Settings2, ShoppingBag, Inbox } from "lucide-react";
import { api, fieldErrors } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useToast } from "../toast.jsx";
import PushToggle from "../components/PushToggle.jsx";
import { Button, ChannelIcon, Empty, Field, Logo, Pill, Sheet, timeAgo } from "../components/ui.jsx";

function PhoneSheet({ open, onClose }) {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [phone, setPhone] = useState(user?.phone || "");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => setPhone(user?.phone || ""), [user, open]);
  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      setUser(await api("/api/auth/me/", { method: "PATCH", body: { phone } }));
      toast("WhatsApp number saved.", "success");
      onClose();
    } catch (e) {
      setErr(fieldErrors(e).phone || e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Sheet open={open} onClose={onClose} title="WhatsApp number"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save}>Save number</Button></>}>
      <Field label="Number with country code" htmlFor="ph" error={err}
        hint="Sandbox rule: Meta only delivers to numbers added as test recipients in the Meta app.">
        <input id="ph" type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="91 98765 43210" />
      </Field>
    </Sheet>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [feed, setFeed] = useState([]);
  const [loadingFeed, setLoadingFeed] = useState(true);
  const [ordering, setOrdering] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [phoneOpen, setPhoneOpen] = useState(false);
  const poll = useRef(null);

  const loadFeed = useCallback(async () => {
    try {
      setFeed(await api("/api/me/notifications/"));
    } catch {
      /* feed is best effort */
    } finally {
      setLoadingFeed(false);
    }
  }, []);

  // Notifications are sent in the background — poll briefly after an action.
  const watch = useCallback(() => {
    clearInterval(poll.current);
    let n = 0;
    poll.current = setInterval(() => {
      loadFeed();
      if (++n >= 8) clearInterval(poll.current);
    }, 2500);
  }, [loadFeed]);

  useEffect(() => {
    loadFeed();
    watch();
    return () => clearInterval(poll.current);
  }, [loadFeed, watch]);

  const order = async () => {
    setOrdering(true);
    try {
      const r = await api("/api/events/order/", { method: "POST", body: {} });
      toast(`Order ${r.order_id} placed. Order placed messages are on their way.`, "success");
      watch();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setOrdering(false);
    }
  };

  const signOut = async () => {
    setLeaving(true);
    await logout().catch(() => {});
    toast("Signed out. Logout messages are on their way.", "success");
    nav("/login");
  };

  const reach = [
    { ch: "whatsapp", label: "WhatsApp", value: user.phone ? `+${user.phone}` : "No number yet", ok: Boolean(user.phone),
      action: <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setPhoneOpen(true)}>{user.phone ? "Change" : "Add number"}</Button> },
    { ch: "email", label: "Email", value: user.email, ok: true },
    { ch: "webpush", label: "Browser alerts", value: user.push_subscribed ? "On in this browser" : "Off", ok: user.push_subscribed,
      action: <PushToggle compact /> },
  ];

  return (
    <div className="app-shell">
      <header className="top-bar">
        <Logo to="/app" />
        <nav className="top-nav">
          {user.is_staff && <Link className="btn btn-ghost" to="/admin"><Settings2 size={16} /> <span>Admin panel</span></Link>}
          <Button variant="ghost" icon={LogOut} loading={leaving} onClick={signOut}>Sign out</Button>
        </nav>
      </header>

      <main className="dash">
        <section className="dash-hello">
          <h1>Hi {user.name.split(" ")[0]}</h1>
          <p className="lede">This is the website side. Everything you do here can fire a trigger, and the admin decides what message it sends.</p>
        </section>

        <section className="panel">
          <h2>Where we can reach you</h2>
          <ul className="reach">
            {reach.map((r) => (
              <li key={r.ch} className={r.ok ? "is-ok" : ""}>
                <ChannelIcon channel={r.ch} size={18} />
                <div className="reach-text">
                  <strong>{r.label}</strong>
                  <span className="muted">{r.value}</span>
                </div>
                {r.action}
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <h2>Do something that sends a message</h2>
          <div className="actions-grid">
            <button className="action-tile" onClick={order} disabled={ordering}>
              <ShoppingBag size={22} aria-hidden />
              <strong>Place a demo order</strong>
              <span className="muted">Fires <b>Order placed</b></span>
            </button>
            <button className="action-tile" onClick={signOut} disabled={leaving}>
              <LogOut size={22} aria-hidden />
              <strong>Sign out</strong>
              <span className="muted">Fires <b>Logout</b></span>
            </button>
            <Link className="action-tile" to="/forgot-password">
              <KeyRound size={22} aria-hidden />
              <strong>Forgot password</strong>
              <span className="muted">Fires <b>Password reset</b></span>
            </Link>
          </div>
          <p className="muted small">Signing in fires <b>Login</b>. Staying away for a day or a week fires the inactivity triggers.</p>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Messages sent to you</h2>
            <Button variant="ghost" size="sm" icon={RefreshCw} onClick={loadFeed}>Refresh</Button>
          </div>
          {loadingFeed ? (
            <p className="muted">Loading…</p>
          ) : feed.length === 0 ? (
            <Empty icon={Inbox} title="Nothing sent yet">Place a demo order or sign out and back in — the messages will show up here.</Empty>
          ) : (
            <ul className="feed">
              {feed.map((n) => (
                <li key={n.id}>
                  <ChannelIcon channel={n.channel} />
                  <div className="feed-main">
                    <div className="feed-line">
                      <strong>{n.trigger_name}</strong>
                      <Pill status={n.status} />
                    </div>
                    <p>{n.rendered_title ? `${n.rendered_title} — ` : ""}{n.rendered_body}</p>
                    {n.error && <p className="feed-err">{n.error}</p>}
                  </div>
                  <time className="muted small">{timeAgo(n.created_at)}</time>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
      <PhoneSheet open={phoneOpen} onClose={() => setPhoneOpen(false)} />
    </div>
  );
}
