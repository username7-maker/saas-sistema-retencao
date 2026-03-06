import {
  Activity,
  Bell,
  Bot,
  Briefcase,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  Globe,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  ScrollText,
  Settings,
  ShieldAlert,
  Sparkles,
  Star,
  Sun,
  Target,
  Upload,
  UserCog,
  UserSquare2,
  Users,
  Wallet,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { notificationService } from "../../services/notificationService";
import { Button, Drawer, cn } from "../ui2";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "Dashboards",
    items: [
      { to: "/dashboard/executive", label: "Executivo", icon: LayoutDashboard },
      { to: "/dashboard/operational", label: "Operacional", icon: Activity },
      { to: "/dashboard/commercial", label: "Comercial", icon: Briefcase, badge: "new" },
      { to: "/dashboard/financial", label: "Financeiro", icon: Wallet },
      { to: "/dashboard/retention", label: "Retencao", icon: ShieldAlert },
    ],
  },
  {
    label: "Gestao",
    items: [
      { to: "/members", label: "Membros", icon: UserSquare2 },
      { to: "/assessments", label: "Avaliacoes", icon: ClipboardList },
      { to: "/crm", label: "CRM", icon: Users, badge: "6" },
      { to: "/tasks", label: "Tarefas", icon: CheckSquare },
    ],
  },
  {
    label: "Resultados",
    items: [
      { to: "/goals", label: "Metas", icon: Target },
      { to: "/nps", label: "NPS", icon: Star },
      { to: "/reports", label: "Relatorios", icon: FileText },
    ],
  },
  {
    label: "Sistema",
    items: [
      { to: "/automations", label: "Automacoes", icon: Bot },
      { to: "/imports", label: "Importacoes", icon: Upload },
      { to: "/audit", label: "Auditoria", icon: ScrollText },
    ],
  },
  {
    label: "Admin",
    items: [
      { to: "/settings/users", label: "Usuarios", icon: UserCog },
      { to: "/settings", label: "Configuracoes", icon: Settings },
    ],
  },
];

function resolveActiveGroup(pathname: string): string | null {
  for (const group of navGroups) {
    if (group.items.some((item) => pathname.startsWith(item.to))) {
      return group.label;
    }
  }
  return null;
}

