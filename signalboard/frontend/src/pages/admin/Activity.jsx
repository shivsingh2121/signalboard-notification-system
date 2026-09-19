import { useCallback, useEffect, useState } from "react";
import { History, RefreshCw } from "lucide-react";
import { api } from "../../api.js";
import { Button, CHANNELS, ChannelIcon, Empty, Pill, Spinner, timeAgo } from "../../components/ui.jsx";

export default function Activity() {
  const [logs, setLogs] = useState(null);
  const [filters, setFilters] = useState({ channel: "", status: "", q: "" });
  const [open, setOpen] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const qs = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString();
    try {
      setLogs(await api(`/api/admin/logs/${qs ? `?${qs}` : ""}`));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const t = setTimeout(load, filters.q ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, filters.q]);

  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Activity</h1>
          <p className="muted">Every message the system tried to send, newest first.</p>
        </div>
        <Button variant="ghost" icon={RefreshCw} loading={loading} onClick={load}>Refresh</Button>
      </div>

      <div className="filters">
        <select value={filters.channel} onChange={set("channel")} aria-label="Channel">
          <option value="">All channels</option>
          {CHANNELS.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
        <select value={filters.status} onChange={set("status")} aria-label="Status">
          <option value="">Any result</option>
          <option value="sent">Sent</option>
          <option value="failed">Failed</option>
          <option value="skipped">Skipped</option>
        </select>
        <input type="search" placeholder="Search email or number" value={filters.q} onChange={set("q")} aria-label="Search" />
      </div>

      {!logs ? (
        <div className="page-loading"><Spinner /> Loading activity…</div>
      ) : logs.length === 0 ? (
        <Empty icon={History} title="No messages yet">Sign in on the website or send a test from Notification settings.</Empty>
      ) : (
        <ul className="log-list">
          {logs.map((l) => (
            <li key={l.id} className={open === l.id ? "open" : ""}>
              <button className="log-row" onClick={() => setOpen(open === l.id ? null : l.id)} aria-expanded={open === l.id}>
                <ChannelIcon channel={l.channel} />
                <span className="log-trigger">
                  <strong>{l.trigger_name}</strong>
                  {l.is_test && <span className="tag">Test</span>}
                </span>
                <span className="log-to muted">{l.recipient || l.user_email || "—"}</span>
                <Pill status={l.status} />
                <time className="muted small">{timeAgo(l.created_at)}</time>
              </button>
              {open === l.id && (
                <div className="log-detail">
                  {l.rendered_title && <p><b>{l.rendered_title}</b></p>}
                  <p className="pre">{l.rendered_body}</p>
                  {l.error && <p className="feed-err">{l.error}</p>}
                  <p className="muted small">
                    User: {l.user_email || "—"} {l.provider_message_id && <>· Provider id: <code>{l.provider_message_id}</code></>} · {new Date(l.created_at).toLocaleString()}
                  </p>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
