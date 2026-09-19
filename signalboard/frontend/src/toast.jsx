import { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

const ToastCtx = createContext(() => {});
let seq = 0;

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const dismiss = (id) => setItems((xs) => xs.filter((x) => x.id !== id));
  const toast = useCallback((message, tone = "info", ms = 5000) => {
    const id = ++seq;
    setItems((xs) => [...xs.slice(-3), { id, message, tone }]);
    if (ms) setTimeout(() => dismiss(id), ms);
  }, []);
  const Icon = { success: CheckCircle2, error: AlertTriangle, info: Info };
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => {
          const I = Icon[t.tone] || Info;
          return (
            <div key={t.id} className={`toast toast-${t.tone}`}>
              <I size={18} aria-hidden />
              <span>{t.message}</span>
              <button className="icon-btn" onClick={() => dismiss(t.id)} aria-label="Dismiss">
                <X size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);
