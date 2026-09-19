import { useState } from "react";
import { BellOff, BellRing } from "lucide-react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { subscribePush, unsubscribePush } from "../push.js";
import { useToast } from "../toast.jsx";
import { Button } from "./ui.jsx";

export default function PushToggle({ compact = false }) {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const on = user?.push_subscribed;

  const save = async (id) => {
    const me = await api("/api/auth/push-subscription/", { method: "POST", body: { subscription_id: id } });
    setUser(me);
  };

  const enable = async () => {
    setBusy(true);
    try {
      const id = await subscribePush(user.id, (newId) => save(newId).catch(() => {}));
      await save(id);
      toast("Browser alerts are on for this browser.", "success");
    } catch (e) {
      toast(e.message, "error", 9000);
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    try {
      await unsubscribePush();
      const me = await api("/api/auth/push-subscription/", { method: "DELETE" });
      setUser(me);
      toast("Browser alerts are off.", "info");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return on ? (
    <Button variant="ghost" size={compact ? "sm" : undefined} icon={BellOff} loading={busy} onClick={disable}>
      {compact ? "Alerts on" : "Turn off browser alerts"}
    </Button>
  ) : (
    <Button variant="push" size={compact ? "sm" : undefined} icon={BellRing} loading={busy} onClick={enable}>
      {compact ? "Allow alerts" : "Turn on browser alerts"}
    </Button>
  );
}
