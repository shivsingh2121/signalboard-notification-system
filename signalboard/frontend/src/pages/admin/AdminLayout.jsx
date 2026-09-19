import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, ExternalLink, LayoutGrid, LogOut, PlugZap, Users } from "lucide-react";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { useToast } from "../../toast.jsx";
import PushToggle from "../../components/PushToggle.jsx";
import { Logo } from "../../components/ui.jsx";

const NAV = [
  { to: "/admin", end: true, label: "Notification settings", Icon: LayoutGrid },
  { to: "/admin/activity", label: "Activity", Icon: Activity },
  { to: "/admin/users", label: "Users", Icon: Users },
  { to: "/admin/setup", label: "Channel setup", Icon: PlugZap },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [overview, setOverview] = useState(null);

  const loadOverview = useCallback(() => api("/api/admin/overview/").then(setOverview).catch(() => {}), []);
  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const signOut = async () => {
    await logout().catch(() => {});
    toast("Signed out.", "info");
    nav("/login");
  };

  return (
    <div className="admin">
      <aside className="admin-side">
        <Logo to="/admin" light />
        <nav className="admin-nav" aria-label="Admin">
          {NAV.map(({ to, end, label, Icon }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon size={18} aria-hidden />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-side-foot">
          <Link to="/app" className="side-link"><ExternalLink size={15} /> Open the website</Link>
          <div className="side-user">
            <span className="avatar">{user.name[0]?.toUpperCase()}</span>
            <div>
              <strong>{user.name}</strong>
              <small>{user.email}</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="admin-main">
        <header className="admin-top">
          <div className="admin-top-mobile"><Logo to="/admin" /></div>
          <div className="admin-top-actions">
            <PushToggle compact />
            <button className="btn btn-ghost btn-sm" onClick={signOut}><LogOut size={16} /> <span>Sign out</span></button>
          </div>
        </header>
        <nav className="admin-tabs" aria-label="Admin sections">
          {NAV.map(({ to, end, label, Icon }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon size={16} aria-hidden /> <span>{label.replace("Notification settings", "Settings").replace("Channel setup", "Setup")}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-content">
          <Outlet context={{ overview, reloadOverview: loadOverview }} />
        </div>
      </div>
    </div>
  );
}
