import { useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw, Send, Link2, Lock } from "lucide-react";
import { api, fieldErrors } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useToast } from "../../toast.jsx";
import PushToggle from "../../components/PushToggle.jsx";
import { Button, Field, Pill, Sheet, Switch, channelMeta, timeAgo } from "../../components/ui.jsx";
import { EmailPreview, PushPreview, WhatsAppPreview, renderVars } from "../../components/Previews.jsx";

const LANGS = [
  ["en_US", "English (US)"],
  ["en", "English"],
  ["en_GB", "English (UK)"],
  ["hi", "Hindi"],
];

function defaults(channel, trigger) {
  const base = { enabled: channel !== "whatsapp", title: "", body: "", cta_label: "", url: "", footer: "" };
  if (channel === "whatsapp")
    return { ...base, wa_name: `${trigger.key.replace(/[^a-z0-9]+/gi, "_").toLowerCase()}_msg`, wa_language: "en_US",
      wa_category: "UTILITY", wa_use_existing: false, body: `Hi {{first_name}}, ` };
  if (channel === "webpush") return { ...base, url: "{{site_url}}/app", push_ios: false, push_android: false };
  return { ...base, url: "{{site_url}}/app" };
}

const pick = (t) => ({
  enabled: t.enabled, title: t.title, body: t.body, cta_label: t.cta_label, url: t.url, footer: t.footer,
  wa_name: t.wa_name, wa_language: t.wa_language, wa_category: t.wa_category, wa_use_existing: t.wa_use_existing,
  push_ios: t.push_ios, push_android: t.push_android,
});