function resolveCurrentSection(pathname: string): string {
  for (const group of navGroups) {
    const item = group.items.find((candidate) => pathname.startsWith(candidate.to));
    if (item) return item.label;
  }
  return "Dashboard";
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  const activeGroup = resolveActiveGroup(pathname);
  const [openGroups, setOpenGroups] = useState<string[]>(activeGroup ? [activeGroup] : ["Dashboards"]);

  useEffect(() => {
    if (activeGroup && !openGroups.includes(activeGroup)) {
      setOpenGroups((prev) => [...prev, activeGroup]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGroup]);

  function toggleGroup(label: string) {
    setOpenGroups((prev) =>
      prev.includes(label) ? prev.filter((groupLabel) => groupLabel !== label) : [...prev, label],
    );
  }

  return (
    <nav className="space-y-2 px-3 pb-2">
      {navGroups.map((group) => {
        const isOpen = openGroups.includes(group.label);
        const ChevronIcon = isOpen ? ChevronDown : ChevronRight;
        return (
          <div key={group.label} className="border-b border-zinc-900/90 pb-2 last:border-b-0">
            <button
              type="button"
              onClick={() => toggleGroup(group.label)}
              className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-200"
            >
              {group.label}
              <ChevronIcon size={13} />
            </button>
            {isOpen ? (
              <div className="mt-1.5 space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-sm font-medium transition",
                          isActive
                            ? "border border-zinc-700 bg-zinc-800 text-zinc-100"
                            : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100",
                        )
                      }
                    >
                      <span className="flex items-center gap-2">
                        <Icon size={16} />
                        <span>{item.label}</span>
                      </span>
                      {item.badge ? (
                        <span
                          className={cn(
                            "rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                            item.badge === "new"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : "bg-zinc-700 text-zinc-200",
                          )}
                        >
                          {item.badge}
                        </span>
                      ) : null}
                    </NavLink>
                  );
                })}
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}

export function LovableLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const currentSection = resolveCurrentSection(pathname);
  const [mobileOpen, setMobileOpen] = useState(false);

  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => notificationService.listNotifications({ unread_only: false }),
    refetchInterval: 60_000,
  });

  const unreadCount = notifications?.items.filter((item) => !item.read_at).length ?? 0;
  const userEmail = user?.email ?? "owner@demo.local";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <aside aria-label="Main navigation" className="fixed inset-y-0 left-0 z-30 hidden w-72 p-3 lg:block">
        <div className="flex h-full flex-col rounded-[24px] border border-zinc-800 bg-zinc-950 shadow-[0_22px_80px_-40px_rgba(0,0,0,0.9)]">
          <div className="px-4 pt-4">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/85 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-950 text-sm font-semibold text-zinc-200">
                    #
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-zinc-100">AI GYM OS</p>
                    <p className="flex items-center gap-1 text-xs text-zinc-500">
                      <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      {userEmail}
                    </p>
                  </div>
                </div>
                <ChevronDown size={14} className="mt-1 text-zinc-500" />
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/60 px-3 py-2">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Integracoes</p>
              <div className="flex items-center gap-1">
                <span className="rounded-md bg-zinc-800 p-1 text-zinc-300">
                  <Globe size={12} />
                </span>
                <span className="rounded-md bg-zinc-800 p-1 text-zinc-300">
                  <Activity size={12} />
                </span>
                <span className="rounded-md bg-zinc-800 p-1 text-zinc-300">
                  <Sparkles size={12} />
                </span>
              </div>
            </div>
          </div>

          <div className="mt-3 flex-1 overflow-y-auto">
            <SidebarNav />
          </div>

          <div className="space-y-3 px-4 pb-4">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-3">
              <span className="inline-flex rounded-md bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
                New
              </span>
              <p className="mt-2 text-sm font-semibold text-zinc-100">Retencao Program</p>
              <p className="mt-1 text-xs text-zinc-500">Automacao para recuperar alunos inativos em lotes.</p>
              <button
                type="button"
                onClick={() => navigate("/automations")}
                className="mt-3 inline-flex items-center rounded-lg border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-xs font-semibold text-zinc-200 transition hover:border-zinc-500 hover:bg-zinc-800"
              >
                Abrir automacoes
              </button>
            </div>

            <div className="space-y-1 text-sm">
              <button
                type="button"
                onClick={() => navigate("/settings")}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-zinc-400 transition hover:bg-zinc-900 hover:text-zinc-100"
              >
                <Settings size={15} />
                Settings
              </button>
              <button
                type="button"
                onClick={() => navigate("/reports")}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-zinc-400 transition hover:bg-zinc-900 hover:text-zinc-100"
              >
                <HelpCircle size={15} />
                Help Center
              </button>
            </div>
          </div>
        </div>
      </aside>

      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)} title="AI GYM OS">
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <div className="min-h-screen lg:ml-72">
        <header role="banner" className="sticky top-0 z-20 px-4 pt-3 md:px-6 lg:px-7">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/92 px-4 py-3 backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="!text-zinc-300 hover:!bg-zinc-800 hover:!text-zinc-100 lg:hidden"
                  onClick={() => setMobileOpen(true)}
                  aria-label="Open navigation menu"
                >
                  <Menu size={16} />
                </Button>
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Workspace</p>
                  <h1 className="font-display text-xl font-semibold text-zinc-100">{currentSection}</h1>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={toggleTheme}
                  title={theme === "dark" ? "Modo claro" : "Modo escuro"}
                  className="rounded-lg border border-zinc-700 bg-zinc-900 p-2 text-zinc-300 transition hover:border-zinc-500 hover:text-zinc-100"
                >
                  {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
                </button>

                <button
                  type="button"
                  onClick={() => navigate("/notifications")}
                  className="relative rounded-lg border border-zinc-700 bg-zinc-900 p-2 text-zinc-300 transition hover:border-zinc-500 hover:text-zinc-100"
                  title="Notifications"
                  aria-label={unreadCount > 0 ? `Notifications ${unreadCount} unread` : "Notifications"}
                >
                  <Bell size={15} aria-hidden="true" />
                  {unreadCount > 0 ? (
                    <span
                      className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white"
                      aria-hidden="true"
                    >
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  ) : null}
                </button>

                <div className="hidden items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 md:flex">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-zinc-100">{user?.full_name ?? "Owner"}</p>
                    <p className="text-[11px] uppercase tracking-wider text-zinc-500">{user?.role ?? "owner"}</p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => void logout()}
                  className="inline-flex items-center gap-1 rounded-lg bg-rose-500 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-rose-400"
                >
                  <LogOut size={14} />
                  Sair
                </button>
              </div>
            </div>
          </div>
        </header>

        <main id="main-content" role="main" className="px-4 py-5 md:px-6 lg:px-7">
          <div className="mx-auto w-full max-w-[1560px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
