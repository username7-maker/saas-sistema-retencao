import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/dashboard/executive", label: "Executivo" },
  { to: "/dashboard/operational", label: "Operacional" },
  { to: "/dashboard/commercial", label: "Comercial" },
  { to: "/dashboard/financial", label: "Financeiro" },
  { to: "/dashboard/retention", label: "Retencao" },
  { to: "/crm", label: "CRM" },
  { to: "/tasks", label: "Tasks" },
];

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#f8fffd] via-[#f4fbf7] to-[#ecf4ff] text-slate-800">
      <header className="sticky top-0 z-30 border-b border-brand-100 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link to="/dashboard/executive" className="font-heading text-2xl font-bold text-brand-700">
              AI GYM OS
            </Link>
            <p className="text-sm text-slate-500">BI, Retencao e CRM para academias B2B</p>
          </div>

          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition ${
                    isActive ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-600 hover:bg-brand-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div className="text-right text-xs text-slate-500">
              <p className="font-semibold text-slate-700">{user?.full_name}</p>
              <p>{user?.role}</p>
            </div>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-full bg-rose-500 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:bg-rose-600"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 animate-rise">
        <Outlet />
      </main>
    </div>
  );
}