export default function TemplateEditor({ open, trigger, channel, template, variables, onClose, onSaved }) {
  const { user } = useAuth();
  const toast = useToast();
  const [tpl, setTpl] = useState(template);
  const [form, setForm] = useState({});
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [testTo, setTestTo] = useState("");
  const [focus, setFocus] = useState("body");
  const refs = { title: useRef(null), body: useRef(null), url: useRef(null) };

  useEffect(() => {
    if (!open) return;
    setTpl(template);
    setForm(template ? pick(template) : defaults(channel, trigger));
    setErrors({});
    setTestTo(channel === "whatsapp" ? user.phone || "" : channel === "email" ? user.email : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, template?.id, channel]);

  const meta = channelMeta(channel);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }));
  const dirty = !tpl || JSON.stringify(pick({ ...tpl })) !== JSON.stringify({ ...pick({ ...tpl }), ...form });
  const samples = useMemo(() => Object.fromEntries((variables || []).map((v) => [v.name, v.sample])), [variables]);
  const r = (s) => renderVars(s, samples);
  const isWA = channel === "whatsapp";
  const linked = isWA && form.wa_use_existing;

  const insertVar = (name) => {
    const key = focus in refs ? focus : "body";
    const el = refs[key].current;
    const token = `{{${name}}}`;
    const val = form[key] || "";
    const start = el?.selectionStart ?? val.length;
    const end = el?.selectionEnd ?? val.length;
    const next = val.slice(0, start) + token + val.slice(end);
    setForm((f) => ({ ...f, [key]: next }));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(start + token.length, start + token.length);
    });
  };

  const save = async () => {
    setSaving(true);
    setErrors({});
    try {
      const body = { ...form, trigger: trigger.id, channel };
      const saved = tpl
        ? await api(`/api/admin/templates/${tpl.id}/`, { method: "PATCH", body })
        : await api("/api/admin/templates/", { method: "POST", body });
      setTpl(saved);
      setForm(pick(saved));
      onSaved(saved);
      if (saved.notice) toast(saved.notice, saved.wa_status === "ERROR" ? "error" : "success", 9000);
      else toast("Template saved.", "success");
      return saved;
    } catch (e) {
      const fe = fieldErrors(e);
      setErrors(Object.keys(fe).length ? fe : { form: e.message });
      return null;
    } finally {
      setSaving(false);
    }
  };

  const sync = async () => {
    setSyncing(true);
    try {
      const s = await api(`/api/admin/templates/${tpl.id}/sync/`, { method: "POST" });
      setTpl(s);
      onSaved(s);
      toast(`Meta says: ${s.wa_status_label}.`, s.wa_status === "APPROVED" ? "success" : "info");
    } catch (e) {
      toast(e.message, "error", 9000);
    } finally {
      setSyncing(false);
    }
  };

  const test = async () => {
    let current = tpl;
    if (dirty) current = await save();
    if (!current) return;
    setTesting(true);
    try {
      const res = await api(`/api/admin/templates/${current.id}/test/`, {
        method: "POST",
        body: channel === "webpush" ? {} : { to: testTo },
      });
      toast(`Test sent to ${res.recipient}. Check your ${channel === "webpush" ? "browser" : meta.label}.`, "success");
    } catch (e) {
      toast(e.data?.error || e.message, "error", 10000);
    } finally {
      setTesting(false);
    }
  };

  const titleLabel = { whatsapp: "Header (optional)", email: "Subject", webpush: "Title" }[channel];

  return (
    <Sheet
      open={open}
      onClose={onClose}
      wide
      title={`${trigger?.name} — ${meta.label}`}
      subtitle={tpl ? `Last saved ${timeAgo(tpl.updated_at)}` : "New template"}
      footer={
        <>
          <label className="inline-switch">
            <Switch checked={!!form.enabled} onChange={set("enabled")} label="Send this message" />
            <span>{form.enabled ? "On" : "Off"}</span>
          </label>
          <div className="grow" />
          <Button variant="ghost" onClick={onClose}>Close</Button>
          <Button loading={saving} onClick={save} disabled={!dirty && !!tpl}>{tpl ? "Save changes" : "Create template"}</Button>
        </>
      }
    >
      <div className="editor">
        <div className="editor-form">
          {errors.form && <div className="alert alert-bad">{errors.form}</div>}

          {isWA && (
            <div className="wa-meta">
              <Field label="Meta template name" htmlFor="wa_name" error={errors.wa_name}
                hint="Lowercase, numbers and underscores. This is the name Meta reviews.">
                <input id="wa_name" value={form.wa_name || ""} onChange={set("wa_name")} />
              </Field>
              <div className="row-2">
                <Field label="Language" htmlFor="wa_lang">
                  <select id="wa_lang" value={form.wa_language} onChange={set("wa_language")}>
                    {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Field>
                <Field label="Category" htmlFor="wa_cat" hint="Account alerts are Utility.">
                  <select id="wa_cat" value={form.wa_category} onChange={set("wa_category")} disabled={linked}>
                    <option value="UTILITY">Utility</option>
                    <option value="MARKETING">Marketing</option>
                  </select>
                </Field>
              </div>
              <label className="check">
                <input type="checkbox" checked={!!form.wa_use_existing} onChange={(e) => set("wa_use_existing")(e.target.checked)} />
                <span><Link2 size={14} aria-hidden /> Use a template that already exists in Meta (e.g. <code>hello_world</code>)</span>
              </label>
            </div>
          )}

          {!(isWA && linked && !form.title) && (
            <Field label={titleLabel} htmlFor="title" error={errors.title}
              hint={isWA ? "Plain text, up to 60 characters." : channel === "email" ? "Variables work here too." : "Keep it short — browsers cut long titles."}>
              <input id="title" ref={refs.title} value={form.title || ""} onChange={set("title")} onFocus={() => setFocus("title")} />
            </Field>
          )}

          <Field label={linked ? "Body (copy of the Meta template)" : "Message"} htmlFor="body" error={errors.body}
            hint={isWA && !linked ? "Can't start or end with a variable — Meta rejects that." : linked ? "Map variables in the same order as {{1}}, {{2}} in Meta. Leave empty and press Save to copy it from Meta." : undefined}>
            <textarea id="body" ref={refs.body} rows={channel === "email" ? 7 : 4} value={form.body || ""}
              onChange={set("body")} onFocus={() => setFocus("body")} />
          </Field>

          <div className="vars" aria-label="Insert a variable">
            <span className="muted small">Insert into {focus === "title" ? titleLabel.toLowerCase() : focus === "url" ? "link" : "message"}:</span>
            {(variables || []).map((v) => (
              <button type="button" key={v.name} className="var-chip" title={`${v.description} — e.g. ${v.sample}`} onClick={() => insertVar(v.name)}>
                {v.name}
              </button>
            ))}
          </div>

          {isWA && !linked && (
            <Field label="Footer (optional)" htmlFor="footer" error={errors.footer}>
              <input id="footer" value={form.footer || ""} onChange={set("footer")} maxLength={60} />
            </Field>
          )}

          {channel === "email" && (
            <div className="row-2">
              <Field label="Button text (optional)" htmlFor="cta">
                <input id="cta" value={form.cta_label || ""} onChange={set("cta_label")} />
              </Field>
              <Field label="Button link" htmlFor="url">
                <input id="url" ref={refs.url} value={form.url || ""} onChange={set("url")} onFocus={() => setFocus("url")} />
              </Field>
            </div>
          )}

          {channel === "webpush" && (
            <>
              <Field label="Open this page when clicked" htmlFor="url">
                <input id="url" ref={refs.url} value={form.url || ""} onChange={set("url")} onFocus={() => setFocus("url")} />
              </Field>
              <div className="platforms">
                <span className="platform on"><Switch checked disabled size="sm" label="Web" /> Web browsers</span>
                <span className="platform"><Switch checked={false} disabled size="sm" label="iOS" /> iOS <Lock size={12} /></span>
                <span className="platform"><Switch checked={false} disabled size="sm" label="Android" /> Android <Lock size={12} /></span>
                <p className="muted small">This project sends Web Push only, so iOS and Android stay off.</p>
              </div>
            </>
          )}

          {isWA && tpl && (
            <div className={`wa-status wa-${tpl.wa_status}`}>
              <div className="wa-status-top">
                <div>
                  <span className="muted small">Meta review</span>
                  <div><Pill status={tpl.wa_status}>{tpl.wa_status_label}</Pill></div>
                </div>
                <Button variant="ghost" size="sm" icon={RefreshCw} loading={syncing} onClick={sync}>Sync</Button>
              </div>
              {tpl.wa_status_reason && <p className="wa-reason">{tpl.wa_status_reason}</p>}
              {tpl.wa_status === "PENDING" && <p className="muted small">Test numbers are usually reviewed within a few minutes. Press Sync to check.</p>}
              {tpl.variable_mapping?.length > 0 && (
                <p className="muted small">
                  Variable mapping: {tpl.variable_mapping.map((v, i) => <code key={v}>{`{{${i + 1}}}`}→{v}</code>)}
                </p>
              )}
              {tpl.wa_synced_at && <p className="muted small">Last synced {timeAgo(tpl.wa_synced_at)}</p>}
            </div>
          )}

          <div className="test-box">
            <h3>Send a test</h3>
            {channel === "webpush" ? (
              user.push_subscribed ? (
                <p className="muted small">Goes to this browser (your admin account).</p>
              ) : (
                <div className="test-push-off">
                  <p className="muted small">Allow browser alerts for your admin account first.</p>
                  <PushToggle compact />
                </div>
              )
            ) : (
              <Field label={isWA ? "WhatsApp number" : "Email address"} htmlFor="test_to"
                hint={isWA ? "Must be a test recipient in your Meta app." : undefined}>
                <input id="test_to" value={testTo} onChange={(e) => setTestTo(e.target.value)} type={isWA ? "tel" : "email"} />
              </Field>
            )}
            <Button variant="secondary" icon={Send} loading={testing}
              disabled={(channel === "webpush" && !user.push_subscribed) || (channel !== "webpush" && !testTo)}
              onClick={test}>
              {dirty ? "Save and send test" : "Send test"}
            </Button>
          </div>
        </div>

        <div className="editor-preview" aria-label="Preview with sample data">
          <p className="muted small">Preview with sample data</p>
          {isWA && <WhatsAppPreview header={r(form.title)} body={r(form.body)} footer={form.footer} />}
          {channel === "email" && <EmailPreview subject={r(form.title)} body={r(form.body)} ctaLabel={form.cta_label} />}
          {channel === "webpush" && <PushPreview title={r(form.title)} body={r(form.body)} url={r(form.url)} />}
        </div>
      </div>
    </Sheet>
  );
}
