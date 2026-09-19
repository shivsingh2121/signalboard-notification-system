import { useEffect, useState } from "react";
import { api, fieldErrors } from "../../api.js";
import { useToast } from "../../toast.jsx";
import { Button, Field, Sheet } from "../../components/ui.jsx";

const slug = (s) => s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 60);

export default function TriggerForm({ open, trigger, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({});
  const [keyTouched, setKeyTouched] = useState(false);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(trigger ? { ...trigger } : { name: "", key: "", description: "", kind: "event", inactivity_days: 3, is_active: true });
    setKeyTouched(Boolean(trigger));
    setErrors({});
  }, [open, trigger]);

  const set = (k) => (e) => {
    const v = e.target.value;
    setForm((f) => ({ ...f, [k]: v, ...(k === "name" && !keyTouched ? { key: slug(v) } : {}) }));
  };

  const save = async () => {
    setBusy(true);
    setErrors({});
    const body = {
      name: form.name, key: form.key, description: form.description, kind: form.kind,
      inactivity_days: form.kind === "inactivity" ? Number(form.inactivity_days) || null : null,
    };
    try {
      const saved = trigger
        ? await api(`/api/admin/triggers/${trigger.id}/`, { method: "PATCH", body })
        : await api("/api/admin/triggers/", { method: "POST", body });
      toast(trigger ? "Trigger saved." : "Trigger added. Now create its messages.", "success");
      onSaved(saved);
    } catch (e) {
      const fe = fieldErrors(e);
      setErrors(Object.keys(fe).length ? fe : { form: e.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title={trigger ? "Edit trigger" : "Add a trigger"}
      subtitle="A trigger is anything on the website that should send a message."
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save}>{trigger ? "Save trigger" : "Add trigger"}</Button></>}>
      <div className="form">
        {errors.form && <div className="alert alert-bad">{errors.form}</div>}
        <Field label="Name" htmlFor="t_name" error={errors.name}>
          <input id="t_name" value={form.name || ""} onChange={set("name")} placeholder="e.g. Profile updated" />
        </Field>
        <Field label="Code key" htmlFor="t_key" error={errors.key}
          hint={form.kind === "event" ? `Website code fires it with fire_trigger("${form.key || "key"}", user)` : "Used in logs and code."}>
          <input id="t_key" value={form.key || ""} onChange={(e) => { setKeyTouched(true); set("key")(e); }} />
        </Field>
        <Field label="Description" htmlFor="t_desc">
          <input id="t_desc" value={form.description || ""} onChange={set("description")} placeholder="When does it fire?" />
        </Field>
        <fieldset className="kind">
          <legend>When it fires</legend>
          <label className={form.kind === "event" ? "sel" : ""}>
            <input type="radio" name="kind" value="event" checked={form.kind === "event"} onChange={set("kind")} />
            <span><strong>Something the user does</strong><small>Login, logout, order placed…</small></span>
          </label>
          <label className={form.kind === "inactivity" ? "sel" : ""}>
            <input type="radio" name="kind" value="inactivity" checked={form.kind === "inactivity"} onChange={set("kind")} />
            <span><strong>The user stays away</strong><small>Checked every hour by the scheduler</small></span>
          </label>
        </fieldset>
        {form.kind === "inactivity" && (
          <Field label="Days without a visit" htmlFor="t_days" error={errors.inactivity_days}>
            <input id="t_days" type="number" min="1" max="365" value={form.inactivity_days || ""} onChange={set("inactivity_days")} />
          </Field>
        )}
      </div>
    </Sheet>
  );
}
