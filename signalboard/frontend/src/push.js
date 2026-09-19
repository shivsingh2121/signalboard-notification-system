// Web Push via OneSignal Web SDK v16 (browser only — no iOS/Android apps).
const APP_ID = import.meta.env.VITE_ONESIGNAL_APP_ID;
let ready = null;

export const pushAvailable = () => Boolean(APP_ID) && "Notification" in window && "serviceWorker" in navigator;

export function initPush() {
  if (!pushAvailable()) return Promise.resolve(null);
  if (ready) return ready;
  ready = new Promise((resolve) => {
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    const s = document.createElement("script");
    s.src = "https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js";
    s.defer = true;
    s.onerror = () => resolve(null);
    document.head.appendChild(s);
    window.OneSignalDeferred.push(async (OneSignal) => {
      try {
        await OneSignal.init({ appId: APP_ID, allowLocalhostAsSecureOrigin: true, notifyButton: { enable: false } });
        resolve(OneSignal);
      } catch (e) {
        console.warn("OneSignal init failed", e);
        resolve(null);
      }
    });
    setTimeout(() => resolve(null), 15000);
  });
  return ready;
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

/** Ask permission, subscribe this browser and return the subscription id. */
export async function subscribePush(userId, onChange) {
  if (!APP_ID) throw new Error("Browser alerts aren't set up yet: add VITE_ONESIGNAL_APP_ID to the frontend env.");
  if (!pushAvailable()) throw new Error("This browser doesn't support notifications. Try Chrome, Edge or Firefox on desktop.");
  const OS = await initPush();
  if (!OS) throw new Error("OneSignal didn't load. Check that your OneSignal site URL matches this website's address.");
  await OS.login(String(userId));
  if (Notification.permission === "denied") {
    throw new Error("Notifications are blocked for this site. Click the lock icon in the address bar and allow notifications.");
  }
  if (onChange) {
    OS.User.PushSubscription.addEventListener("change", (e) => {
      if (e.current?.id && e.current?.optedIn) onChange(e.current.id);
    });
  }
  await OS.User.PushSubscription.optIn();
  for (let i = 0; i < 20; i++) {
    const sub = OS.User.PushSubscription;
    if (sub.id && sub.optedIn) return sub.id;
    await wait(500);
  }
  throw new Error("Notification permission wasn't granted. Allow notifications when the browser asks.");
}

export async function unsubscribePush() {
  const OS = await initPush();
  if (OS) await OS.User.PushSubscription.optOut();
}

export async function logoutPush() {
  const OS = await initPush();
  if (OS) {
    try {
      await OS.logout();
    } catch {
      /* ignore */
    }
  }
}
