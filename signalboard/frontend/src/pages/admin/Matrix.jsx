import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { AlertTriangle, Clock, Pencil, Plus, RefreshCw, Send, Trash2, Zap } from "lucide-react";
import { api } from "../../api.js";
import { useToast } from "../../toast.jsx";
import { Button, CHANNELS, ChannelIcon, Empty, Pill, Spinner, Switch, timeAgo } from "../../components/ui.jsx";
import TemplateEditor from "./TemplateEditor.jsx";
import TriggerForm from "./TriggerForm.jsx";

function Cell({ trigger, channel, tpl, provider, onOpen, onChange }) {
  const toast = useToast();
  const [busy, setBusy] = useState("");
  const label = CHANNELS.find((c) => c.key === channel).label;

  if (!tpl) {
    return (
      <div className="cell cell-empty" role="cell">
        <span className="cell-ch"><ChannelIcon channel={channel} size={14} /> {label}</span>
        <button className="create-btn" onClick={onOpen}>
          <Plus size={16} aria-hidden /> Create template
        </button>
      </div>
    );
  }

  const run = async (what, fn) => {
    setBusy(what);
    try {
      await fn();
    } finally {
      setBusy("");
    }
  };

  const toggle = (v) =>
    run("toggle", async () => {
      try {
        onChange(await api(`/api/admin/templates/${tpl.id}/toggle/`, { method: "POST", body: { enabled: v } }));
        toast(`${trigger.name} on ${label} is ${v ? "on" : "off"}.`, "success", 2500);
      } catch (e) {
        toast(e.message, "error");
      }
    });

  const test = () =>
    run("test", async () => {
      try {
        const res = await api(`/api/admin/templates/${tpl.id}/test/`, { method: "POST", body: {} });
        toast(`Test sent to ${res.recipient}.`, "success");
      } catch (e) {
        toast(e.data?.error || e.message, "error", 10000);
      }
    });

  const sync = () =>
    run("sync", async () => {
      try {
        const s = await api(`/api/admin/templates/${tpl.id}/sync/`, { method: "POST" });
        onChange(s);
        toast(`Meta says: ${s.wa_status_label}.`, s.wa_status === "APPROVED" ? "success" : "info");
      } catch (e) {
        toast(e.message, "error", 9000);
      }
    });

  const isWA = channel === "whatsapp";
  const blocked = isWA && tpl.enabled && tpl.wa_status !== "APPROVED";
  const status = isWA ? <Pill status={tpl.wa_status}>{tpl.wa_status_label}</Pill>
    : !provider?.configured ? <Pill status="skipped">Keys missing</Pill>
    : <Pill status={tpl.enabled ? "sent" : "DRAFT"}>{tpl.enabled ? "Ready" : "Off"}</Pill>;

  return (
    <div className={`cell ${tpl.enabled ? "cell-on" : "cell-off"} cell-${channel}`} role="cell">
      <div className="cell-top">
        <span className="cell-ch"><ChannelIcon channel={channel} size={14} /> {label}</span>
        <Switch size="sm" checked={tpl.enabled} disabled={busy === "toggle"} onChange={toggle}
          label={`${trigger.name} on ${label}: ${tpl.enabled ? "on" : "off"}`} />
      </div>
      <button className="cell-body" onClick={onOpen} title="Edit template">
        {tpl.preview.title && <strong>{tpl.preview.title}</strong>}
        <span>{tpl.preview.body || <em>No message yet</em>}</span>
      </button>
      <div className="cell-foot">
        {status}
        <div className="cell-actions">
          {isWA && (
            <button className="icon-btn" onClick={sync} disabled={!!busy} aria-label="Sync with Meta" title="Sync with Meta">
              {busy === "sync" ? <Spinner size={15} /> : <RefreshCw size={15} />}
            </button>
          )}
          <button className="icon-btn" onClick={test} disabled={!!busy} aria-label="Send test" title="Send test to yourself">
            {busy === "test" ? <Spinner size={15} /> : <Send size={15} />}
          </button>
          <button className="icon-btn" onClick={onOpen} aria-label="Edit template" title="Edit">
            <Pencil size={15} />
          </button>
        </div>
      </div>
      {blocked && (
        <p className="cell-warn"><AlertTriangle size={13} aria-hidden /> Sends once Meta approves it</p>
      )}
    </div>
  );
}

