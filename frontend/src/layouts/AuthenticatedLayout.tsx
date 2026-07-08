import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { StationSelector } from "../components/StationSelector";

const navItems = [
  { to: "/", label: "Início", permission: "dashboard.read" },
  { to: "/organization", label: "Organização", permission: "organizations.read" },
  { to: "/stations", label: "Postos", permission: "stations.read" },
  { to: "/users", label: "Usuários", permission: "users.read" },
  { to: "/audit", label: "Auditoria", permission: "audit.read" },
  { to: "/profile", label: "Perfil", permission: "dashboard.read" },
];

export function AuthenticatedLayout() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded border border-slate-300 px-2 py-1 text-sm md:hidden"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Abrir menu"
            >
              Menu
            </button>
            <div>
              <p className="font-semibold">Inteligência Auto Postos</p>
              <p className="text-xs text-slate-500">{user?.organization.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StationSelector />
            <div className="hidden text-right text-sm sm:block">
              <p className="font-medium">{user?.name}</p>
              <p className="text-xs text-slate-500">{user?.roles.join(", ")}</p>
            </div>
            <button
              type="button"
              className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
        <aside
          className={`${menuOpen ? "block" : "hidden"} w-full shrink-0 md:block md:w-56`}
          aria-label="Menu principal"
        >
          <nav className="space-y-1 rounded-lg border border-slate-200 bg-white p-2">
            {navItems
              .filter((item) => hasPermission(item.permission))
              .map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `block rounded px-3 py-2 text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            <Link to="/health" className="block rounded px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
              Saúde do sistema
            </Link>
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
