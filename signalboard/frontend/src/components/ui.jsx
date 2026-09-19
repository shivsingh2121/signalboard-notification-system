import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { BellRing, Mail, MessageCircle, X, Loader2 } from "lucide-react";

export const CHANNELS = [
  { key: "whatsapp", label: "WhatsApp", short: "WhatsApp", Icon: MessageCircle },
  { key: "email", label: "Email", short: "Email", Icon: Mail },
  { key: "webpush", label: "Web Push", short: "Browser", Icon: BellRing },
];
export const channelMeta = (key) => CHANNELS.find((c) => c.key === key) || CHANNELS[0];

export function ChannelIcon({ channel, size = 16 }) {
  const { Icon, label } = channelMeta(channel);
  return (
    <span className={`ch-icon ch-${channel}`} title={label}>
      <Icon size={size} aria-hidden />
    </span>
  );
}

export function Logo({ to = "/", light = false }) {
  return (
    <Link to={to} className={`logo ${light ? "logo-light" : ""}`} aria-label="Signalboard home">
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="8" fill="currentColor" />
        <circle cx="10" cy="11" r="3" fill="#1f9d57" />
        <circle cx="16" cy="16" r="3" fill="#2f6fdb" />
        <circle cx="22" cy="21" r="3" fill="#e0a02a" />
      </svg>
      <span>Signalboard</span>
    </Link>
  );
}

export function Spinner({ size = 16 }) {
  return <Loader2 size={size} className="spin" aria-hidden />;
}

export function Button({ children, variant = "primary", size, loading, icon: Icon, className = "", ...rest }) {
  return (
    <button
      className={`btn btn-${variant} ${size ? `btn-${size}` : ""} ${className}`}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading ? <Spinner /> : Icon ? <Icon size={16} aria-hidden /> : null}
      {children && <span>{children}</span>}
    </button>
  );
}

export function Switch({ checked, onChange, label, disabled, size }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={`switch ${checked ? "on" : ""} ${size === "sm" ? "switch-sm" : ""}`}
      onClick={() => !disabled && onChange(!checked)}
    >
      <span className="knob" />
    </button>
  );
}

export function Field({ label, hint, error, children, htmlFor, aside }) {
  return (
    <div className={`field ${error ? "has-error" : ""}`}>
      <div className="field-top">
        {label && <label htmlFor={htmlFor}>{label}</label>}
        {aside}
      </div>
      {children}
      {error ? <p className="field-error">{error}</p> : hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  );
}

export function Sheet({ open, onClose, title, subtitle, children, footer, wide }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`sheet ${wide ? "sheet-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <header className="sheet-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </header>
        <div className="sheet-body">{children}</div>
        {footer && <footer className="sheet-foot">{footer}</footer>}
      </div>
    </div>
  );
}

const STATUS_TONE = {
  sent: "ok", APPROVED: "ok",
  failed: "bad", REJECTED: "bad", ERROR: "bad", DISABLED: "bad",
  skipped: "warn", PENDING: "warn", PAUSED: "warn",
  DRAFT: "idle",
};
export function Pill({ status, children }) {
  return <span className={`pill pill-${STATUS_TONE[status] || "idle"}`}>{children || status}</span>;
}

export function timeAgo(iso) {
  if (!iso) return "never";
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  const d = Math.round(s / 86400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}

export function Empty({ icon: Icon, title, children, action }) {
  return (
    <div className="empty">
      {Icon && <Icon size={28} aria-hidden />}
      <h3>{title}</h3>
      {children && <p className="muted">{children}</p>}
      {action}
    </div>
  );
}
