import { Link, NavLink, Outlet } from "react-router-dom";
import { Moon, Sun } from "lucide-react";

import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";

const navItems = [
  { to: "/dashboard/executive", label: "Executivo" },
  { to: "/dashboard/operational", label: "Operacional" },
  { to: "/dashboard/commercial", label: "Comercial" },
  { to: "/dashboard/financial", label: "Financeiro" },
  { to: "/dashboard/retention", label: "Retencao" },
  { to: "/assessments", label: "Avaliacoes" },
  { to: "/crm", label: "CRM" },
  { to: "/tasks", label: "Tasks" },
  { to: "/goals", label: "Metas" },
  { to: "/imports", label: "Importacoes" },
  { to: "/automations", label: "Automacoes" },
  { to: "/notifications", label: "Notificacoes" },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#f8fffd] via-[#f4fbf7] to-[#ecf4ff] text-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950 dark:text-slate-200">
      <header className="sticky top-0 z-30 border-b border-brand-100 bg-white/80 backdrop-blur dark:border-slate-700 dark:bg-slate-900/80">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link to="/dashboard/executive" className="font-heading text-2xl font-bold text-brand-700 dark:text-brand-300">
              AI GYM OS
            </Link>
            <p className="text-sm text-slate-500 dark:text-slate-400">BI, Retencao e CRM para academias B2B</p>
          </div>

          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition ${
                    isActive
                      ? "bg-brand-500 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-brand-100 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-full p-1.5 text-slate-500 transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              title={theme === "dark" ? "Modo claro" : "Modo escuro"}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div className="text-right text-xs text-slate-500 dark:text-slate-400">
              <p className="font-semibold text-slate-700 dark:text-slate-200">{user?.full_name}</p>
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
