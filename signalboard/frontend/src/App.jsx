import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Landing from "./pages/Landing.jsx";
import { Login, Register, ForgotPassword } from "./pages/AuthPages.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import AdminLayout from "./pages/admin/AdminLayout.jsx";
import Matrix from "./pages/admin/Matrix.jsx";
import Activity from "./pages/admin/Activity.jsx";
import Users from "./pages/admin/Users.jsx";
import Setup from "./pages/admin/Setup.jsx";
import { Spinner } from "./components/ui.jsx";

function RequireAuth({ children, admin = false }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="page-loading"><Spinner /> Loading your account…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (admin && !user.is_staff) return <Navigate to="/app" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/app" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/admin" element={<RequireAuth admin><AdminLayout /></RequireAuth>}>
        <Route index element={<Matrix />} />
        <Route path="activity" element={<Activity />} />
        <Route path="users" element={<Users />} />
        <Route path="setup" element={<Setup />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
