import { useCallback, useEffect, useState } from "react";
import { BellRing, Clock, Moon, Play, Users as UsersIcon } from "lucide-react";
import { api } from "../../api.js";
import { useToast } from "../../toast.jsx";
import { Button, Empty, Spinner, timeAgo } from "../../components/ui.jsx";

function UserRow({ u, triggers, onUpdated }) {
  const toast = useToast();
  const [trig, setTrig] = useState("");
  const [busy, setBusy] = useState("");

  const fire = async () => {
    if (!trig) return;
    setBusy("fire");
    try {
      const res = await api(`/api/admin/users/${u.id}/fire/`, { method: "POST", body: { trigger: trig } });
      const summary = res.results.map((r) => `${r.channel}: ${r.status}`).join(", ") || "no messages are switched on";
      toast(`Fired for ${u.email} — ${summary}.`, res.results.some((r) => r.status !== "sent") ? "info" : "success", 8000);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy("");
    }
  };

  const away = async () => {
    setBusy("away");
    try {
      onUpdated(await api(`/api/admin/users/${u.id}/simulate-inactive/`, { method: "POST", body: { days: 8 } }));
      toast(`${u.email} now looks 8 days inactive. Run the inactivity check to fire the triggers.`, "success", 7000);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy("");
    }
  };

  return (
    <li className="user-row">
      <div className="user-id">
        <span className="avatar">{u.name[0]?.toUpperCase()}</span>
        <div>
          <strong>{u.name} {u.is_staff && <span className="tag">Admin</span>}</strong>
          <small className="muted">{u.email}</small>
        </div>
      </div>
      <div className="user-reach">
        <span className={u.phone ? "ok" : ""} title="WhatsApp number">{u.phone ? `+${u.phone}` : "No WhatsApp"}</span>
        <span className={u.push_subscribed ? "ok" : ""}><BellRing size={12} aria-hidden /> {u.push_subscribed ? "Alerts on" : "Alerts off"}</span>
        <span><Clock size={12} aria-hidden /> Seen {timeAgo(u.last_seen)}</span>
      </div>
      <div className="user-actions">
        <select value={trig} onChange={(e) => setTrig(e.target.value)} aria-label={`Trigger to fire for ${u.email}`}>
          <option value="">Fire a trigger…</option>
          {triggers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <Button size="sm" variant="secondary" icon={Play} disabled={!trig} loading={busy === "fire"} onClick={fire}>Fire</Button>
        <Button size="sm" variant="ghost" icon={Moon} loading={busy === "away"} onClick={away}>Mark 8 days away</Button>
      </div>
    </li>
  );
}

export default function Users() {
  const toast = useToast();
  const [users, setUsers] = useState(null);
  const [triggers, setTriggers] = useState([]);
  const [running, setRunning] = useState(false);

  const load = useCallback(() => api("/api/admin/users/").then(setUsers), []);
  useEffect(() => {
    load();
    api("/api/admin/triggers/").then(setTriggers).catch(() => {});
  }, [load]);

  const runCheck = async () => {
    setRunning(true);
    try {
      const { fired } = await api("/api/admin/run-inactivity-check/", { method: "POST" });
      toast(fired.length ? `Fired ${fired.length} inactivity trigger(s): ${fired.map((f) => `${f.trigger} → ${f.user}`).join(", ")}` : "Nobody is due an inactivity message right now.", fired.length ? "success" : "info", 9000);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Users</h1>
          <p className="muted">Check who can be reached, and fire any trigger for a demo.</p>
        </div>
        <Button variant="secondary" icon={Clock} loading={running} onClick={runCheck}>Run inactivity check now</Button>
      </div>
      <p className="muted small note">
        The inactivity check also runs on a schedule (see Channel setup). It sends each "not logged in" message once per absence.
      </p>
      {!users ? (
        <div className="page-loading"><Spinner /> Loading users…</div>
      ) : users.length === 0 ? (
        <Empty icon={UsersIcon} title="No users yet">Users appear here after they create an account on the website.</Empty>
      ) : (
        <ul className="user-list">
          {users.map((u) => (
            <UserRow key={u.id} u={u} triggers={triggers}
              onUpdated={(nu) => setUsers((us) => us.map((x) => (x.id === nu.id ? nu : x)))} />
          ))}
        </ul>
      )}
    </div>
  );
}