export default function Matrix() {
  const { overview, reloadOverview } = useOutletContext();
  const toast = useToast();
  const [triggers, setTriggers] = useState(null);
  const [variables, setVariables] = useState([]);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState(null); // {trigger, channel}
  const [triggerForm, setTriggerForm] = useState(null); // {trigger?}

  const load = useCallback(async () => {
    try {
      setTriggers(await api("/api/admin/triggers/"));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
    api("/api/variables/").then(setVariables).catch(() => {});
  }, [load]);

  const updateTemplate = (tpl) => {
    setTriggers((ts) =>
      ts.map((t) => (t.id === tpl.trigger ? { ...t, templates: { ...t.templates, [tpl.channel]: tpl } } : t))
    );
    reloadOverview();
  };

  const toggleTrigger = async (t, v) => {
    try {
      const saved = await api(`/api/admin/triggers/${t.id}/`, { method: "PATCH", body: { is_active: v } });
      setTriggers((ts) => ts.map((x) => (x.id === t.id ? saved : x)));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const remove = async (t) => {
    if (!window.confirm(`Delete "${t.name}" and its ${Object.values(t.templates).filter(Boolean).length} templates? This can't be undone.`)) return;
    try {
      await api(`/api/admin/triggers/${t.id}/`, { method: "DELETE" });
      setTriggers((ts) => ts.filter((x) => x.id !== t.id));
      toast(`Deleted ${t.name}.`, "success");
      reloadOverview();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const providers = overview?.providers;
  const missing = providers ? CHANNELS.filter((c) => !providers[c.key]?.configured) : [];
  const editing = editor && triggers?.find((t) => t.id === editor.trigger.id);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Notification settings</h1>
          <p className="muted">Rows are triggers, columns are channels. Each cell is one message.</p>
        </div>
        <Button icon={Plus} onClick={() => setTriggerForm({})}>Add trigger</Button>
      </div>

      {overview && (
        <div className="stat-strip">
          <div><strong>{overview.stats.triggers}</strong><span>Triggers</span></div>
          <div><strong>{overview.stats.active_templates}</strong><span>Messages on</span></div>
          <div><strong>{overview.stats.sent_7d}</strong><span>Sent this week</span></div>
          <div className={overview.stats.failed_7d ? "bad" : ""}><strong>{overview.stats.failed_7d}</strong><span>Failed this week</span></div>
        </div>
      )}

      {missing.length > 0 && (
        <div className="alert alert-warn">
          <AlertTriangle size={16} aria-hidden />
          <span>
            {missing.map((m) => m.label).join(", ")} {missing.length === 1 ? "has" : "have"} no API keys yet, so those messages will be skipped.{" "}
            <Link to="/admin/setup">See channel setup</Link>
          </span>
        </div>
      )}

      {error && <div className="alert alert-bad">{error} <button className="link-btn" onClick={load}>Try again</button></div>}

      {!triggers && !error && <div className="page-loading"><Spinner /> Loading triggers…</div>}

      {triggers && triggers.length === 0 && (
        <Empty icon={Zap} title="No triggers yet" action={<Button icon={Plus} onClick={() => setTriggerForm({})}>Add trigger</Button>}>
          Add something that happens on the website, like Login or Order placed.
        </Empty>
      )}

      {triggers && triggers.length > 0 && (
        <div className="matrix" role="table" aria-label="Notification templates by trigger and channel">
          <div className="mx-row mx-head" role="row">
            <div role="columnheader">Trigger</div>
            {CHANNELS.map((c) => (
              <div role="columnheader" key={c.key} className={`mx-colhead ch-text-${c.key}`}>
                <ChannelIcon channel={c.key} size={15} /> {c.label}
              </div>
            ))}
          </div>
          {triggers.map((t) => (
            <div className={`mx-row ${t.is_active ? "" : "mx-paused"}`} role="row" key={t.id}>
              <div className="mx-trigger" role="rowheader">
                <div className="mx-trigger-top">
                  <h3>{t.name}</h3>
                  <Switch size="sm" checked={t.is_active} onChange={(v) => toggleTrigger(t, v)}
                    label={`${t.name} trigger ${t.is_active ? "active" : "paused"}`} />
                </div>
                <p className="muted small">{t.description}</p>
                <div className="mx-tags">
                  {t.kind === "inactivity" ? (
                    <span className="tag"><Clock size={12} aria-hidden /> After {t.inactivity_days} day{t.inactivity_days > 1 ? "s" : ""} away</span>
                  ) : (
                    <span className="tag"><Zap size={12} aria-hidden /> {t.key}</span>
                  )}
                  {!t.is_active && <span className="tag tag-warn">Paused</span>}
                </div>
                <div className="mx-trigger-foot">
                  <span className="muted small">Fired {t.fired_count}× · {timeAgo(t.last_fired)}</span>
                  <span>
                    <button className="icon-btn" aria-label={`Edit ${t.name}`} onClick={() => setTriggerForm({ trigger: t })}><Pencil size={14} /></button>
                    <button className="icon-btn danger" aria-label={`Delete ${t.name}`} onClick={() => remove(t)}><Trash2 size={14} /></button>
                  </span>
                </div>
              </div>
              {CHANNELS.map((c) => (
                <Cell key={c.key} trigger={t} channel={c.key} tpl={t.templates[c.key]} provider={providers?.[c.key]}
                  onOpen={() => setEditor({ trigger: t, channel: c.key })} onChange={updateTemplate} />
              ))}
            </div>
          ))}
        </div>
      )}

      {editor && (
        <TemplateEditor
          open
          trigger={editing || editor.trigger}
          channel={editor.channel}
          template={(editing || editor.trigger).templates[editor.channel]}
          variables={variables}
          onClose={() => setEditor(null)}
          onSaved={updateTemplate}
        />
      )}
      <TriggerForm
        open={!!triggerForm}
        trigger={triggerForm?.trigger}
        onClose={() => setTriggerForm(null)}
        onSaved={() => {
          setTriggerForm(null);
          load();
          reloadOverview();
        }}
      />
    </div>
  );
}
