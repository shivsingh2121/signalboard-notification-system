import { BellRing, Globe } from "lucide-react";

export const renderVars = (text, vars) =>
  (text || "").replace(/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g, (_, v) => (vars[v] !== undefined ? vars[v] : `{{${v}}}`));

export function WhatsAppPreview({ header, body, footer, time = "10:30" }) {
  return (
    <div className="pv-wa">
      <div className="pv-wa-top">
        <span className="pv-wa-avatar">S</span>
        <div>
          <strong>Signalboard</strong>
          <small>Business account</small>
        </div>
      </div>
      <div className="pv-wa-chat">
        <div className="pv-wa-bubble">
          {header && <p className="pv-wa-header">{header}</p>}
          <p className="pv-wa-body">{body || <em className="muted">Your message appears here</em>}</p>
          {footer && <p className="pv-wa-footer">{footer}</p>}
          <span className="pv-wa-time">{time}</span>
        </div>
      </div>
    </div>
  );
}

export function EmailPreview({ subject, body, ctaLabel, from = "notifications@signalboard.dev" }) {
  return (
    <div className="pv-mail">
      <div className="pv-mail-meta">
        <div><span className="muted">From</span> Signalboard &lt;{from}&gt;</div>
        <div className="pv-mail-subject">{subject || <em className="muted">Subject line</em>}</div>
      </div>
      <div className="pv-mail-card">
        <div className="pv-mail-brand">Signalboard</div>
        <div className="pv-mail-content">
          {(body || "").split(/\n\n+/).filter(Boolean).map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          {!body && <p className="muted"><em>Email body</em></p>}
          {ctaLabel && <span className="pv-mail-btn">{ctaLabel}</span>}
        </div>
      </div>
    </div>
  );
}

export function PushPreview({ title, body, url }) {
  let host = "signalboard.vercel.app";
  try {
    if (url) host = new URL(url).host;
  } catch {
    /* keep default */
  }
  return (
    <div className="pv-push">
      <div className="pv-push-card">
        <div className="pv-push-app">
          <Globe size={13} aria-hidden /> Chrome · {host}
        </div>
        <div className="pv-push-row">
          <span className="pv-push-icon"><BellRing size={18} /></span>
          <div>
            <strong>{title || <em className="muted">Title</em>}</strong>
            <p>{body || <em className="muted">Message</em>}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
