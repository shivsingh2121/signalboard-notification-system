import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "../auth.jsx";
import { api, fieldErrors } from "../api.js";
import { useToast } from "../toast.jsx";
import { Button, Field, Logo } from "../components/ui.jsx";

function AuthShell({ title, sub, children, foot }) {
  return (
    <div className="auth">
      <div className="auth-card">
        <Logo />
        <h1>{title}</h1>
        {sub && <p className="muted">{sub}</p>}
        {children}
        {foot && <div className="auth-foot">{foot}</div>}
      </div>
      <aside className="auth-aside" aria-hidden>
        <p>Signing in or out sends a message on every channel the admin has switched on.</p>
        <ul>
          <li><i className="dot dot-wa" /> WhatsApp</li>
          <li><i className="dot dot-mail" /> Email</li>
          <li><i className="dot dot-push" /> Browser alert</li>
        </ul>
      </aside>
    </div>
  );
}

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const toast = useToast();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login(form.email, form.password);
      toast("Signed in. Your Login messages are on their way.", "success");
      nav(loc.state?.from || (user.is_staff ? "/admin" : "/app"), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Sign in"
      sub="Use the email and password you registered with."
      foot={<>New here? <Link to="/register">Create an account</Link></>}
    >
      <form onSubmit={submit} className="form" noValidate>
        {error && <div className="alert alert-bad">{error}</div>}
        <Field label="Email" htmlFor="email">
          <input id="email" type="email" autoComplete="email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Password" htmlFor="password" aside={<Link to="/forgot-password" className="small-link">Forgot password?</Link>}>
          <input id="password" type="password" autoComplete="current-password" required value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        <Button type="submit" loading={busy} className="btn-block">Sign in</Button>
      </form>
    </AuthShell>
  );
}

export function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      await register(form);
      toast("Account created. Turn on browser alerts to get Web Push messages.", "success");
      nav("/app", { replace: true });
    } catch (err) {
      const fe = fieldErrors(err);
      setErrors(Object.keys(fe).length ? fe : { form: err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      sub="Add your WhatsApp number to receive WhatsApp messages."
      foot={<>Already registered? <Link to="/login">Sign in</Link></>}
    >
      <form onSubmit={submit} className="form" noValidate>
        {errors.form && <div className="alert alert-bad">{errors.form}</div>}
        <Field label="Full name" htmlFor="name" error={errors.name}>
          <input id="name" autoComplete="name" required value={form.name} onChange={set("name")} />
        </Field>
        <Field label="Email" htmlFor="email" error={errors.email}>
          <input id="email" type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        </Field>
        <Field label="WhatsApp number" htmlFor="phone" error={errors.phone}
          hint="With country code, e.g. 91 98765 43210. In sandbox mode it must be on Meta's test recipient list.">
          <input id="phone" type="tel" autoComplete="tel" inputMode="tel" value={form.phone} onChange={set("phone")} placeholder="91 98765 43210" />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password} hint="At least 6 characters.">
          <input id="password" type="password" autoComplete="new-password" required value={form.password} onChange={set("password")} />
        </Field>
        <Button type="submit" loading={busy} className="btn-block">Create account</Button>
      </form>
    </AuthShell>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api("/api/auth/password-reset/", { method: "POST", body: { email } });
      setDone(res.detail);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthShell
      title="Reset your password"
      sub="We'll send the reset link on every channel you have turned on. This fires the Password reset trigger."
      foot={<Link to="/login" className="back-link"><ArrowLeft size={14} /> Back to sign in</Link>}
    >
      {done ? (
        <div className="alert alert-ok">{done}</div>
      ) : (
        <form onSubmit={submit} className="form" noValidate>
          {error && <div className="alert alert-bad">{error}</div>}
          <Field label="Email" htmlFor="email">
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Button type="submit" loading={busy} className="btn-block">Send reset link</Button>
        </form>
      )}
    </AuthShell>
  );
}
