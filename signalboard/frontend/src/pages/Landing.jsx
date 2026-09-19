import { Link } from "react-router-dom";
import { BellRing, Mail, MessageCircle, LogIn } from "lucide-react";
import { Logo } from "../components/ui.jsx";
import { useAuth } from "../auth.jsx";

const ROWS = [
  ["Login", true, true, true],
  ["Logout", true, true, false],
  ["Not logged in for 1 week", false, true, true],
  ["Order placed", true, true, true],
];

export default function Landing() {
  const { user } = useAuth();
  const home = user ? (user.is_staff ? "/admin" : "/app") : null;
  return (
    <div className="landing">
      <header className="top-bar">
        <Logo />
        <nav className="top-nav">
          {home ? (
            <Link className="btn btn-primary" to={home}>Open {user.is_staff ? "admin panel" : "dashboard"}</Link>
          ) : (
            <>
              <Link className="btn btn-ghost" to="/login">Sign in</Link>
              <Link className="btn btn-primary" to="/register">Create account</Link>
            </>
          )}
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <h1>Every website notification, run from one table.</h1>
          <p className="lede">
            When something happens on the site — a sign-in, an order, a week away — Signalboard sends
            the right message on WhatsApp, email and the browser. Admins write and switch every message
            here, without opening Meta, Postmark or OneSignal.
          </p>
          <div className="hero-cta">
            <Link className="btn btn-primary btn-lg" to={home || "/register"}>
              {home ? "Continue" : "Create an account"}
            </Link>
            {!home && <Link className="btn btn-ghost btn-lg" to="/login">I already have one</Link>}
          </div>
        </div>

        <div className="signal" aria-label="Example: one sign-in sends three messages">
          <div className="signal-event">
            <LogIn size={18} aria-hidden />
            <div>
              <strong>Riya signed in</strong>
              <small>Trigger: Login</small>
            </div>
          </div>
          <svg className="signal-wires" viewBox="0 0 60 300" preserveAspectRatio="none" aria-hidden>
            <path pathLength="1" d="M0 150 C 30 150, 30 52, 60 52" />
            <path pathLength="1" d="M0 150 L 60 150" />
            <path pathLength="1" d="M0 150 C 30 150, 30 248, 60 248" />
          </svg>
          <div className="signal-out">
            <div className="out out-wa">
              <MessageCircle size={16} aria-hidden />
              <p>Hi Riya, you just signed in to Signalboard at 10:30 AM.</p>
            </div>
            <div className="out out-mail">
              <Mail size={16} aria-hidden />
              <div>
                <strong>You signed in to Signalboard</strong>
                <p>Welcome back! You signed in using Chrome on Windows.</p>
              </div>
            </div>
            <div className="out out-push">
              <BellRing size={16} aria-hidden />
              <div>
                <strong>Welcome back, Riya!</strong>
                <p>You're signed in to Signalboard.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="band">
        <div className="band-inner">
          <div className="band-copy">
            <h2>The admin sees one table</h2>
            <p>
              Each row is something that happens on the website. Each column is a channel. Each cell is one
              message you can write, test and switch on or off.
            </p>
          </div>
          <div className="mini-matrix" role="table" aria-label="Example admin table">
            <div className="mm-row mm-head" role="row">
              <span role="columnheader">Trigger</span>
              <span role="columnheader">WhatsApp</span>
              <span role="columnheader">Email</span>
              <span role="columnheader">Browser</span>
            </div>
            {ROWS.map(([name, ...on]) => (
              <div className="mm-row" role="row" key={name}>
                <span role="cell">{name}</span>
                {on.map((v, i) => (
                  <span role="cell" key={i}>
                    <i className={`mm-dot ${v ? `mm-on-${i}` : ""}`} aria-label={v ? "on" : "off"} />
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="steps">
        <h2>How a message goes out</h2>
        <ol>
          <li>
            <h3>Something happens</h3>
            <p>A user signs in, signs out, places an order, or stays away for a day or a week.</p>
          </li>
          <li>
            <h3>Signalboard picks the messages</h3>
            <p>It looks up that trigger's row and fills in the user's name, time and order details.</p>
          </li>
          <li>
            <h3>Each channel delivers</h3>
            <p>WhatsApp Cloud API, Postmark and OneSignal send it. Every attempt is logged for the admin.</p>
          </li>
        </ol>
      </section>

      <footer className="site-foot">
        <Logo />
        <p className="muted">Notification system assignment · Django on Render · React on Vercel</p>
      </footer>
    </div>
  );
}
